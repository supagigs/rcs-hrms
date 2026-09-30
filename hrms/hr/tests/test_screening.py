import json
import re
from unittest.mock import patch

import frappe
from frappe.utils import add_days, add_years, getdate, nowdate
from frappe.website.doctype.web_form.web_form import accept

from hrms.hr.doctype.employee_referral.employee_referral import create_job_applicant
from hrms.hr.doctype.employee_referral.test_employee_referral import create_employee_referral
from hrms.hr.doctype.job_applicant.job_applicant import make_employee as map_applicant_to_employee
from hrms.hr.screening import (
	QUESTION_DOCTYPE,
	QUESTION_TYPES,
	ScreeningAnswerError,
	format_experience_duration,
	get_total_experience_years,
	normalize_answer,
	parse_options,
	validate_question_config,
)
from hrms.overrides.job_applicant import is_pdf_upload
from hrms.tests.utils import HRMSTestSuite

EVERY_TYPE = [
	{"question": "Your name as on your ID?", "question_type": "Short Text", "is_mandatory": 1},
	{"question": "Tell us about a project", "question_type": "Long Text"},
	{"question": "Notice period in days", "question_type": "Number", "min_value": 1, "max_value": 90},
	{"question": "Expected monthly salary", "question_type": "Currency"},
	{"question": "Can you relocate?", "question_type": "Yes/No", "is_mandatory": 1},
	{"question": "Preferred shift", "question_type": "Single Select (Radio)", "options": "Day\nNight"},
	{
		"question": "Languages you use",
		"question_type": "Multiple Select",
		"options": "Python\nSQL\nJavaScript",
	},
	{"question": "Highest degree", "question_type": "Dropdown", "options": "Bachelor\nMaster\nDoctorate"},
	{"question": "Available from", "question_type": "Date"},
	{"question": "Code sample link", "question_type": "URL"},
	{"question": "Reference email", "question_type": "Email"},
	{"question": "No longer asked", "question_type": "Short Text", "is_active": 0},
]


def make_opening(questions=None, **kwargs):
	opening = frappe.get_doc(
		{
			"doctype": "Job Opening",
			"job_title": f"Screening Test {frappe.generate_hash(length=8)}",
			"designation": "Designer",
			"company": "_Test Company",
			"status": "Open",
			"publish": 1,
			"currency": "INR",
			"custom_screening_questions": questions or [],
			**kwargs,
		}
	)
	return opening.insert()


def question_rows(opening):
	"""question text -> question row name"""
	return {row.question: row.name for row in opening.custom_screening_questions}


def apply_via_web_form(**data):
	"""What web_form.accept() does for a new applicant: the in_web_form flag, the raw posted data, insert"""
	data.setdefault("applicant_name", "Web Applicant")
	data.setdefault("email_id", f"web.{frappe.generate_hash(length=8)}@example.com")
	data.setdefault("custom_consent_given", 1)
	if "resume_attachment" not in data:
		data.setdefault("resume_link", "https://example.com/resume.pdf")

	frappe.flags.in_web_form = True
	frappe.form_dict.data = json.dumps(data)
	try:
		doc = frappe.get_doc({"doctype": "Job Applicant", **data})
		# uploads can come in as "<file name>,<data URL>"; accept() blanks them until after insert
		if "base64" in str(data.get("resume_attachment") or ""):
			doc.resume_attachment = ""
		return doc.insert(ignore_permissions=True, ignore_mandatory=True)
	finally:
		frappe.flags.in_web_form = False
		frappe.form_dict.pop("data", None)


PDF_UPLOAD = "resume.pdf,data:application/pdf;base64,JVBERi0xLjQK"  # "%PDF-1.4"


WEB_FORM = "job-application"
WEB_FORM_SCRIPT = ("public", "js", "recruitment", "job_application_form.js")
REGISTRY_KEY = re.compile(r'^(?:"([^"]+)"|([A-Za-z_$][\w$]*))\s*:')


def read_web_form_script() -> str:
	with open(frappe.get_app_path("hrms", *WEB_FORM_SCRIPT)) as f:
		return f.read()


