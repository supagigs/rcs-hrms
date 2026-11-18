"""Screening questions on Job Openings and the answers stored on Job Applicants.

QUESTION_TYPES is the single server-side registry: each type knows how to validate and normalize a
posted answer. The Job Opening Screening Question `question_type` options and the web form's client
renderer map (hrms/public/js/recruitment/job_application_form.js) must list the same types; a test
keeps them in sync. Adding a type means one entry here, one there and one Select option.
"""

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.utils import cint, cstr, escape_html, flt, getdate, today, validate_email_address

QUESTION_DOCTYPE = "Job Opening Screening Question"
RESPONSE_DOCTYPE = "Job Applicant Screening Response"

MAX_QUESTIONS = 50  # per Job Opening, as asked on the application form
MAX_RAW_ANSWER_LENGTH = 5000  # anything longer is rejected before parsing
MAX_HISTORY_ROWS = 20  # work experience / education rows on a web form application
SHORT_TEXT_MAX_LENGTH = 140
LONG_TEXT_MAX_LENGTH = 2000
URL_MAX_LENGTH = 500

QUESTION_FIELDS = (
	"name",
	"question",
	"question_type",
	"options",
	"is_mandatory",
	"description",
	"min_value",
	"max_value",
	"min_length",
	"max_length",
	"currency",
)


class ScreeningAnswerError(frappe.ValidationError):
	pass


@dataclass(frozen=True)
class Normalized:
	answer: str  # canonical text, what recruiters read
	number: float | None = None  # Number / Currency
	date: str | None = None  # Date, ISO format
	currency: str | None = None  # Currency


@dataclass(frozen=True)
class QuestionType:
	normalize: Callable[[object, frappe._dict], Normalized]
	needs_options: bool = False
	max_length: int | None = None  # hard cap for free text


# NORMALIZERS
# Each receives a non-empty raw value and the question row, and returns a Normalized value or raises
# ScreeningAnswerError with a message that completes "<question>: ...".


def text_type(cap: int) -> Callable[[object, frappe._dict], Normalized]:
	def normalize(value: object, question: frappe._dict) -> Normalized:
		if isinstance(value, list | dict):
			raise ScreeningAnswerError(_("must be text"))

		text = cstr(value).strip()
		max_length = min(cint(question.max_length) or cap, cap)
		if len(text) > max_length:
			raise ScreeningAnswerError(_("must be at most {0} characters").format(max_length))
		if cint(question.min_length) and len(text) < cint(question.min_length):
			raise ScreeningAnswerError(_("must be at least {0} characters").format(cint(question.min_length)))
		return Normalized(text)

	return normalize


def parse_number(value: object) -> float:
	if isinstance(value, bool) or isinstance(value, list | dict):
		raise ScreeningAnswerError(_("must be a number"))
	try:
		number = (
			float(value) if isinstance(value, int | float) else float(cstr(value).strip().replace(",", ""))
		)
	except ValueError:
		raise ScreeningAnswerError(_("must be a number")) from None
	if not math.isfinite(number):
		raise ScreeningAnswerError(_("must be a number"))
	return number


def check_range(number: float, question: frappe._dict) -> None:
	# Float fields store 0 when left empty, so 0 means "no limit"
	if flt(question.min_value) and number < flt(question.min_value):
		raise ScreeningAnswerError(_("must be at least {0}").format(format_number(flt(question.min_value))))
	if flt(question.max_value) and number > flt(question.max_value):
		raise ScreeningAnswerError(_("must be at most {0}").format(format_number(flt(question.max_value))))


def format_number(number: float) -> str:
	if number.is_integer():
		return str(int(number))
	return f"{number:.6f}".rstrip("0").rstrip(".")


def normalize_number(value: object, question: frappe._dict) -> Normalized:
	number = parse_number(value)
	check_range(number, question)
	return Normalized(format_number(number), number=number)


def normalize_currency(value: object, question: frappe._dict) -> Normalized:
	number = parse_number(value)
	if number < 0:
		raise ScreeningAnswerError(_("can't be negative"))
	check_range(number, question)
	return Normalized(format_number(number), number=number, currency=question.currency or None)


