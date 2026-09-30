import frappe
from frappe.query_builder.functions import Avg
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, get_fullname

from hrms.hr.screening import get_active_questions, to_public_question


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=60, seconds=60)
def get_screening_questions(job_opening: str) -> list[dict]:
	"""Questions for the public application form: active ones of a published, open opening, at most 50"""
	return [to_public_question(question) for question in get_active_questions(job_opening)]


@frappe.whitelist()
def get_candidate_summary(job_applicant: str) -> dict:
	frappe.has_permission("Job Applicant", "read", job_applicant, throw=True)

	job_opening = frappe.db.get_value("Job Applicant", job_applicant, "job_title")
	summary = {
		# the applicant only stores the Job Opening's name (e.g. HR-OPN-2026-0004)
		"job_opening_title": job_opening and frappe.db.get_value("Job Opening", job_opening, "job_title"),
		"interviews": [],
		"feedback": [],
		"skill_ratings": [],
		"pending_feedback": [],
		# ratings are stored as a fraction of this many stars
		"rating_scale": cint(frappe.get_meta("Interview").get_options("average_rating")) or 5,
	}
	if not frappe.has_permission("Interview", "read"):
		return summary

	interviews = frappe.get_list(
		"Interview",
		filters={"job_applicant": job_applicant, "docstatus": ["!=", 2]},
		fields=[
			"name",
			"interview_type",
			"scheduled_on",
			"from_time",
			"to_time",
			"status",
			"average_rating",
			"docstatus",
		],
		order_by="scheduled_on asc, from_time asc",
	)
	if not interviews:
		return summary

	interview_names = [interview.name for interview in interviews]
	interviewers = frappe.get_all(
		"Interview Detail",
		filters={"parent": ["in", interview_names], "parenttype": "Interview"},
		fields=["parent", "interviewer"],
		order_by="idx asc",
	)
	submitted_by = {
		(row.interview, row.interviewer)
		for row in frappe.get_all(
			"Interview Feedback",
			filters={"interview": ["in", interview_names], "docstatus": 1},
			fields=["interview", "interviewer"],
		)
	}

	interviews_by_name = {interview.name: interview for interview in interviews}
	for interview in interviews:
		interview.interviewers = []

	for row in interviewers:
		if not row.interviewer:
			continue

		interviewer = {"user": row.interviewer, "full_name": get_fullname(row.interviewer)}
		interview = interviews_by_name[row.parent]
		interview.interviewers.append(interviewer)

		if interview.status != "Cancelled" and (row.parent, row.interviewer) not in submitted_by:
			summary["pending_feedback"].append(
				{"interview": row.parent, "interview_type": interview.interview_type, **interviewer}
			)

	summary["interviews"] = interviews

	if frappe.has_permission("Interview Feedback", "read"):
		feedback = frappe.get_list(
			"Interview Feedback",
			filters={"interview": ["in", interview_names], "docstatus": 1},
			fields=[
				"name",
				"interview",
				"interview_type",
				"interviewer",
				"average_rating",
				"result",
				"feedback",
				"modified",
			],
			order_by="creation asc",
		)
		for row in feedback:
			row.interviewer_name = get_fullname(row.interviewer)

		summary["feedback"] = feedback
		summary["skill_ratings"] = get_skill_ratings([row.name for row in feedback])

	return summary


def get_skill_ratings(feedback_names: list[str]) -> list[dict]:
	"""Average rating per skill across the given (submitted) Interview Feedback entries"""
	if not feedback_names:
		return []

	skill_assessment = frappe.qb.DocType("Skill Assessment")
	return (
		frappe.qb.from_(skill_assessment)
		.select(skill_assessment.skill, Avg(skill_assessment.rating).as_("rating"))
		.where(
			(skill_assessment.parenttype == "Interview Feedback")
			& (skill_assessment.parent.isin(feedback_names))
		)
		.groupby(skill_assessment.skill)
		.orderby(skill_assessment.skill)
	).run(as_dict=True)


@frappe.whitelist()
def get_mentionable_users() -> list[dict]:
	"""Same user list Desk offers for @mentions, shaped for the frappe-ui TextEditor"""
	from frappe.desk.search import get_users_for_mentions

	users = frappe.cache.get_value("users_for_mentions", get_users_for_mentions)
	return [{"label": user.get("value") or user.get("id"), "value": user.get("id")} for user in users]
