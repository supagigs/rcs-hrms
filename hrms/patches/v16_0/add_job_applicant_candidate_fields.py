from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.patches.v16_0.upgrade_job_applicant_screening import sync_recruitment_child_doctypes
from hrms.setup import get_custom_fields, set_job_applicant_track_changes


def execute():
	# runs in pre_model_sync (so the job_application web form can reference these fields when it syncs),
	# hence the child doctypes used by the Table fields have to be synced here first
	sync_recruitment_child_doctypes()

	custom_fields = get_custom_fields()
	create_custom_fields(
		{doctype: custom_fields[doctype] for doctype in ("Job Applicant", "Job Opening")},
		ignore_validate=True,
	)

	set_job_applicant_track_changes()
