// Screening questions on Job Opening and Job Opening Template (doctype_js in hooks.py, loaded on top
// of the doctype's own script): show only the settings each question type uses, and copy a
// template's questions into an opening that has none yet.

(() => {
	const QUESTIONS = "custom_screening_questions";
	const QUESTION_DOCTYPE = "Job Opening Screening Question";

	// question settings -> the types they apply to (hrms/hr/screening.py reads them the same way)
	const SETTINGS = {
		min_value: ["Number", "Currency"],
		max_value: ["Number", "Currency"],
		currency: ["Currency"],
		min_length: ["Short Text", "Long Text"],
		max_length: ["Short Text", "Long Text"],
	};
	const SETTINGS_SECTION = "settings_section";

	function applies_to(types) {
		return `eval:${JSON.stringify(types)}.includes(doc.question_type)`;
	}

	function set_settings_visibility(frm) {
		const grid = frm.fields_dict[QUESTIONS]?.grid;
		if (!grid) return;

		const all_types = new Set();
		for (const [fieldname, types] of Object.entries(SETTINGS)) {
			types.forEach((type) => all_types.add(type));
			grid.update_docfield_property(fieldname, "depends_on", applies_to(types));
		}
		grid.update_docfield_property(SETTINGS_SECTION, "depends_on", applies_to([...all_types]));
	}

	["Job Opening", "Job Opening Template"].forEach((doctype) => {
		frappe.ui.form.on(doctype, {
			refresh: set_settings_visibility,
		});
	});

	frappe.ui.form.on(QUESTION_DOCTYPE, {
		question_type(frm, cdt, cdn) {
			// clear settings the new type doesn't use, so hidden values can't fail validation
			const row = locals[cdt][cdn];
			for (const [fieldname, types] of Object.entries(SETTINGS)) {
				if (!types.includes(row.question_type) && row[fieldname]) {
					frappe.model.set_value(cdt, cdn, fieldname, fieldname === "currency" ? "" : 0);
				}
			}
			if (row.question_type === "Currency" && !row.currency && frm.doc.currency) {
				frappe.model.set_value(cdt, cdn, "currency", frm.doc.currency);
			}
		},
	});

	frappe.ui.form.on("Job Opening", {
		job_opening_template(frm) {
			const template = frm.doc.job_opening_template;
			if (!template || !frm.fields_dict[QUESTIONS]) return;

			if ((frm.doc[QUESTIONS] || []).length) {
				frappe.show_alert({
					message: __(
						"Kept this opening's screening questions. Clear them first to use the template's.",
					),
					indicator: "blue",
				});
				return;
			}

			frappe.db.get_doc("Job Opening Template", template).then((doc) => {
				// the template may have changed, or questions been added, while this loaded
				if (
					frm.doc.job_opening_template !== template ||
					(frm.doc[QUESTIONS] || []).length
				) {
					return;
				}

				const rows = doc[QUESTIONS] || [];
				if (!rows.length) return;

				const fieldnames = frappe.meta
					.get_docfields(QUESTION_DOCTYPE)
					.filter((df) => !frappe.model.no_value_type.includes(df.fieldtype))
					.map((df) => df.fieldname);

				rows.forEach((row) => {
					const copy = {};
					fieldnames.forEach((fieldname) => (copy[fieldname] = row[fieldname]));
					frm.add_child(QUESTIONS, copy);
				});
				frm.refresh_field(QUESTIONS);
				frappe.show_alert({
					message: __("Copied {0} screening questions from {1}", [
						rows.length,
						frappe.utils.escape_html(template),
					]),
					indicator: "green",
				});
			});
		},
	});
})();
