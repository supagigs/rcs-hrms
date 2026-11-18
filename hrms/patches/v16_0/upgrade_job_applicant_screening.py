import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import get_custom_fields

QUESTION = "Job Opening Screening Question"
RESPONSE = "Job Applicant Screening Response"


def execute():
	"""Typed screening questions, experience & education and social links for Job Applicant.

	Upgrades the screening child doctypes in place: existing rows are kept and only filled in.
	Runs in pre_model_sync, so the job_application web form can reference the new fields when it syncs.
	"""
	sync_recruitment_child_doctypes()

	# questions and answers created before question types existed were plain text
	frappe.db.set_value(
		QUESTION, {"question_type": ("is", "not set")}, "question_type", "Short Text", update_modified=False
	)
	frappe.db.set_value(
		RESPONSE, {"question_type": ("is", "not set")}, "question_type", "Short Text", update_modified=False
	)
	backfill_question_rows()

	custom_fields = get_custom_fields()
	create_custom_fields(
		{
			doctype: custom_fields[doctype]
			for doctype in ("Job Applicant", "Job Opening", "Job Opening Template")
		},
		ignore_validate=True,
	)


def sync_recruitment_child_doctypes():
	"""Sync the child doctypes used by the recruitment custom fields' Table fields.

	Shared with add_job_applicant_candidate_fields, which can run first on sites that have neither patch.
	Whichever adds `is_active` marks the existing questions active: they were all being asked until now.
	"""
	adds_is_active = frappe.db.table_exists(QUESTION) and not frappe.db.has_column(QUESTION, "is_active")

	for doctype in (
		"job_applicant_screening_response",
		"job_opening_screening_question",
		"job_applicant_work_experience",
	):
		frappe.reload_doc("hr", "doctype", doctype)

	if adds_is_active:
		frappe.db.set_value(QUESTION, {"is_active": 0}, "is_active", 1, update_modified=False)


def backfill_question_rows():
	"""Link existing answers to their question row, matching on the question text within the applicant's opening"""
	responses = frappe.get_all(
		RESPONSE,
		filters={"parenttype": "Job Applicant", "question_row": ("is", "not set")},
		fields=["name", "parent", "question"],
	)
	if not responses:
		return

	opening_by_applicant = dict(
		frappe.get_all(
			"Job Applicant",
			filters={"name": ("in", {row.parent for row in responses})},
			fields=["name", "job_title"],
			as_list=True,
		)
	)
	openings = {opening for opening in opening_by_applicant.values() if opening}
	if not openings:
		return

	question_rows = {}
	for question in frappe.get_all(
		QUESTION,
		filters={"parenttype": "Job Opening", "parent": ("in", openings)},
		fields=["name", "parent", "question"],
	):
		question_rows.setdefault((question.parent, (question.question or "").strip()), question.name)

	for response in responses:
		opening = opening_by_applicant.get(response.parent)
		question_row = question_rows.get((opening, (response.question or "").strip()))
		if question_row:
			frappe.db.set_value(RESPONSE, response.name, "question_row", question_row, update_modified=False)
