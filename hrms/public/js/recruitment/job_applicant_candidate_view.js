// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// Loaded via `doctype_js` in addition to the doctype's own job_applicant.js. Shows the Job Applicant page from
// roster (/hr/recruitment/job-applicant/<name>) inside the Desk form, in a same-origin iframe,
// in place of the standard layout. ?classic=1 and new documents show the standard form.
(() => {
	const APP_PATH = "/hr/recruitment/job-applicant/";
	const MSG_UPDATED = "hrms:job-applicant:updated"; // iframe -> Desk: the applicant changed
	const MSG_RELOAD = "hrms:job-applicant:reload"; // Desk -> iframe: reload your data
	const MSG_MAKE_EMPLOYEE = "hrms:job-applicant:make-employee"; // iframe -> Desk: Create Employee

	// Header buttons from job_applicant.js that the embedded page provides itself, so they
	// appear once: Create Employee is in the page header, and rejecting goes through the page's
	// Change Stage, which asks for confirmation first.
	const BUTTONS_PROVIDED_BY_PAGE = ["Create Employee", "Reject"];
	const EMBED_CLASS = "hrms-applicant-embed";
	const HIDDEN_CLASS = "hrms-applicant-embed-hidden";

	const app_url = (name) => `${APP_PATH}${encodeURIComponent(name)}?embed=1`;
	const desk_url = (name, classic) =>
		`/desk/job-applicant/${encodeURIComponent(name)}${classic ? "?classic=1" : ""}`;

	// in-Desk navigation re-encodes query params as JSON, so ?classic=1 may arrive as ?classic="1"
	const flag_requested = (param) =>
		["1", '"1"'].includes(new URLSearchParams(window.location.search).get(param));
	const classic_requested = () => flag_requested("classic");

	// the same action as the Desk "Create Employee" button: map the applicant and open the new
	// Employee form. Only for Accepted applicants without an Employee, as that button.
	function make_employee(frm) {
		if (frm.doc.status !== "Accepted" || frm.doc.__onload?.employee) return;
		frm.make_methods?.Employee?.();
	}

	// shared by every evaluation of this script (it runs again when the doctype meta reloads)
	const registry = (window.__hrms_applicant_embed ||= { active: null, listening: false });

	frappe.dom.set_style(
		`
		.${HIDDEN_CLASS} { display: none !important; }
		.${EMBED_CLASS} .layout-main-section-wrapper { flex: 1 1 auto; max-width: 100%; }
		.${EMBED_CLASS} .layout-main-section {
			padding: 0 !important; border: 0 !important; background: none !important; box-shadow: none !important;
		}
		.hrms-applicant-embed-frame {
			border: 1px solid var(--border-color); border-radius: var(--border-radius-md);
			overflow: hidden; background: var(--card-bg);
		}
		.hrms-applicant-embed-frame iframe { display: block; width: 100%; border: 0; }
		`,
		"hrms-applicant-embed-style",
	);

	function fit_height(state) {
		if (!state?.container.isConnected) return;
		// fill the viewport below the page header, so neither Desk nor the iframe page scrolls
		const top = state.container.getBoundingClientRect().top + window.scrollY;
		state.iframe.style.height = `${Math.max(480, window.innerHeight - top - 16)}px`;
	}

	// the standard layout, its right sidebar (assign, attachments, tags, share) and the timeline
	const standard_parts = (frm) =>
		[frm.layout?.wrapper, frm.page.sidebar, frm.footer?.wrapper].filter(Boolean);

	function show_classic(frm) {
		$(frm.page.wrapper).removeClass(EMBED_CLASS);
		standard_parts(frm).forEach(($el) => $($el).removeClass(HIDDEN_CLASS));
		if (frm.__applicant_embed) $(frm.__applicant_embed.container).addClass(HIDDEN_CLASS);
		registry.active = null;
	}

	function show_embedded(frm) {
		$(frm.page.wrapper).addClass(EMBED_CLASS);
		standard_parts(frm).forEach(($el) => $($el).addClass(HIDDEN_CLASS));

		// one Form (and so one iframe) is reused for every Job Applicant: create it once
		let state = frm.__applicant_embed;
		if (!state) {
			const container = document.createElement("div");
			container.className = "hrms-applicant-embed-frame";
			const iframe = document.createElement("iframe");
			iframe.title = __("Job Applicant");
			container.appendChild(iframe);
			$(frm.form_wrapper).after(container);
			state = frm.__applicant_embed = { container, iframe, name: null, modified: null };
			// header buttons can render after the first measurement
			iframe.addEventListener("load", () => fit_height(state));
		}
		$(state.container).removeClass(HIDDEN_CLASS);

		const name = frm.doc.name;
		if (state.name !== name) {
			// another applicant: load it. Refreshes of the same one keep the loaded page.
			// Once the iframe has a page, replace() it: changing src would add a browser history
			// entry, and Back would then step through the iframe instead of Desk.
			const url = app_url(name);
			if (state.name) state.iframe.contentWindow.location.replace(url);
			else state.iframe.src = url;
			state.name = name;
		} else if (state.modified !== frm.doc.modified && !state.reloading_for_iframe) {
			// changed from Desk (header buttons, another tab): let the page refetch
			state.iframe.contentWindow?.postMessage(
				{ type: MSG_RELOAD, name },
				window.location.origin,
			);
		}
		state.modified = frm.doc.modified;
		state.reloading_for_iframe = false;

		registry.active = { frm, state };
		requestAnimationFrame(() => fit_height(state));

		// the standard fields aren't shown, so there is nothing to save from here
		frm.disable_save();
		// Desk header actions (Shortlist, Reject, ...) still save through frm.save()
		frm.$wrapper.off("dirty.hrms_applicant_embed").on("dirty.hrms_applicant_embed", () =>
			setTimeout(() =>
				removeEventListener("beforeunload", frm.beforeUnloadListener, {
					capture: true,
				}),
			),
		);
	}

	if (!registry.listening) {
		registry.listening = true;

		window.addEventListener("message", (event) => {
			const active = registry.active;
			if (
				event.origin !== window.location.origin ||
				!active ||
				event.source !== active.state.iframe.contentWindow ||
				event.data?.type !== MSG_UPDATED ||
				event.data.name !== active.frm.doc.name
			)
				return;

			// keep the Desk title, indicator and header buttons in sync with changes made in the page
			active.state.reloading_for_iframe = true;
			active.frm.reload_doc();
		});

		window.addEventListener("message", (event) => {
			const active = registry.active;
			if (
				event.origin !== window.location.origin ||
				!active ||
				event.source !== active.state.iframe.contentWindow ||
				event.data?.type !== MSG_MAKE_EMPLOYEE ||
				event.data.name !== active.frm.doc.name
			)
				return;
			make_employee(active.frm);
		});

		window.addEventListener("resize", () => fit_height(registry.active?.state));
	}

	frappe.ui.form.on("Job Applicant", {
		refresh(frm) {
			frm.$wrapper.off("dirty.hrms_applicant_embed");
			if (frm.is_new() || frm.doc.__islocal) {
				show_classic(frm);
				return;
			}

			// only the full-page form of this document, never other routes
			const route = frappe.get_route();
			const on_form =
				route[0] === "Form" && route[1] === frm.doctype && route[2] === frm.doc.name;

			if (!on_form || classic_requested()) {
				show_classic(frm);
				frm.page.add_menu_item(__("Back to Applicant View"), () => {
					window.location.href = desk_url(frm.doc.name);
				});
				return;
			}

			show_embedded(frm);
			BUTTONS_PROVIDED_BY_PAGE.forEach((label) => frm.remove_custom_button(__(label)));
			frm.page.add_menu_item(__("Edit in classic form"), () => {
				window.location.href = desk_url(frm.doc.name, true);
			});

			// "Create Employee" from the page opened outside Desk (/hr/...) lands here
			if (flag_requested("make_employee")) {
				const url = new URL(window.location.href);
				url.searchParams.delete("make_employee");
				window.history.replaceState(window.history.state, "", url);
				make_employee(frm);
			}
		},
	});
})();
