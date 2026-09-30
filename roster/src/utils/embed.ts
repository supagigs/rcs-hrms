// Embed mode: the Job Applicant page shown inside the Desk form (?embed=1, same-origin iframe,
// see hrms/public/js/recruitment/job_applicant_candidate_view.js). Desk provides the navigation around it.

const MSG_UPDATED = "hrms:job-applicant:updated"; // page -> Desk: the applicant changed
const MSG_RELOAD = "hrms:job-applicant:reload"; // Desk -> page: refetch
const MSG_MAKE_EMPLOYEE = "hrms:job-applicant:make-employee"; // page -> Desk: run Create Employee

function detectEmbedded() {
	try {
		return (
			new URLSearchParams(window.location.search).get("embed") === "1" &&
			window.self !== window.top
		);
	} catch {
		// cross-origin parent: never treat as embedded
		return false;
	}
}

export const isEmbedded = detectEmbedded();

// links that leave the page must navigate the whole Desk window, not the iframe
export const linkTarget = isEmbedded ? "_top" : undefined;

export function navigate(url: string) {
	(isEmbedded ? window.top! : window).location.href = url;
}

// after every successful change, so Desk reloads its header, indicator and buttons
export function notifyDesk(name: string) {
	if (!isEmbedded) return;
	window.parent.postMessage({ type: MSG_UPDATED, name }, window.location.origin);
}

// Create Employee runs the Desk form's own mapping (make_employee via open_mapped_doc), which
// opens the new, unsaved Employee in Desk. Outside Desk, open the Desk form and let it run there.
export function makeEmployeeInDesk(name: string) {
	if (isEmbedded) {
		window.parent.postMessage({ type: MSG_MAKE_EMPLOYEE, name }, window.location.origin);
		return;
	}
	navigate(`/desk/job-applicant/${encodeURIComponent(name)}?make_employee=1`);
}

export function onDeskReload(callback: (name: string) => void) {
	if (!isEmbedded) return () => {};
	const listener = (event: MessageEvent) => {
		if (
			event.origin !== window.location.origin ||
			event.source !== window.parent ||
			event.data?.type !== MSG_RELOAD
		)
			return;
		callback(event.data.name);
	};
	window.addEventListener("message", listener);
	return () => window.removeEventListener("message", listener);
}

// the Desk theme lives on the parent's <html data-theme>; follow it, including live switches
export function followDeskTheme(apply: (theme: string) => void) {
	if (!isEmbedded) return () => {};
	const root = window.parent.document.documentElement;
	const sync = () => apply(root.getAttribute("data-theme") === "dark" ? "dark" : "light");
	sync();
	const observer = new MutationObserver(sync);
	observer.observe(root, { attributes: true, attributeFilter: ["data-theme"] });
	return () => observer.disconnect();
}
