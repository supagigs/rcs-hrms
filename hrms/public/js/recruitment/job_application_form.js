// Job Application web form (hrms/hr/web_form/job_application): typed screening questions and the
// checks behind Next and Submit. The server (hrms/hr/screening.py, hrms/overrides/job_applicant.py)
// repeats every check and never trusts what is posted; these only give applicants early feedback.
//
// Included through webform_include_js for every Job Applicant web form, but only acts on forms
// that have the screening container field. Frappe renders this file through Jinja before inlining
// it, so it must not contain two opening curly braces in a row, or a curly brace followed by % or #.

(() => {
	const CONTAINER = "screening_questions_html";
	const RESPONSES = "custom_screening_responses";
	const WORK_EXPERIENCE = "custom_work_experience";
	const EDUCATION = "custom_education";
	const SOCIAL_LINKS = [
		"custom_linkedin_profile",
		"custom_github_profile",
		"custom_portfolio_url",
		"custom_other_profile_url",
	];

	// same limits as hrms/hr/screening.py
	const SHORT_TEXT_MAX_LENGTH = 140;
	const LONG_TEXT_MAX_LENGTH = 2000;
	const URL_MAX_LENGTH = 500;
	const MAX_HISTORY_ROWS = 20;

	class AnswerError extends Error {}

	// local versions: web form pages don't load every Desk utility
	function cstr(value) {
		return value === null || value === undefined ? "" : String(value);
	}

	function cint(value) {
		return parseInt(value, 10) || 0;
	}

	function fail(message) {
		throw new AnswerError(message);
	}

	// CLIENT TYPE REGISTRY
	// One entry per question type, keyed by the exact Select value (and server registry key):
	//   df(question)            -> control definition for the nested FieldGroup
	//   read(field, question)   -> raw answer from the control (defaults to field.get_value())
	//   normalize(raw, question) -> answer text as stored, or fail() with the server's message
	//   hints(question)         -> extra help lines
	//   after_make(field, question) -> optional, for controls that need more than a df
	const QUESTION_TYPES = {
		"Short Text": text_type("Data", SHORT_TEXT_MAX_LENGTH),
		"Long Text": text_type("Small Text", LONG_TEXT_MAX_LENGTH),
		Number: number_type(false),
		Currency: number_type(true),
		"Yes/No": radio_type(
			() => [
				{ label: __("Yes"), value: "Yes" },
				{ label: __("No"), value: "No" },
			],
			() => __("must be Yes or No"),
		),
		"Single Select (Radio)": radio_type(
			(question) => question.options.map((option) => ({ label: option, value: option })),
			() => __("must be one of the listed options"),
		),
		"Multiple Select": {
			df: (question) => ({
				fieldtype: "MultiCheck",
				// values are option positions: MultiCheck puts values into attribute selectors
				options: question.options.map((option, i) => ({
					label: escape(option),
					value: String(i),
				})),
				sort_options: false,
				columns: "15rem",
			}),
			read: (field, question) =>
				(field.get_value() || []).map((i) => question.options[cint(i)]).filter(Boolean),
			normalize(value, question) {
				if (!Array.isArray(value)) fail(__("must be a list of options"));
				const chosen = new Set(value.map((item) => cstr(item).trim()).filter(Boolean));
				if ([...chosen].some((item) => !question.options.includes(item))) {
					fail(__("must only contain the listed options"));
				}
				return question.options.filter((option) => chosen.has(option)).join("\n");
			},
			hints: () => [__("Select all that apply")],
			after_make: (field, question) => {
				// MultiCheck has no required marker or help text of its own
				field.$label?.toggleClass("reqd", Boolean(question.is_mandatory));
				append_help(field.$wrapper, field.df.description);
			},
		},
		Dropdown: {
			df: (question) => ({
				fieldtype: "Select",
				options: [""].concat(
					question.options.map((option) => ({ label: escape(option), value: option })),
				),
			}),
			normalize: one_of(() => __("must be one of the listed options")),
		},
		Date: {
			df: () => ({ fieldtype: "Date" }),
			normalize(value) {
				const text = cstr(value).trim();
				if (!is_valid_date(text)) fail(__("must be a valid date"));
				return text.slice(0, 10);
			},
		},
		URL: {
			// Data inputs default to a 140 character maxlength
			df: () => ({ fieldtype: "Data", options: "URL", length: URL_MAX_LENGTH }),
			normalize(value) {
				const text = cstr(value).trim();
				if (text.length > URL_MAX_LENGTH || !is_web_url(text)) {
					fail(__("must be a valid link starting with http:// or https://"));
				}
				return text;
			},
			hints: () => [__("A link starting with https://")],
		},
		Email: {
			df: () => ({ fieldtype: "Data", options: "Email" }),
			normalize(value) {
				const text = cstr(value).trim();
				if (/[,;]/.test(text) || !frappe.utils.validate_type(text, "email")) {
					fail(__("must be a valid email address"));
				}
				return text;
			},
		},
	};

	function text_type(fieldtype, cap) {
		return {
			df: (question) => ({
				fieldtype,
				...(fieldtype === "Data" ? { length: max_length(question, cap) } : {}),
			}),
			normalize(value, question) {
				if (typeof value !== "string") fail(__("must be text"));
				const text = value.trim();
				const length = [...text].length; // code points, like Python's len()
				if (length > max_length(question, cap)) {
					fail(__("must be at most {0} characters", [max_length(question, cap)]));
				}
				if (question.min_length && length < question.min_length) {
					fail(__("must be at least {0} characters", [question.min_length]));
				}
				return text;
			},
			hints(question) {
				const hints = [];
				if (question.min_length) {
					hints.push(__("At least {0} characters", [question.min_length]));
				}
				if (fieldtype !== "Data" || max_length(question, cap) < cap) {
					hints.push(__("Up to {0} characters", [max_length(question, cap)]));
				}
				return hints;
			},
		};
	}

	function max_length(question, cap) {
		return Math.min(question.max_length || cap, cap);
	}

	function number_type(is_currency) {
		return {
			// Data, not Float: Float shows the system precision ("30.000") and hides what was typed
			df: () => ({ fieldtype: "Data" }),
			after_make: (field) => field.$input?.attr("inputmode", "decimal"),
			normalize(value, question) {
				if (typeof value === "boolean" || typeof value === "object") {
					fail(__("must be a number"));
				}
				const number =
					typeof value === "number"
						? value
						: Number(cstr(value).trim().replace(/,/g, ""));
				if (!Number.isFinite(number)) fail(__("must be a number"));
				if (is_currency && number < 0) fail(__("can't be negative"));
				// 0 means "no limit", as on the server
				if (question.min_value && number < question.min_value) {
					fail(__("must be at least {0}", [format_number(question.min_value)]));
				}
				if (question.max_value && number > question.max_value) {
					fail(__("must be at most {0}", [format_number(question.max_value)]));
				}
				return format_number(number);
			},
			hints(question) {
				const hints = [];
				if (is_currency && question.currency) {
					hints.push(__("Amount in {0}", [escape(question.currency)]));
				}
				const min = question.min_value && format_number(question.min_value);
				const max = question.max_value && format_number(question.max_value);
				if (min && max) hints.push(__("Between {0} and {1}", [min, max]));
				else if (min) hints.push(__("At least {0}", [min]));
				else if (max) hints.push(__("At most {0}", [max]));
				return hints;
			},
		};
	}

	function format_number(number) {
		return Number.isInteger(number)
			? String(number)
			: number.toFixed(6).replace(/0+$/, "").replace(/\.$/, "");
	}

	function one_of(message) {
		return (value, question) => {
			const text = cstr(value).trim();
			if (!question.options.includes(text)) fail(message());
			return text;
		};
	}

	// radio buttons: the only control Frappe doesn't provide. Rendered into an HTML field.
	function radio_type(get_choices, message) {
		return {
			df: () => ({ fieldtype: "HTML", options: "" }),
			read: (field) => field.$wrapper.find("input[type=radio]:checked").val() || null,
			normalize(value, question) {
				const text = cstr(value).trim();
				if (!get_choices(question).some((choice) => choice.value === text)) {
					fail(message());
				}
				return text;
			},
			after_make(field, question) {
				const name = `${field.df.fieldname}-choice`;
				const $group = $('<div class="form-group screening-radio"></div>');
				const $label = $('<label class="control-label"></label>')
					.attr("id", `${name}-label`)
					.toggleClass("reqd", Boolean(question.is_mandatory))
					.html(field.df.label);
				const $choices = $('<div class="screening-radio-choices" role="radiogroup"></div>')
					.attr("aria-labelledby", `${name}-label`)
					.attr("aria-required", question.is_mandatory ? "true" : "false");

				get_choices(question).forEach((choice) => {
					$('<label class="screening-radio-choice"></label>')
						.append($('<input type="radio">').attr({ name, value: choice.value }))
						.append($("<span></span>").text(choice.label))
						.appendTo($choices);
				});

				$group.append($label, $choices).appendTo(field.$wrapper.empty());
				append_help($group, field.df.description);
				$choices.on("change", () => field.$wrapper.removeClass("has-error"));
			},
		};
	}

	// SHARED CHECKS (as in hrms/hr/screening.py)

	function is_empty(value) {
		return (
			value === null ||
			value === undefined ||
			(Array.isArray(value) && !value.length) ||
			(typeof value === "string" && !value.trim())
		);
	}

	function is_web_url(text) {
		if (!text || /\s/.test(text)) return false;
		try {
			const url = new URL(text);
			return ["http:", "https:"].includes(url.protocol) && url.hostname.includes(".");
		} catch (e) {
			return false;
		}
	}

	function is_valid_date(text) {
		const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(text);
		if (!match) return false;
		const [year, month, day] = match.slice(1).map(Number);
		const date = new Date(Date.UTC(year, month - 1, day));
		return (
			year >= 1900 &&
			year <= 2200 &&
			date.getUTCFullYear() === year &&
			date.getUTCMonth() === month - 1 &&
			date.getUTCDate() === day
		);
	}

	function escape(text) {
		return frappe.utils.escape_html(cstr(text));
	}

	function append_help($parent, html) {
		if (html)
			$('<div class="help-box small text-extra-muted"></div>').html(html).appendTo($parent);
	}

	// RESUME: PDF only on this form (the server checks too, see hrms/overrides/job_applicant.py)

	const RESUME_NOT_PDF = () => __("Your resume must be a PDF file (.pdf)");

	// an uploaded file's URL, or "<file name>,<data URL>" before upload
	function is_pdf_name(value) {
		const name = value.startsWith("/") ? value.split("?")[0] : value.split(",")[0];
		return name.toLowerCase().endsWith(".pdf");
	}

	function is_pdf_file(file) {
		return is_pdf_name(file.name) && ["", "application/pdf"].includes(file.type);
	}

	function restrict_resume_to_pdf(field) {
		if (!field) return;
		const options = typeof field.df.options === "object" ? field.df.options : {};
		field.df.options = {
			...options,
			// the file picker only offers PDFs; links belong in Resume Link
			restrictions: { ...(options.restrictions || {}), allowed_file_types: [".pdf"] },
			allow_web_link: false,
			allow_take_photo: false,
			allow_google_drive: false,
		};

		// Frappe would skip a non-PDF with a generic "invalid file type" alert; stop it first, in
		// the capture phase, and say what's needed
		const on_attach_click = field.on_attach_click.bind(field);
		field.on_attach_click = () => {
			on_attach_click();
			const wrapper = field.file_uploader?.dialog?.$wrapper?.get(0);
			if (!wrapper || wrapper.dataset.pdfOnly) return;
			wrapper.dataset.pdfOnly = "1";
			const reject_non_pdf = (event) => {
				const files = event.dataTransfer?.files || event.target?.files;
				if (!files?.length || [...files].every(is_pdf_file)) return;
				// read the names first: clearing the input empties its file list
				const names = [...files]
					.filter((file) => !is_pdf_file(file))
					.map((file) => file.name);
				event.preventDefault();
				event.stopImmediatePropagation();
				if (event.target?.type === "file") event.target.value = "";
				frappe.msgprint({
					title: __("PDF files only"),
					indicator: "orange",
					message: `${RESUME_NOT_PDF()}. ${__("{0} can't be used as your resume.", [
						names.map((name) => `<b>${escape(name)}</b>`).join(", "),
					])}`,
				});
			};
			wrapper.addEventListener("change", reject_non_pdf, true);
			wrapper.addEventListener("drop", reject_non_pdf, true);
		};
	}

	// FORM

	const init_client_script = frappe.init_client_script;
	frappe.init_client_script = () => {
		init_client_script && init_client_script();
		const web_form = frappe.web_form;
		if (web_form?.fields_dict?.[CONTAINER] && web_form.is_new) {
			setup(web_form);
		}
	};

	function setup(web_form) {
		const state = {
			job_opening: undefined, // opening the questions were loaded for
			questions: [], // public questions, in the opening's order (idx), active ones only
			status: "idle", // idle | loading | ready | error
			request: 0,
			group: null,
		};

		const container = web_form.fields_dict[CONTAINER];
		// web forms fill fields from the query string; never let a URL write HTML into the page
		container.set_value = () => Promise.resolve();
		container.set_input = () => {};
		const $area = $('<div class="screening-questions"></div>').appendTo(container.$wrapper);

		restrict_resume_to_pdf(web_form.fields_dict.resume_attachment);
		show_opening_title();
		// ?job_title is read once here; the change handler covers the value being set later
		load_questions(frappe.utils.get_query_params().job_title);
		const job_title = web_form.fields_dict.job_title;
		if (job_title) {
			job_title.df.change = () => {
				load_questions(job_title.get_value());
				// after FieldGroup.set_value has re-rendered the field
				setTimeout(show_opening_title);
			};
		}

		const validate_section = web_form.validate_section.bind(web_form);
		web_form.validate_section = () => {
			if (!validate_section()) return false;
			const page = page_selector(web_form.current_section);
			return report(run_checks((fieldname) => field_is_on_page(fieldname, page)));
		};

		const validate = web_form.validate;
		web_form.validate = () => {
			if (validate && validate.call(web_form) === false) return false;
			const errors = run_checks(() => true);
			if (errors.length) go_to_page(errors[0].fieldname);
			return report(errors);
		};

		// CHECKS, keyed by the field that places them on a step

		const CHECKS = [
			[CONTAINER, check_screening],
			[WORK_EXPERIENCE, check_work_experience],
			[EDUCATION, check_education],
			...SOCIAL_LINKS.map((fieldname) => [fieldname, () => check_link(fieldname)]),
			["resume_link", check_resume],
			["custom_consent_given", check_consent],
		];

		function run_checks(include) {
			const errors = [];
			for (const [fieldname, check] of CHECKS) {
				if (!web_form.fields_dict[fieldname] || !include(fieldname)) continue;
				check().forEach((message) => errors.push({ fieldname, message }));
			}
			return errors;
		}

		function report(errors) {
			if (!errors.length) return true;
			frappe.msgprint({
				title: __("Please check your application"),
				indicator: "red",
				message: `<ul><li>${errors.map((error) => error.message).join("</li><li>")}</li></ul>`,
			});
			return false;
		}

		function check_screening() {
			if (state.status === "loading") {
				return [
					__("The screening questions are still loading, please try again in a moment."),
				];
			}
			if (state.status === "error") {
				return [
					__(
						"The screening questions couldn't be loaded. Use Retry, or reload the page.",
					),
				];
			}

			const errors = [];
			state.questions.forEach((question, i) => {
				const field = state.group.fields_dict[question_fieldname(i)];
				let error = null;
				try {
					const answer = read_answer(question, i);
					if (answer === "" && question.is_mandatory)
						error = __("an answer is required");
				} catch (e) {
					if (!(e instanceof AnswerError)) throw e;
					error = e.message;
				}
				field.$wrapper.toggleClass("has-error", Boolean(error));
				if (error) errors.push(`${escape(question.question)}: ${error}`);
			});
			write_answers();
			return errors;
		}

		function check_work_experience() {
			const rows = web_form.get_value(WORK_EXPERIENCE) || [];
			const today = frappe.datetime.get_today();
			const errors = [];
			if (rows.length > MAX_HISTORY_ROWS) {
				errors.push(__("Add at most {0} work experience entries", [MAX_HISTORY_ROWS]));
			}
			rows.forEach((row, i) => {
				const label = __("Work Experience row {0}", [row.idx || i + 1]);
				const to_date = row.currently_working ? null : row.to_date;
				if (row.from_date && to_date && to_date < row.from_date) {
					errors.push(__("{0}: To Date can't be before From Date", [label]));
				}
				if (!cstr(row.company_name).trim()) {
					errors.push(__("{0}: Company is required", [label]));
				}
				if (!row.from_date) {
					errors.push(__("{0}: From Date is required", [label]));
				} else if (row.from_date > today) {
					errors.push(__("{0}: From Date can't be in the future", [label]));
				}
				if (!row.currently_working && !row.to_date) {
					errors.push(__("{0}: add a To Date, or tick Current", [label]));
				} else if (to_date && to_date > today) {
					errors.push(__("{0}: To Date can't be in the future", [label]));
				}
			});
			return errors;
		}

		function check_education() {
			// rows without a school or qualification are dropped on submit, as on the server
			const rows = (web_form.get_value(EDUCATION) || []).filter(
				(row) => cstr(row.school_univ).trim() || cstr(row.qualification).trim(),
			);
			const latest_year = new Date().getFullYear() + 10;
			const errors = [];
			if (rows.length > MAX_HISTORY_ROWS) {
				errors.push(__("Add at most {0} education entries", [MAX_HISTORY_ROWS]));
			}
			rows.forEach((row, i) => {
				const year = cint(row.year_of_passing);
				if (row.year_of_passing && (year < 1900 || year > latest_year)) {
					errors.push(
						__("Education row {0}: Year of Passing looks wrong", [row.idx || i + 1]),
					);
				}
			});
			return errors;
		}

		function check_link(fieldname) {
			const value = cstr(web_form.get_value(fieldname)).trim();
			if (!value || is_web_url(value)) return [];
			const label = escape(__(web_form.fields_dict[fieldname].df.label));
			return [__("{0} must be a valid link starting with http:// or https://", [label])];
		}

		function check_resume() {
			const link = cstr(web_form.get_value("resume_link")).trim();
			if (link && !is_web_url(link)) {
				return [__("Resume Link must be a valid link starting with http:// or https://")];
			}
			const upload = cstr(web_form.get_value("resume_attachment")).trim();
			if (upload && !is_pdf_name(upload)) return [RESUME_NOT_PDF()];
			if (link || upload) return [];
			return [__("Please attach your resume or add a link to it")];
		}

		function check_consent() {
			if (web_form.get_value("custom_consent_given")) return [];
			return [
				__(
					"Please consent to the processing of your personal data to submit the application.",
				),
			];
		}

		// SCREENING QUESTIONS

		function load_questions(job_opening) {
			job_opening = cstr(job_opening).trim();
			if (job_opening === state.job_opening) return;
			state.job_opening = job_opening;
			const request = ++state.request;

			if (!job_opening) {
				set_questions([], "ready");
				return;
			}

			set_questions([], "loading");
			frappe.call({
				method: "hrms.api.recruitment.get_screening_questions",
				args: { job_opening },
				type: "GET",
				callback: (r) => {
					if (request === state.request) set_questions(r?.message || [], "ready");
				},
				error: () => {
					if (request === state.request) set_questions([], "error");
				},
			});
		}

		function set_questions(questions, status) {
			state.questions = questions.filter(
				(question) => QUESTION_TYPES[question.question_type],
			);
			state.status = status;
			render();
			write_answers();
		}

		function render() {
			$area.empty();
			state.group = null;

			if (state.status === "loading") {
				status_message(__("Loading questions…"));
				return;
			}
			if (state.status === "error") {
				status_message(__("The questions for this job opening couldn't be loaded."));
				$('<button type="button" class="btn btn-default btn-sm"></button>')
					.text(__("Retry"))
					.on("click", () => {
						const job_opening = state.job_opening;
						state.job_opening = undefined;
						load_questions(job_opening);
					})
					.appendTo($area);
				return;
			}
			if (!state.questions.length) {
				status_message(
					__("No additional questions for this opening. Continue to the next step."),
				);
				return;
			}

			if (state.questions.some((question) => question.is_mandatory)) {
				status_message(__("Questions marked * need an answer."), "small");
			}

			const $body = $('<div class="screening-questions-body"></div>').appendTo($area);
			state.group = new frappe.ui.FieldGroup({
				fields: state.questions.map((question, i) => {
					const type = QUESTION_TYPES[question.question_type];
					return {
						...type.df(question),
						fieldname: question_fieldname(i),
						label: escape(question.question),
						reqd: question.is_mandatory ? 1 : 0,
						description: help_html(question, type),
					};
				}),
				body: $body.get(0),
				no_submit_on_enter: true,
			});
			state.group.make();

			state.questions.forEach((question, i) => {
				const after_make = QUESTION_TYPES[question.question_type].after_make;
				after_make && after_make(state.group.fields_dict[question_fieldname(i)], question);
			});
		}

		function status_message(text, size = "") {
			$('<p class="screening-status text-muted"></p>')
				.addClass(size)
				.text(text)
				.appendTo($area);
		}

		function help_html(question, type) {
			const lines = [];
			if (question.description)
				lines.push(escape(question.description).replace(/\n/g, "<br>"));
			lines.push(...(type.hints ? type.hints(question) : []));
			return lines.join("<br>");
		}

		function question_fieldname(i) {
			// prefixed so the web form's own step check never mistakes these for its fields
			return `screening_question_${i + 1}`;
		}

		// the stored answer text, "" when unanswered; throws AnswerError when invalid
		function read_answer(question, i) {
			const type = QUESTION_TYPES[question.question_type];
			const field = state.group.fields_dict[question_fieldname(i)];
			const raw = type.read ? type.read(field, question) : field.get_value();
			return is_empty(raw) ? "" : type.normalize(raw, question);
		}

		// the hidden table is what gets posted; the server only takes question_row and answer from it
		function write_answers() {
			const field = web_form.fields_dict[RESPONSES];
			if (!field) return;
			field.df.data = state.questions.map((question, i) => {
				let answer = "";
				try {
					answer = state.group ? read_answer(question, i) : "";
				} catch (e) {
					if (!(e instanceof AnswerError)) throw e;
					answer = raw_text(question, i);
				}
				return {
					idx: i + 1,
					question_row: question.question_row,
					question: question.question,
					answer,
				};
			});
		}

		function raw_text(question, i) {
			const type = QUESTION_TYPES[question.question_type];
			const field = state.group.fields_dict[question_fieldname(i)];
			const raw = type.read ? type.read(field, question) : field.get_value();
			return Array.isArray(raw) ? raw.join("\n") : cstr(raw);
		}

		// OPENING

		function show_opening_title() {
			const field = web_form.fields_dict.job_title;
			const opening = frappe.utils.get_query_params().job_title;
			if (!field || !web_form.job_opening_title || field.get_value() !== opening) return;
			// the ID stays the field's value; only the display changes
			$(field.wrapper).find(".control-value").text(web_form.job_opening_title);
		}

		if (web_form.job_opening_closed) {
			$('<div class="alert alert-warning screening-closed-notice"></div>')
				.text(__("This job opening is no longer accepting applications."))
				.prependTo($(web_form.wrapper || web_form.parent));
		}

		// STEPS

		function page_selector(idx) {
			return web_form.get_page(idx);
		}

		function field_is_on_page(fieldname, selector) {
			const field = web_form.fields_dict[fieldname];
			return Boolean(field && $(selector).has(field.wrapper).length);
		}

		function go_to_page(fieldname) {
			if (!web_form.is_multi_step_form) return;
			for (let idx = 0; idx <= web_form.page_breaks.length; idx++) {
				if (field_is_on_page(fieldname, page_selector(idx))) {
					if (idx !== web_form.current_section) {
						web_form.current_section = idx;
						web_form.toggle_section();
					}
					return;
				}
			}
		}
	}
})();