def normalize_yes_no(value: object, question: frappe._dict) -> Normalized:
	answers = {"yes": "Yes", "no": "No", "true": "Yes", "false": "No", "1": "Yes", "0": "No"}
	answer = answers.get(cstr(value).strip().lower())
	if not answer:
		raise ScreeningAnswerError(_("must be Yes or No"))
	return Normalized(answer)


def normalize_one_of(value: object, question: frappe._dict) -> Normalized:
	if isinstance(value, list):
		if len(value) != 1:
			raise ScreeningAnswerError(_("must be a single option"))
		value = value[0]
	answer = cstr(value).strip()
	if answer not in parse_options(question.options):
		raise ScreeningAnswerError(_("must be one of the listed options"))
	return Normalized(answer)


def normalize_many_of(value: object, question: frappe._dict) -> Normalized:
	if isinstance(value, str):
		value = value.strip()
		if value.startswith("["):
			try:
				value = json.loads(value)
			except ValueError:
				raise ScreeningAnswerError(_("must be a list of options")) from None
		else:
			value = value.split("\n")
	if not isinstance(value, list):
		raise ScreeningAnswerError(_("must be a list of options"))

	chosen = {cstr(item).strip() for item in value if cstr(item).strip()}
	options = parse_options(question.options)
	if chosen - set(options):
		raise ScreeningAnswerError(_("must only contain the listed options"))
	# option order, one per line: options can't contain newlines, so this round-trips
	return Normalized("\n".join(option for option in options if option in chosen))


def normalize_date(value: object, question: frappe._dict) -> Normalized:
	text = cstr(value).strip()
	try:
		answer = date.fromisoformat(text[:10]) if len(text) >= 10 else None
	except ValueError:
		answer = None
	if not answer or not 1900 <= answer.year <= 2200:
		raise ScreeningAnswerError(_("must be a valid date"))
	return Normalized(answer.isoformat(), date=answer.isoformat())


def is_web_url(text: str) -> bool:
	"""http(s) URL with a host; stricter than frappe.utils.validate_url, which accepts 'http:abc'"""
	url = urlparse(text)
	return url.scheme in ("http", "https") and "." in (url.hostname or "") and " " not in text


def normalize_url(value: object, question: frappe._dict) -> Normalized:
	text = cstr(value).strip()
	if len(text) > URL_MAX_LENGTH or not is_web_url(text):
		raise ScreeningAnswerError(_("must be a valid link starting with http:// or https://"))
	return Normalized(text)


def normalize_email(value: object, question: frappe._dict) -> Normalized:
	text = cstr(value).strip()
	# validate_email_address accepts comma separated lists; a question takes one address
	if "," in text or ";" in text or not validate_email_address(text):
		raise ScreeningAnswerError(_("must be a valid email address"))
	return Normalized(text)


QUESTION_TYPES: dict[str, QuestionType] = {
	"Short Text": QuestionType(text_type(SHORT_TEXT_MAX_LENGTH), max_length=SHORT_TEXT_MAX_LENGTH),
	"Long Text": QuestionType(text_type(LONG_TEXT_MAX_LENGTH), max_length=LONG_TEXT_MAX_LENGTH),
	"Number": QuestionType(normalize_number),
	"Currency": QuestionType(normalize_currency),
	"Yes/No": QuestionType(normalize_yes_no),
	"Single Select (Radio)": QuestionType(normalize_one_of, needs_options=True),
	"Multiple Select": QuestionType(normalize_many_of, needs_options=True),
	"Dropdown": QuestionType(normalize_one_of, needs_options=True),
	"Date": QuestionType(normalize_date),
	"URL": QuestionType(normalize_url),
	"Email": QuestionType(normalize_email),
}


def parse_options(options: str | None) -> list[str]:
	"""Options are entered one per line; blank lines and repeats are ignored"""
	seen = []
	for line in cstr(options).split("\n"):
		option = line.strip()
		if option and option not in seen:
			seen.append(option)
	return seen


def is_empty(value: object) -> bool:
	return value is None or value == [] or (isinstance(value, str) and not value.strip())


def normalize_answer(question: frappe._dict, value: object) -> Normalized | None:
	"""Validate and normalize one answer. None means not answered."""
	question_type = QUESTION_TYPES.get(question.question_type)
	if not question_type:
		raise ScreeningAnswerError(_("has an unknown question type {0}").format(question.question_type))
	if is_empty(value):
		return None
	if isinstance(value, str) and len(value) > MAX_RAW_ANSWER_LENGTH:
		raise ScreeningAnswerError(_("is too long"))

	normalized = question_type.normalize(value, question)
	return normalized if normalized.answer else None