def get_client_question_types(source: str) -> list[str]:
	"""Top-level keys of `const QUESTION_TYPES = {...}` in the web form script, in order"""
	marker = "const QUESTION_TYPES = {"
	i = source.index(marker) + len(marker)
	entries, entry, depth, quote = [], [], 0, None
	while True:
		char = source[i]
		if quote:
			if char == "\\":
				entry.append(source[i : i + 2])
				i += 2
				continue
			if char == quote:
				quote = None
		elif source.startswith("//", i):
			i = source.index("\n", i)
			continue
		elif char in "\"'`":
			quote = char
		elif char in "([{":
			depth += 1
		elif char in ")]}":
			if depth == 0:
				entries.append("".join(entry))
				break
			depth -= 1
		elif char == "," and depth == 0:
			entries.append("".join(entry))
			entry = []
			i += 1
			continue
		entry.append(char)
		i += 1

	keys = []
	for text in entries:
		if not text.strip():
			continue  # trailing comma
		match = REGISTRY_KEY.match(text.strip())
		keys.append(match.group(1) or match.group(2))
	return keys


class TestScreeningRegistry(HRMSTestSuite):
	def test_question_types_match_select_options(self):
		options = frappe.get_meta(QUESTION_DOCTYPE).get_field("question_type").options.split("\n")
		self.assertEqual(options, list(QUESTION_TYPES))

	def test_client_registry_matches_server(self):
		"""The web form script, the server registry and the Select options list the same types"""
		options = frappe.get_meta(QUESTION_DOCTYPE).get_field("question_type").options.split("\n")
		client = get_client_question_types(read_web_form_script())
		self.assertEqual(len(client), len(set(client)), "a type is listed twice in the client registry")
		self.assertEqual(set(client), set(QUESTION_TYPES))
		self.assertEqual(set(client), set(options))

	def test_web_form_script_survives_jinja(self):
		# webform_include_js files are rendered through Jinja before being inlined in the page
		source = read_web_form_script()
		self.assertEqual(frappe.render_template(source, {}).rstrip("\n"), source.rstrip("\n"))
		self.assertNotIn("</script", source.lower())

	def test_parse_options(self):
		self.assertEqual(parse_options(" A\n\nB\nA \n"), ["A", "B"])
		self.assertEqual(parse_options(None), [])

	def assert_normalized(self, question, value, answer, number=None, date=None, currency=None):
		result = normalize_answer(frappe._dict(question), value)
		self.assertEqual(
			(result.answer, result.number, result.date, result.currency), (answer, number, date, currency)
		)

	def assert_rejected(self, question, value):
		self.assertRaises(ScreeningAnswerError, normalize_answer, frappe._dict(question), value)

	def test_empty_answers_are_unanswered(self):
		for value in (None, "", "   ", []):
			self.assertIsNone(normalize_answer(frappe._dict(question_type="Short Text"), value))
		self.assertIsNone(normalize_answer(frappe._dict(question_type="Multiple Select", options="A"), "[]"))

	def test_unknown_type(self):
		self.assert_rejected({"question_type": "Signature"}, "x")

	def test_text(self):
		short = {"question_type": "Short Text"}
		self.assert_normalized(short, "  hello ", "hello")
		self.assert_rejected(short, "x" * 141)
		self.assert_rejected({**short, "max_length": 5}, "123456")
		self.assert_rejected({**short, "min_length": 3}, "ab")
		self.assert_rejected(short, ["not", "text"])
		self.assert_normalized({"question_type": "Long Text"}, "x" * 2000, "x" * 2000)
		self.assert_rejected({"question_type": "Long Text"}, "x" * 2001)
		# a configured max above the cap is still capped
		self.assert_rejected({**short, "max_length": 500}, "x" * 141)

	def test_number(self):
		number = {"question_type": "Number", "min_value": 1, "max_value": 90}
		self.assert_normalized(number, "30", "30", number=30.0)
		self.assert_normalized({"question_type": "Number"}, "1,200.50", "1200.5", number=1200.5)
		for value in ("abc", "nan", "inf", True, "0", "91"):
			self.assert_rejected(number, value)

	def test_currency(self):
		currency = {"question_type": "Currency", "currency": "INR"}
		self.assert_normalized(currency, 45000, "45000", number=45000.0, currency="INR")
		self.assert_rejected(currency, "-1")

	def test_yes_no(self):
		self.assert_normalized({"question_type": "Yes/No"}, "yes", "Yes")
		self.assert_normalized({"question_type": "Yes/No"}, "No", "No")
		self.assert_rejected({"question_type": "Yes/No"}, "maybe")

	def test_single_select_and_dropdown(self):
		for question_type in ("Single Select (Radio)", "Dropdown"):
			question = {"question_type": question_type, "options": "Day\nNight"}
			self.assert_normalized(question, "Night", "Night")
			self.assert_normalized(question, ["Day"], "Day")
			self.assert_rejected(question, "Evening")
			self.assert_rejected(question, ["Day", "Night"])

	def test_multiple_select(self):
		question = {"question_type": "Multiple Select", "options": "Python\nSQL\nJavaScript"}
		# stored in option order, one per line, without repeats
		self.assert_normalized(question, "SQL\nPython\nSQL", "Python\nSQL")
		self.assert_normalized(question, ["JavaScript", "Python"], "Python\nJavaScript")
		self.assert_normalized(question, '["SQL"]', "SQL")
		self.assert_rejected(question, ["Python", "Rust"])
		self.assert_rejected(question, "[not json")
		self.assert_rejected(question, {"Python": 1})

	def test_date(self):
		self.assert_normalized({"question_type": "Date"}, "2026-01-05", "2026-01-05", date="2026-01-05")
		for value in ("05-01-2026", "2026-02-30", "soon", "1800-01-01"):
			self.assert_rejected({"question_type": "Date"}, value)

	def test_url(self):
		self.assert_normalized({"question_type": "URL"}, "https://example.com/a", "https://example.com/a")
		for value in ("http:abc", "javascript:alert(1)", "/relative", "ftp://example.com", "https://x"):
			self.assert_rejected({"question_type": "URL"}, value)

	def test_email(self):
		self.assert_normalized({"question_type": "Email"}, "ref@example.com", "ref@example.com")
		for value in ("nope", "a@example.com, b@example.com"):
			self.assert_rejected({"question_type": "Email"}, value)

	def test_question_config(self):
		def config(**row):
			return validate_question_config(frappe._dict(row))

		self.assertEqual(config(question_type="Dropdown", options="A\nB"), [])
		self.assertTrue(config(question_type="Dropdown", options=""))
		self.assertTrue(config(question_type="Multiple Select", options="A\na"))
		self.assertTrue(config(question_type="Number", min_value=10, max_value=5))
		self.assertTrue(config(question_type="Short Text", max_length=500))
		self.assertTrue(config(question_type="Short Text", min_length=10, max_length=5))
		self.assertTrue(config(question_type="Signature"))

	def test_total_experience(self):
		row = frappe._dict
		two_years = row(from_date=add_years(nowdate(), -3), to_date=add_years(nowdate(), -1))
		overlapping = row(from_date=add_years(nowdate(), -2), to_date=add_years(nowdate(), -1))
		current = row(from_date=add_years(nowdate(), -1), currently_working=1)
		self.assertAlmostEqual(get_total_experience_years([two_years, overlapping]), 2.0, delta=0.1)
		self.assertAlmostEqual(get_total_experience_years([two_years, current]), 3.0, delta=0.1)
		# rows without an end are ignored unless current
		self.assertEqual(get_total_experience_years([row(from_date=nowdate())]), 0)

	def test_experience_duration(self):
		self.assertEqual(format_experience_duration("2020-01-01", "2022-04-01"), "2 years 3 months")
		self.assertEqual(format_experience_duration("2020-01-01", "2020-01-10"), "less than a month")
		self.assertEqual(format_experience_duration("2020-01-01", None), "")


