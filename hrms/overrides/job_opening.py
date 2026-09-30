import frappe
from frappe import _
from frappe.utils import escape_html

from hrms.hr.screening import RESPONSE_DOCTYPE, validate_question_config


def validate(doc, method=None):
	"""Job Opening and Job Opening Template: screening question settings"""
	if not doc.meta.has_field("custom_screening_questions"):
		return

	validate_screening_questions(doc)
	if doc.doctype == "Job Opening":
		warn_about_removed_questions_with_answers(doc)


def validate_screening_questions(doc):
	messages = []
	for row in doc.get("custom_screening_questions") or []:
		if row.question_type == "Currency" and not row.currency:
			row.currency = doc.get("currency")
		messages += [
			_("Screening Question row {0} ({1}): {2}").format(
				row.idx, escape_html(row.question or ""), message
			)
			for message in validate_question_config(row)
		]

	if messages:
		frappe.throw("<br>".join(messages), title=_("Invalid Screening Questions"))


def warn_about_removed_questions_with_answers(doc):
	before = doc.get_doc_before_save()
	if not before:
		return

	current = {row.name for row in doc.get("custom_screening_questions") or []}
	removed = [row.name for row in before.get("custom_screening_questions") or [] if row.name not in current]
	if removed and frappe.db.exists(RESPONSE_DOCTYPE, {"question_row": ("in", removed)}):
		frappe.msgprint(
			_(
				"Applicants have already answered a question you removed. Their answers are kept. "
				"To stop asking a question, untick Active instead of deleting it."
			),
			title=_("Removed Screening Question"),
			indicator="orange",
		)