# QUESTIONS


def get_active_questions(job_opening: str | None) -> list[frappe._dict]:
	"""Active screening questions of a published, open Job Opening (empty list otherwise)"""
	if not job_opening or not frappe.get_meta("Job Opening").has_field("custom_screening_questions"):
		return []

	opening = frappe.db.get_value("Job Opening", job_opening, ["publish", "status", "currency"], as_dict=True)
	if not opening or not opening.publish or opening.status != "Open":
		return []

	questions = frappe.get_all(
		QUESTION_DOCTYPE,
		filters={
			"parent": job_opening,
			"parenttype": "Job Opening",
			"parentfield": "custom_screening_questions",
			"is_active": 1,
		},
		fields=list(QUESTION_FIELDS),
		order_by="idx asc",
		limit=MAX_QUESTIONS,
	)
	for question in questions:
		if question.question_type == "Currency" and not question.currency:
			question.currency = opening.currency
	return questions


def to_public_question(question: frappe._dict) -> dict:
	"""What the public application form needs to render and pre-validate a question"""
	question_type = QUESTION_TYPES.get(question.question_type)
	cap = question_type.max_length if question_type else None
	return {
		"question_row": question.name,
		"question": question.question,
		"question_type": question.question_type,
		"options": parse_options(question.options) if question_type and question_type.needs_options else [],
		"is_mandatory": cint(question.is_mandatory),
		"description": question.description or "",
		"min_value": flt(question.min_value) or None,
		"max_value": flt(question.max_value) or None,
		"min_length": cint(question.min_length) or None,
		"max_length": min(cint(question.max_length) or cap, cap) if cap else None,
		"currency": question.currency or None,
	}


def validate_question_config(row) -> list[str]:
	"""Problems with one Job Opening (Template) screening question, as messages"""
	messages = []
	question_type = QUESTION_TYPES.get(row.question_type)
	if not question_type:
		return [_("unknown question type {0}").format(row.question_type)]

	if question_type.needs_options:
		lines = [line.strip() for line in cstr(row.options).split("\n") if line.strip()]
		if not lines:
			messages.append(_("add at least one option, one per line"))
		elif len({line.lower() for line in lines}) != len(lines):
			messages.append(_("options must not repeat"))

	if flt(row.min_value) and flt(row.max_value) and flt(row.min_value) > flt(row.max_value):
		messages.append(_("Minimum Value can't be more than Maximum Value"))

	if cint(row.min_length) < 0 or cint(row.max_length) < 0:
		messages.append(_("lengths can't be negative"))
	if cint(row.max_length) and cint(row.min_length) > cint(row.max_length):
		messages.append(_("Minimum Length can't be more than Maximum Length"))
	if question_type.max_length and cint(row.max_length) > question_type.max_length:
		messages.append(
			_("Maximum Length can be at most {0} for {1}").format(question_type.max_length, row.question_type)
		)
	return messages


# ANSWERS


def build_screening_responses(
	questions: list[frappe._dict], posted_rows: list
) -> tuple[list[dict], list[str]]:
	"""Rebuild the answer rows from the questions being asked; posted rows only supply answers.

	Posted rows are matched on question_row, falling back to the question text for forms cached before
	question_row existed. Answers to unknown or inactive questions are dropped, and the question text,
	type and typed values always come from the Job Opening, never from the post.
	"""
	by_row, by_text = {}, {}
	for row in (posted_rows or [])[: MAX_QUESTIONS * 2]:
		row = row.as_dict() if hasattr(row, "as_dict") else frappe._dict(row or {})
		question_row = cstr(row.get("question_row")).strip()
		if question_row:
			by_row.setdefault(question_row, row.get("answer"))
		else:
			by_text.setdefault(cstr(row.get("question")).strip(), row.get("answer"))

	rows, errors = [], []
	for question in questions:
		if question.name in by_row:
			raw = by_row[question.name]
		else:
			raw = by_text.get(cstr(question.question).strip())

		try:
			answer = normalize_answer(question, raw)
		except ScreeningAnswerError as error:
			errors.append(f"{escape_html(question.question)}: {error}")
			continue

		if not answer and question.is_mandatory:
			errors.append(_("{0}: an answer is required").format(escape_html(question.question)))
			continue

		rows.append(
			{
				"question": question.question,
				"question_type": question.question_type,
				"question_row": question.name,
				"answer": answer.answer if answer else "",
				"answer_number": answer.number if answer else None,
				"answer_date": answer.date if answer else None,
				"currency": answer.currency if answer else None,
			}
		)
	return rows, errors