class TestWebFormApplication(HRMSTestSuite):
	def setUp(self):
		self.opening = make_opening(EVERY_TYPE)
		self.rows = question_rows(self.opening)

	def valid_answers(self):
		return {
			"Your name as on your ID?": "Web Applicant",
			"Can you relocate?": "Yes",
			"Notice period in days": "30",
			"Expected monthly salary": "45000",
			"Languages you use": "SQL\nPython",
			"Available from": "2026-11-01",
		}

	def answers_payload(self, answers):
		return [
			{"question_row": self.rows[question], "answer": answer} for question, answer in answers.items()
		]

	def test_opening_without_questions(self):
		applicant = apply_via_web_form(job_title=make_opening().name)
		self.assertEqual(applicant.custom_screening_responses, [])

	def test_answers_are_rebuilt_from_the_opening(self):
		posted = self.answers_payload(self.valid_answers())
		# tampering: reworded question, forged type/typed values, unknown and inactive questions
		posted[0].update(question="Forged question?", question_type="Number", answer_number=999)
		posted.append({"question_row": "not-a-real-row", "answer": "extra"})
		posted.append({"question_row": self.rows["No longer asked"], "answer": "sneaky"})
		# forms cached before question_row existed only send the question text
		posted.append({"question": "Preferred shift", "answer": "Night"})

		applicant = apply_via_web_form(job_title=self.opening.name, custom_screening_responses=posted)
		answers = {row.question: row for row in applicant.custom_screening_responses}

		active = [question["question"] for question in EVERY_TYPE if question.get("is_active", 1)]
		self.assertEqual(list(answers), active)
		self.assertNotIn("Forged question?", answers)
		self.assertNotIn("No longer asked", answers)

		name = answers["Your name as on your ID?"]
		self.assertEqual((name.question_type, name.answer), ("Short Text", "Web Applicant"))
		self.assertFalse(name.answer_number)
		self.assertEqual(name.question_row, self.rows["Your name as on your ID?"])
		self.assertEqual(answers["Preferred shift"].answer, "Night")
		self.assertEqual(answers["Languages you use"].answer, "Python\nSQL")
		self.assertEqual(answers["Notice period in days"].answer_number, 30)
		salary = answers["Expected monthly salary"]
		self.assertEqual((salary.answer_number, salary.currency), (45000, "INR"))
		self.assertEqual(getdate(answers["Available from"].answer_date), getdate("2026-11-01"))
		self.assertEqual(answers["Tell us about a project"].answer, "")

	def test_required_answer_missing(self):
		answers = self.valid_answers()
		del answers["Can you relocate?"]
		with self.assertRaisesRegex(frappe.ValidationError, "Can you relocate\\?: an answer is required"):
			apply_via_web_form(
				job_title=self.opening.name, custom_screening_responses=self.answers_payload(answers)
			)

	def test_invalid_answers(self):
		for question, answer in (
			("Preferred shift", "Evening"),
			("Languages you use", "Python\nRust"),
			("Highest degree", "PhD"),
			("Notice period in days", "120"),
			("Available from", "next week"),
			("Code sample link", "javascript:alert(1)"),
			("Reference email", "not-an-email"),
		):
			answers = {**self.valid_answers(), question: answer}
			with self.subTest(question=question), self.assertRaises(frappe.ValidationError):
				apply_via_web_form(
					job_title=self.opening.name, custom_screening_responses=self.answers_payload(answers)
				)

	def test_unpublished_opening(self):
		opening = make_opening(publish=0)
		with self.assertRaisesRegex(frappe.ValidationError, "not accepting applications"):
			apply_via_web_form(job_title=opening.name)

	def test_closed_opening(self):
		opening = make_opening()
		opening.db_set("status", "Closed")
		with self.assertRaisesRegex(frappe.ValidationError, "closed Job Opening"):
			apply_via_web_form(job_title=opening.name)

	def test_consent_required(self):
		with self.assertRaisesRegex(frappe.ValidationError, "consent"):
			apply_via_web_form(job_title=make_opening().name, custom_consent_given=0)

	def test_resume_required(self):
		opening = make_opening().name
		with self.assertRaisesRegex(frappe.ValidationError, "attach your resume"):
			apply_via_web_form(job_title=opening, resume_attachment="")
		with self.assertRaisesRegex(frappe.ValidationError, "Resume Link"):
			apply_via_web_form(job_title=opening, resume_link="javascript:alert(1)")

		# an uploaded file is blank on the document until after insert, but was posted
		applicant = apply_via_web_form(job_title=opening, resume_attachment=PDF_UPLOAD)
		self.assertTrue(applicant.name)

	def test_resume_upload_must_be_pdf(self):
		opening = make_opening().name
		for label, upload in (
			("word file", "resume.docx,data:application/msword;base64,UEsDBBQA"),
			("renamed to .pdf", "resume.pdf,data:application/pdf;base64,UEsDBBQA"),
			("pdf type, other name", "resume.doc,data:application/pdf;base64,JVBERi0xLjQK"),
			("not a data URL", "resume.pdf,JVBERi0xLjQK"),
			("a link", "https://example.com/resume.pdf"),
		):
			with self.subTest(label), self.assertRaisesRegex(frappe.ValidationError, "must be a PDF"):
				apply_via_web_form(job_title=opening, resume_attachment=upload)

		# files uploaded before submitting arrive as their URL; the check reads the file's start
		with patch("hrms.overrides.job_applicant.read_file_start", return_value=b"%PDF-1.7"):
			self.assertTrue(is_pdf_upload("/private/files/cv.pdf"))
			self.assertTrue(is_pdf_upload("/files/my%20cv.PDF"))
			self.assertFalse(is_pdf_upload("/private/files/cv.docx"))
		with patch("hrms.overrides.job_applicant.read_file_start", return_value=b"PK\x03\x04"):
			self.assertFalse(is_pdf_upload("/private/files/cv.pdf"))

		# a URL with no File behind it
		with self.assertRaisesRegex(frappe.ValidationError, "must be a PDF"):
			apply_via_web_form(job_title=opening, resume_attachment="/private/files/missing-cv.pdf")

		# the link alternative isn't a file and isn't checked for type
		self.assertTrue(
			apply_via_web_form(job_title=opening, resume_link="https://example.com/resume.docx").name
		)

	def test_social_links(self):
		with self.assertRaisesRegex(frappe.ValidationError, "GitHub"):
			apply_via_web_form(job_title=make_opening().name, custom_github_profile="http:abc")

	def test_experience_and_education(self):
		opening = make_opening().name
		past = add_years(nowdate(), -3)
		with self.assertRaisesRegex(frappe.ValidationError, "add a To Date, or tick Current"):
			apply_via_web_form(
				job_title=opening,
				custom_work_experience=[{"company_name": "Acme", "from_date": past}],
			)
		with self.assertRaisesRegex(frappe.ValidationError, "can't be in the future"):
			apply_via_web_form(
				job_title=opening,
				custom_work_experience=[
					{"company_name": "Acme", "from_date": add_days(nowdate(), 10), "currently_working": 1}
				],
			)
		with self.assertRaisesRegex(frappe.ValidationError, "at most 20"):
			apply_via_web_form(
				job_title=opening,
				custom_work_experience=[
					{"company_name": f"Acme {i}", "from_date": past, "to_date": add_years(nowdate(), -1)}
					for i in range(21)
				],
			)

		applicant = apply_via_web_form(
			job_title=opening,
			custom_work_experience=[
				{"company_name": "Acme", "from_date": past, "to_date": add_years(nowdate(), -1)},
				{"company_name": "Globex", "from_date": add_years(nowdate(), -1), "currently_working": 1},
			],
			custom_education=[
				{"school_univ": "Pune University", "qualification": "MCA", "year_of_passing": 2023},
				{"school_univ": "", "qualification": ""},
			],
		)
		self.assertAlmostEqual(applicant.custom_total_experience_years, 3.0, delta=0.1)
		self.assertEqual(len(applicant.custom_education), 1)


