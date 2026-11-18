import base64
import binascii
import json
from urllib.parse import unquote, urlparse

import frappe
from frappe import _
from frappe.utils import cstr, now_datetime

from hrms.hr.screening import (
	build_screening_responses,
	get_active_questions,
	get_total_experience_years,
	is_web_url,
	refresh_typed_values,
	validate_education,
	validate_work_experience,
)

SOCIAL_LINK_FIELDS = ("custom_github_profile", "custom_portfolio_url", "custom_other_profile_url")
PDF_SIGNATURE = b"%PDF-"


def before_insert(doc, method=None):
	# applications from the public job_application web form: nothing posted is trusted
	if frappe.flags.in_web_form:
		validate_web_form_application(doc)


def validate(doc, method=None):
	set_consent_timestamp(doc)
	check_work_experience(doc)
	if not frappe.flags.in_web_form:
		for row in doc.get("custom_screening_responses") or []:
			refresh_typed_values(row)


def validate_web_form_application(doc):
	validate_job_opening_is_published(doc)
	validate_web_form_consent(doc)

	messages = []
	messages += validate_resume(doc)
	messages += validate_links(doc)
	messages += set_screening_responses_from_job_opening(doc)
	if doc.meta.has_field("custom_work_experience"):
		messages += validate_work_experience(doc.get("custom_work_experience") or [], strict=True)
	if doc.meta.has_field("custom_education"):
		messages += validate_education(doc, strict=True)

	if messages:
		frappe.throw("<br>".join(messages), title=_("Please check your application"))


def validate_job_opening_is_published(doc):
	# closed openings are already rejected by JobApplicant.before_insert
	if doc.job_title and frappe.db.get_value("Job Opening", doc.job_title, "publish") == 0:
		frappe.throw(
			_("This job opening is not accepting applications through the website."),
			title=_("Not Accepting Applications"),
		)


def validate_web_form_consent(doc):
	# the web form marks the checkbox mandatory, but a mandatory Check with value 0 isn't rejected server-side
	if doc.meta.has_field("custom_consent_given") and not doc.custom_consent_given:
		frappe.throw(
			_("Please consent to the processing of your personal data to submit the application."),
			title=_("Consent Required"),
		)


def get_posted_web_form_value(fieldname: str):
	"""A value as posted to the web form.

	Uploaded files arrive as data URLs that the web form clears from the document until after insert,
	so Attach fields are empty in before_insert even when a file was uploaded.
	"""
	data = frappe.form_dict.get("data")
	if isinstance(data, str):
		try:
			data = json.loads(data)
		except ValueError:
			return None
	return data.get(fieldname) if isinstance(data, dict) else None


def validate_resume(doc) -> list[str]:
	resume_link = cstr(doc.resume_link).strip()
	if resume_link and not is_web_url(resume_link):
		return [_("Resume Link must be a valid link starting with http:// or https://")]

	upload = cstr(doc.resume_attachment or get_posted_web_form_value("resume_attachment")).strip()
	if upload:
		return [] if is_pdf_upload(upload) else [_("Your resume must be a PDF file (.pdf)")]
	if resume_link:
		return []
	return [_("Please attach your resume or add a link to it")]


def is_pdf_upload(value: str) -> bool:
	"""Whether an uploaded resume is a PDF, by extension, declared type and the file's first bytes.

	The web form posts either the URL of a file uploaded beforehand, or "<file name>,<data URL>",
	which it saves as a File after insert. Links elsewhere belong in Resume Link, not here.
	"""
	if value.startswith(("/files/", "/private/files/")):
		path = unquote(urlparse(value).path)
		return path.lower().endswith(".pdf") and read_file_start(value).startswith(PDF_SIGNATURE)

	filename, _sep, dataurl = value.partition(",")
	header, _sep, content = dataurl.partition(",")
	if not (header.startswith("data:") and header.endswith(";base64")):
		return False
	if not filename.lower().endswith(".pdf") or header[5:].split(";")[0] != "application/pdf":
		return False
	try:
		# 8 base64 characters decode to the first 6 bytes
		return base64.b64decode(content.strip()[:8]).startswith(PDF_SIGNATURE)
	except (binascii.Error, ValueError):
		return False


def read_file_start(file_url: str, size: int = 8) -> bytes:
	"""First bytes of a local File, or b"" if there is no such File"""
	name = frappe.db.get_value("File", {"file_url": file_url, "is_folder": 0}, "name")
	if not name:
		return b""
	try:
		with open(frappe.get_doc("File", name).get_full_path(), "rb") as f:
			return f.read(size)
	except (OSError, frappe.ValidationError):
		# unreadable, or a path File refuses to resolve
		return b""


def validate_links(doc) -> list[str]:
	return [
		_("{0} must be a valid link starting with http:// or https://").format(_(doc.meta.get_label(field)))
		for field in ("custom_linkedin_profile", *SOCIAL_LINK_FIELDS)
		if doc.meta.has_field(field) and doc.get(field) and not is_web_url(cstr(doc.get(field)).strip())
	]


def set_screening_responses_from_job_opening(doc) -> list[str]:
	"""Rebuild the answers from the Job Opening's active questions (see build_screening_responses)"""
	if not doc.meta.has_field("custom_screening_responses"):
		return []

	rows, messages = build_screening_responses(
		get_active_questions(doc.job_title), doc.get("custom_screening_responses") or []
	)
	doc.set("custom_screening_responses", rows)
	return messages


def check_work_experience(doc):
	if not doc.meta.has_field("custom_work_experience"):
		return

	rows = doc.get("custom_work_experience") or []
	messages = validate_work_experience(rows, strict=False)
	if messages:
		frappe.throw("<br>".join(messages), title=_("Invalid Work Experience"))

	if doc.meta.has_field("custom_total_experience_years"):
		doc.custom_total_experience_years = get_total_experience_years(rows)


def set_consent_timestamp(doc):
	"""Record when consent was given. Server-side only, so the value can't be supplied or backdated by the client"""
	if not doc.meta.has_field("custom_consent_given_on"):
		return

	if not doc.custom_consent_given:
		doc.custom_consent_given_on = None
		return

	previous = doc.get_doc_before_save()
	if previous and previous.custom_consent_given and previous.custom_consent_given_on:
		doc.custom_consent_given_on = previous.custom_consent_given_on
	else:
		doc.custom_consent_given_on = now_datetime()
