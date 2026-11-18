import { MaybeRefOrGetter, computed, toValue } from "vue";
import { createResource, useCall } from "frappe-ui";

import { dayjs, raiseToast } from "../utils";

export const APPLICANT_STATUSES = [
	"Open",
	"Replied",
	"Shortlisted",
	"Rejected",
	"Hold",
	"Accepted",
] as const;
export type ApplicantStatus = (typeof APPLICANT_STATUSES)[number];

// question and question_type are copies taken when the applicant answered (hrms/hr/screening.py)
export type ScreeningResponse = {
	name: string;
	question: string;
	question_type?: string;
	question_row?: string;
	answer?: string;
	answer_number?: number | null;
	answer_date?: string | null;
	currency?: string | null;
};

export type WorkExperience = {
	name: string;
	company_name: string;
	designation?: string;
	location?: string;
	from_date: string;
	to_date?: string | null;
	currently_working?: 0 | 1;
	description?: string;
};

// ERPNext Employee Education, reused on the applicant
export type Education = {
	name: string;
	school_univ?: string;
	qualification?: string;
	level?: string;
	year_of_passing?: number;
	class_per?: string;
	maj_opt_subj?: string;
};

export type JobApplicant = {
	name: string;
	owner: string;
	creation: string;
	applicant_name: string;
	email_id: string;
	phone_number?: string;
	country?: string;
	job_title?: string;
	designation?: string;
	status: ApplicantStatus;
	applicant_rating?: number;
	source?: string;
	source_name?: string;
	employee_referral?: string;
	cover_letter?: string;
	resume_attachment?: string;
	resume_link?: string;
	currency?: string;
	lower_range?: number;
	upper_range?: number;
	_user_tags?: string;
	__onload?: { job_offer?: string; employee?: string };
	// custom fields (hrms.patches.v16_0.add_job_applicant_candidate_fields)
	custom_linkedin_profile?: string;
	custom_github_profile?: string;
	custom_portfolio_url?: string;
	custom_other_profile_url?: string;
	custom_referrer_name?: string;
	custom_referrer_email?: string;
	custom_supporting_document_1?: string;
	custom_supporting_document_2?: string;
	custom_screening_responses?: ScreeningResponse[];
	custom_work_experience?: WorkExperience[];
	custom_education?: Education[];
	custom_total_experience_years?: number;
	custom_internal_notes?: string;
	custom_consent_given?: 0 | 1;
	custom_consent_given_on?: string;
};

export type Comment = {
	name: string;
	creation: string;
	owner: string;
	content: string;
	comment_type: string;
};
export type Communication = {
	name: string;
	creation: string;
	communication_date?: string;
	subject?: string;
	content?: string;
	sender?: string;
	sender_full_name?: string;
	recipients?: string;
	sent_or_received?: "Sent" | "Received";
	communication_medium?: string;
};
export type Version = { name: string; owner: string; creation: string; data: string };
export type Attachment = { name: string; file_name: string; file_url: string; is_private: 0 | 1 };

export type DocInfo = {
	comments: Comment[];
	communications: Communication[];
	versions: Version[];
	attachments: Attachment[];
};

export type Interviewer = { user: string; full_name: string };
export type Interview = {
	name: string;
	interview_type: string;
	scheduled_on: string;
	from_time?: string;
	to_time?: string;
	status: string;
	average_rating?: number;
	interviewers: Interviewer[];
};
export type Feedback = {
	name: string;
	interview: string;
	interview_type: string;
	interviewer: string;
	interviewer_name: string;
	average_rating?: number;
	result?: string;
	feedback?: string;
	modified: string;
};
export type CandidateSummary = {
	interviews: Interview[];
	feedback: Feedback[];
	skill_ratings: { skill: string; rating: number }[];
	pending_feedback: (Interviewer & { interview: string; interview_type: string })[];
	rating_scale: number;
	job_opening_title?: string | null;
};

export function useJobApplicant(name: MaybeRefOrGetter<string>) {
	const applicant = createResource({
		url: "frappe.desk.form.load.getdoc",
		makeParams: () => ({ doctype: "Job Applicant", name: toValue(name) }),
		auto: true,
		transform: (data: { docs: JobApplicant[]; docinfo: DocInfo }) => ({
			doc: data.docs[0],
			docinfo: data.docinfo,
		}),
	});

	// frappe-ui 0.1.105 ships untyped JS, so results are typed where they're consumed
	const summary = useCall({
		url: "/api/v2/method/hrms.api.recruitment.get_candidate_summary",
		params: () => ({ job_applicant: toValue(name) }),
	});

	const doc = computed<JobApplicant | undefined>(() => applicant.data?.doc);
	const docinfo = computed<DocInfo | undefined>(() => applicant.data?.docinfo);

	function reload() {
		applicant.reload();
		summary.reload();
	}

	return { applicant, summary, doc, docinfo, reload };
}