class TestWebFormAccept(HRMSTestSuite):
	"""The real Job Application web form: its field list, and web_form.accept() posted to as a guest"""

	STEP_FIELDS = (
		"custom_work_experience",
		"custom_education",
		"custom_github_profile",
		"custom_portfolio_url",
		"custom_other_profile_url",
		"screening_questions_html",
		"custom_screening_responses",
		"resume_attachment",
		"resume_link",
		"custom_consent_given",
	)

	def post(self, data):
		data = {"doctype": "Job Applicant", "web_form_name": WEB_FORM, **data}
		payload = json.dumps(data)
		frappe.form_dict.update(web_form=WEB_FORM, data=payload)
		frappe.set_user("Guest")
		try:
			return accept(web_form=WEB_FORM, data=payload)
		finally:
			frappe.set_user("Administrator")
			frappe.flags.in_web_form = False
			frappe.form_dict.pop("data", None)
			frappe.form_dict.pop("web_form", None)

	def test_web_form_fields(self):
		fields = frappe.get_doc("Web Form", WEB_FORM).web_form_fields
		by_name = {field.fieldname: field for field in fields if field.fieldname}
		missing = set(self.STEP_FIELDS) - set(by_name)
		self.assertFalse(missing, f"Web form is missing {missing}; run bench migrate to sync it")

		self.assertEqual(
			[field.label for field in fields if field.fieldtype == "Page Break"],
			["Experience & Education", "Social Links", "Screening Questions", "Documents & Consent"],
		)
		self.assertTrue(by_name["custom_screening_responses"].hidden)

		meta = frappe.get_meta("Job Applicant")
		for field in fields:
			if field.fieldname and field.fieldtype not in frappe.model.no_value_fields:
				self.assertTrue(meta.has_field(field.fieldname), field.fieldname)

	def test_accept(self):
		opening = make_opening(EVERY_TYPE)
		rows = question_rows(opening)
		past = add_years(nowdate(), -2)

		response = self.post(
			{
				"job_title": opening.name,
				"applicant_name": "Accepted Guest",
				"email_id": "accepted.guest@example.com",
				"resume_link": "https://example.com/resume.pdf",
				"custom_consent_given": 1,
				"custom_github_profile": "https://github.com/accepted-guest",
				"custom_work_experience": [
					{
						"company_name": "Acme",
						"designation": "Analyst",
						"from_date": past,
						"currently_working": 1,
					}
				],
				"custom_education": [{"school_univ": "Pune University", "qualification": "MCA"}],
				"custom_screening_responses": [
					{"question_row": rows["Your name as on your ID?"], "answer": "Accepted Guest"},
					{"question_row": rows["Can you relocate?"], "answer": "No", "question": "Forged?"},
					{"question_row": rows["Notice period in days"], "answer": "15"},
				],
				"screening_questions_html": "<img src=x onerror=alert(1)>",
				# not on the web form, so never set from the post
				"status": "Accepted",
				"custom_consent_given_on": "2000-01-01 00:00:00",
			}
		)

		applicant = frappe.get_doc("Job Applicant", response.name)
		self.assertEqual(applicant.name, "accepted.guest@example.com")
		self.assertEqual(applicant.status, "Open")
		self.assertNotEqual(str(applicant.custom_consent_given_on)[:4], "2000")
		self.assertEqual(applicant.custom_github_profile, "https://github.com/accepted-guest")
		self.assertEqual([row.company_name for row in applicant.custom_work_experience], ["Acme"])
		self.assertAlmostEqual(applicant.custom_total_experience_years, 2.0, delta=0.1)
		self.assertEqual([row.qualification for row in applicant.custom_education], ["MCA"])

		answers = {row.question: row for row in applicant.custom_screening_responses}
		self.assertNotIn("Forged?", answers)
		self.assertEqual(answers["Can you relocate?"].answer, "No")
		self.assertEqual(answers["Notice period in days"].answer_number, 15)

	def test_accept_rejects_invalid_applications(self):
		opening = make_opening(EVERY_TYPE)
		base = {
			"job_title": opening.name,
			"applicant_name": "Rejected Guest",
			"email_id": "rejected.guest@example.com",
			"resume_link": "https://example.com/resume.pdf",
			"custom_consent_given": 1,
		}
		# mandatory screening answers missing
		with self.assertRaisesRegex(frappe.ValidationError, "an answer is required"):
			self.post(base)
		with self.assertRaisesRegex(frappe.ValidationError, "not accepting applications"):
			self.post({**base, "job_title": make_opening(publish=0).name})
		self.assertFalse(frappe.db.exists("Job Applicant", "rejected.guest@example.com"))


