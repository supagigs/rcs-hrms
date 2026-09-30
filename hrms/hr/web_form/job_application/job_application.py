import frappe

# Columns the Experience and Education grids show on the web form, with their widths. The row
# editor gets every field: by default a web form only sends a table's in-list-view fields, so
# fields like Location and Description could not be filled in at all.
TABLE_COLUMNS = {
	"custom_work_experience": {
		"company_name": 3,
		"designation": 2,
		"from_date": 2,
		"to_date": 2,
		"currently_working": 1,
	},
	"custom_education": {"school_univ": 3, "qualification": 3, "level": 2, "year_of_passing": 2},
}

# rendered differently on web forms (Link) or not supported in a row editor
SKIPPED_FIELDTYPES = ("Link", "Dynamic Link", "Table", "Table MultiSelect", "Attach", "Attach Image")


def get_context(context):
	web_form_doc = context.get("web_form_doc")
	if not web_form_doc or context.get("is_list"):
		return

	for field in web_form_doc.get("web_form_fields") or []:
		columns = TABLE_COLUMNS.get(field.get("fieldname"))
		if field.get("fieldtype") == "Table" and columns:
			field["fields"] = get_table_fields(field.get("options"), columns)

	# shown instead of the opening's ID; guests can't read Job Opening through the API
	opening = get_job_opening(frappe.form_dict.get("job_title"))
	web_form_doc["job_opening_title"] = opening.job_title if opening else None
	web_form_doc["job_opening_closed"] = bool(opening and opening.status != "Open")


def get_table_fields(child_doctype: str, columns: dict[str, int]) -> list[dict]:
	fields = []
	for df in frappe.get_meta(child_doctype).fields:
		if df.hidden or df.fieldtype in SKIPPED_FIELDTYPES:
			continue
		df = df.as_dict()
		df.in_list_view = int(df.fieldname in columns)
		df.columns = columns.get(df.fieldname) or 0
		fields.append(df)
	return fields


def get_job_opening(job_opening: str | None):
	if not job_opening or not isinstance(job_opening, str):
		return None
	return frappe.db.get_value(
		"Job Opening", {"name": job_opening, "publish": 1}, ["job_title", "status"], as_dict=True
	)