// POST wrapper for whitelisted methods that change data; create it in setup, call .submit(params) later
export function useMethod(method: string, onSuccess?: (data: any) => void) {
	return useCall({
		url: `/api/v2/method/${method}`,
		method: "POST",
		immediate: false,
		onSuccess,
		onError: (error: Error) => raiseToast("error", error.message),
	});
}

export type UserOption = { label: string; value: string };

// users Desk offers for @mentions; shared by the comment box, task and interview pickers
let users: { data: UserOption[] | null; loading: boolean } | null = null;
export function useUsers() {
	users ||= createResource({ url: "hrms.api.recruitment.get_mentionable_users", auto: true });
	return users!;
}

export const userLabel = (email: string | undefined, options?: UserOption[] | null) =>
	options?.find((user) => user.value === email)?.label || email || "";

export const stripHtml = (html?: string) =>
	new DOMParser().parseFromString(html || "", "text/html").body.textContent?.trim() || "";

export const deskUrl = (doctype: string, name?: string) =>
	`/desk/${doctype.toLowerCase().replace(/ /g, "-")}${
		name ? `/${encodeURIComponent(name)}` : ""
	}`;

// the classic Desk form; ?classic=1 stops its redirect to the workspace
export const classicDeskUrl = (name: string) => `${deskUrl("Job Applicant", name)}?classic=1`;

// status pill colours from the mockup, as semantic tokens so they also work in dark mode
const TONES = {
	amber: { pill: "bg-surface-orange-1 text-ink-amber-3", dot: "bg-[--ink-amber-3]" },
	blue: { pill: "bg-surface-blue-2 text-ink-blue-3", dot: "bg-[--ink-blue-3]" },
	red: { pill: "bg-surface-red-2 text-ink-red-4", dot: "bg-[--ink-red-4]" },
	green: { pill: "bg-surface-green-2 text-ink-green-3", dot: "bg-[--ink-green-3]" },
	gray: { pill: "bg-surface-gray-2 text-ink-gray-6", dot: "bg-[--ink-gray-4]" },
};
const STATUS_TONES: Record<string, keyof typeof TONES> = {
	// Job Applicant
	Open: "amber",
	Replied: "amber",
	Shortlisted: "blue",
	Hold: "red",
	Rejected: "red",
	Accepted: "green",
	// Interview / Interview Feedback
	Pending: "blue",
	"Under Review": "blue",
	Cleared: "green",
	Cancelled: "gray",
	// consent and other yes/no pills
	Given: "green",
	Current: "green",
	Yes: "green",
	No: "gray",
};
export const pillClasses = (status?: string) => TONES[STATUS_TONES[status || ""] || "gray"].pill;
export const dotClasses = (status?: string) => TONES[STATUS_TONES[status || ""] || "gray"].dot;

// ratings are stored as a fraction (0-1) of the rating scale
export const toStars = (fraction?: number, scale = 5) =>
	Math.round((fraction || 0) * scale * 10) / 10;

// links entered by applicants are only followed when they are plain web links
export const webUrl = (url?: string | null) => {
	const value = (url || "").trim();
	return /^https?:\/\/[^\s]+$/i.test(value) ? value : undefined;
};

// "github.com/someone" for a link's label
export const displayUrl = (url: string) =>
	url.replace(/^https?:\/\/(www\.)?/i, "").replace(/\/$/, "");

export const formatAmount = (value?: number | null, currency?: string | null) => {
	if (value === null || value === undefined) return "";
	try {
		return new Intl.NumberFormat(undefined, {
			...(currency ? { style: "currency", currency } : {}),
			minimumFractionDigits: 0,
			maximumFractionDigits: 2,
		}).format(value);
	} catch {
		return `${currency || ""} ${value}`.trim();
	}
};

export const formatDate = (value?: string | null, format = "D MMM YYYY") =>
	value ? dayjs(value).format(format) : "";

// "2 yrs 3 mos" between two dates; to = null means still going
export function formatDuration(from: string, to?: string | null) {
	const months = dayjs(to || undefined).diff(dayjs(from), "month");
	if (months < 1) return "less than a month";
	const years = Math.floor(months / 12);
	const rest = months % 12;
	return [
		years && `${years} ${years === 1 ? "yr" : "yrs"}`,
		rest && `${rest} ${rest === 1 ? "mo" : "mos"}`,
	]
		.filter(Boolean)
		.join(" ");
}