class TestOtherApplicantPaths(HRMSTestSuite):
	"""Inserts that don't come from the web form must keep working with none of the new fields set"""

	def assert_untouched(self, applicant):
		self.assertEqual(applicant.custom_screening_responses, [])
		self.assertEqual(applicant.custom_work_experience, [])
		self.assertFalse(applicant.custom_consent_given_on)

	def test_email_style_insert(self):
		# what an Email Account with append_to = Job Applicant creates from an incoming email
		applicant = frappe.get_doc(
			{
				"doctype": "Job Applicant",
				"applicant_name": "Mail Sender",
				"email_id": "mail.sender@example.com",
			}
		).insert(ignore_permissions=True)
		self.assert_untouched(applicant)

	def test_employee_referral(self):
		referral = create_employee_referral(email="referred.screening@example.com")
		applicant = create_job_applicant(referral.name)
		self.assert_untouched(frappe.get_doc("Job Applicant", applicant.name))

	def test_data_import(self):
		frappe.flags.in_import = True
		try:
			applicant = frappe.get_doc(
				{
					"doctype": "Job Applicant",
					"applicant_name": "Imported Applicant",
					"email_id": "imported.applicant@example.com",
					"job_title": make_opening(EVERY_TYPE).name,
					"custom_screening_responses": [
						{"question": "Notice period in days", "question_type": "Number", "answer": "45"}
					],
				}
			).insert()
		finally:
			frappe.flags.in_import = False

		# imported answers are kept as given, only typed values are filled in
		self.assertEqual(len(applicant.custom_screening_responses), 1)
		self.assertEqual(applicant.custom_screening_responses[0].answer_number, 45)
		self.assertFalse(applicant.custom_consent_given_on)