def refresh_typed_values(row) -> None:
	"""Keep answer_number / answer_date in step with answers edited from Desk (options aren't known here)"""
	if row.question_type not in ("Number", "Currency", "Date"):
		return
	try:
		answer = normalize_answer(frappe._dict(question_type=row.question_type), row.answer)
	except ScreeningAnswerError:
		answer = None
	row.answer_number = answer.number if answer else None
	row.answer_date = answer.date if answer else None


# EXPERIENCE & EDUCATION


def validate_work_experience(rows: list, strict: bool) -> list[str]:
	"""Date order always; on web form applications also required values, the row cap and no future dates"""
	messages = []
	if strict and len(rows) > MAX_HISTORY_ROWS:
		messages.append(_("Add at most {0} work experience entries").format(MAX_HISTORY_ROWS))

	current_date = getdate(today())
	for row in rows:
		label = _("Work Experience row {0}").format(row.idx)
		if row.currently_working:
			row.to_date = None
		if row.from_date and row.to_date and getdate(row.to_date) < getdate(row.from_date):
			messages.append(_("{0}: To Date can't be before From Date").format(label))

		if not strict:
			continue
		if not cstr(row.company_name).strip():
			messages.append(_("{0}: Company is required").format(label))
		if not row.from_date:
			messages.append(_("{0}: From Date is required").format(label))
		elif getdate(row.from_date) > current_date:
			messages.append(_("{0}: From Date can't be in the future").format(label))
		if not row.currently_working and not row.to_date:
			messages.append(_("{0}: add a To Date, or tick Current").format(label))
		elif row.to_date and getdate(row.to_date) > current_date:
			messages.append(_("{0}: To Date can't be in the future").format(label))
	return messages


def validate_education(doc, strict: bool) -> list[str]:
	"""On web form applications: drop empty rows, cap the rows and check the year of passing"""
	if not strict:
		return []

	rows = [
		row
		for row in doc.get("custom_education") or []
		if cstr(row.school_univ).strip() or cstr(row.qualification).strip()
	]
	doc.set("custom_education", rows)

	messages = []
	if len(rows) > MAX_HISTORY_ROWS:
		messages.append(_("Add at most {0} education entries").format(MAX_HISTORY_ROWS))
	latest_year = getdate(today()).year + 10
	for row in rows:
		if row.year_of_passing and not 1900 <= cint(row.year_of_passing) <= latest_year:
			messages.append(_("Education row {0}: Year of Passing looks wrong").format(row.idx))
	return messages


def get_total_experience_years(rows: list) -> float:
	"""Years worked across all entries, counting overlapping periods once"""
	current_date = getdate(today())
	periods = []
	for row in rows:
		if not row.from_date:
			continue
		end = current_date if row.currently_working else row.to_date
		if not end:
			continue
		start, end = getdate(row.from_date), min(getdate(end), current_date)
		if end >= start:
			periods.append((start, end))

	days, last_end = 0, None
	for start, end in sorted(periods):
		if last_end and start <= last_end:
			if end > last_end:
				days += (end - last_end).days
				last_end = end
			continue
		days += (end - start).days + 1
		last_end = end
	return round(days / 365.25, 1)


def format_experience_duration(from_date, to_date) -> str:
	"""e.g. '2 years 3 months', for Employee External Work History's text field"""
	from dateutil.relativedelta import relativedelta

	if not from_date or not to_date or getdate(to_date) < getdate(from_date):
		return ""
	delta = relativedelta(getdate(to_date), getdate(from_date))
	parts = []
	if delta.years:
		parts.append(
			_("{0} year").format(delta.years) if delta.years == 1 else _("{0} years").format(delta.years)
		)
	if delta.months:
		parts.append(
			_("{0} month").format(delta.months) if delta.months == 1 else _("{0} months").format(delta.months)
		)
	return " ".join(parts) or _("less than a month")