class TestEmployeeCarryOver(HRMSTestSuite):
	def make_applicant(self):
		return frappe.get_doc(
			{
				"doctype": "Job Applicant",
				"applicant_name": "Carry Over",
				"email_id": f"carry.{frappe.generate_hash(length=6)}@example.com",
				"custom_education": [
					{
						"school_univ": "Pune University",
						"qualification": "MCA",
						"level": "Post Graduate",
						"year_of_passing": 2023,
					}
				],
				"custom_work_experience": [
					{
						"company_name": "Acme",
						"designation": "Intern",
						"location": "Mumbai",
						"from_date": "2022-01-01",
						"to_date": "2022-07-01",
					}
				],
			}
		).insert()

	def make_employee(self, applicant):
		employee = map_applicant_to_employee(applicant.name)
		employee.update(
			{
				"naming_series": "EMP-",
				"company": "_Test Company",
				"gender": "Female",
				"date_of_birth": "1995-01-01",
				"date_of_joining": nowdate(),
				"status": "Active",
			}
		)
		return employee

	def test_history_is_copied(self):
		applicant = self.make_applicant()
		employee = self.make_employee(applicant).insert()

		self.assertEqual(
			[
				(row.school_univ, row.qualification, row.level, row.year_of_passing)
				for row in employee.education
			],
			[("Pune University", "MCA", "Post Graduate", 2023)],
		)
		self.assertEqual(
			[
				(row.company_name, row.designation, row.address, row.total_experience)
				for row in employee.external_work_history
			],
			[("Acme", "Intern", "Mumbai", "6 months")],
		)

	def test_existing_history_is_kept(self):
		employee = self.make_employee(self.make_applicant())
		employee.append("education", {"school_univ": "Entered by HR"})
		employee.insert()
		self.assertEqual([row.school_univ for row in employee.education], ["Entered by HR"])
		self.assertEqual(len(employee.external_work_history), 1)
