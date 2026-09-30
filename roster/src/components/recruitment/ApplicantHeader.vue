<template>
	<div>
		<!-- embedded in the Desk form, Desk's breadcrumbs and menu cover these -->
		<a
			v-if="!isEmbedded"
			:href="deskUrl('Job Applicant')"
			class="mb-2 inline-flex items-center gap-1 text-xs text-ink-gray-5 hover:text-ink-gray-8"
		>
			<FeatherIcon name="chevron-left" class="size-3.5" />
			Back to list
		</a>

		<div class="flex items-center gap-4">
			<span
				class="flex size-[46px] shrink-0 items-center justify-center rounded-full bg-surface-violet-1 text-[17px] font-bold text-ink-violet-1"
				aria-hidden="true"
			>
				{{ initial }}
			</span>

			<div class="min-w-0 flex-1">
				<div class="flex items-center gap-2.5">
					<h1 class="truncate text-[21px] font-bold leading-tight text-ink-gray-9">
						{{ doc.applicant_name }}
					</h1>
					<!-- applicant_rating: set here by hand, saved on click -->
					<Tooltip
						text="Your rating of this applicant. Click a star to change it; it saves automatically."
					>
						<div aria-label="Applicant rating">
							<Rating
								:model-value="applicantStars"
								size="sm"
								:readonly="setValue.loading"
								@update:model-value="setRating"
							/>
						</div>
					</Tooltip>
				</div>
				<div class="mt-[5px] flex items-center gap-2">
					<!-- computed from submitted Interview Feedback, read-only -->
					<Tooltip :text="teamScoreHint">
						<span
							class="inline-flex cursor-default items-center rounded-full px-[9px] py-0.5 text-xs font-bold"
							:class="
								teamScore === null
									? 'bg-surface-gray-2 text-ink-gray-5'
									: 'bg-surface-green-2 text-ink-green-3'
							"
						>
							{{
								teamScore === null
									? "No team score yet"
									: `${teamScore.toFixed(1)} / ${ratingScale} Team Score`
							}}
						</span>
					</Tooltip>
				</div>
			</div>

			<div class="flex shrink-0 items-center gap-2.5">
				<Dropdown :options="moreOptions" placement="right">
					<IconButton icon="more-horizontal" label="More actions" />
				</Dropdown>
				<button
					v-if="canCreateEmployee"
					class="flex h-[34px] items-center gap-1.5 rounded-lg border border-outline-gray-2 px-3 text-sm font-semibold text-ink-gray-7 hover:bg-surface-gray-2"
					@click="makeEmployeeInDesk(doc.name)"
				>
					<FeatherIcon name="user-plus" class="size-3.5" />
					Create Employee
				</button>
				<IconButton
					icon="calendar"
					:label="
						canScheduleInterview
							? 'Schedule Interview'
							: `Interviews can't be scheduled for ${doc.status} applicants`
					"
					:disabled="!canScheduleInterview"
					@click="emit('schedule-interview')"
				/>
				<a
					v-if="!isEmbedded"
					:href="classicDeskUrl(doc.name)"
					class="flex h-[34px] items-center gap-1.5 rounded-lg border border-outline-gray-2 px-3 text-sm font-semibold text-ink-gray-7 hover:bg-surface-gray-2"
					title="Edit fields this page doesn't cover, like Salary Expectation and Additional Details"
				>
					<FeatherIcon name="edit-2" class="size-3.5" />
					Edit in Desk
				</a>

				<Popover placement="bottom-end">
					<template #target="{ togglePopover }">
						<button
							class="flex h-9 items-center gap-2 rounded-[7px] bg-blue-500 px-4 text-sm font-bold text-white hover:bg-surface-blue-3 disabled:opacity-60"
							:disabled="setValue.loading"
							@click="togglePopover()"
						>
							<FeatherIcon name="list" class="size-3.5" />
							Change Stage
						</button>
					</template>
					<template #body="{ close }">
						<div
							class="mt-1.5 w-[200px] rounded-[9px] border border-outline-gray-2 bg-surface-modal p-1.5 shadow-xl"
						>
							<div class="px-2.5 pb-0.5 pt-1.5 text-2xs font-bold text-ink-gray-4">
								JOB APPLICANT STATUS
							</div>
							<button
								v-for="status in APPLICANT_STATUSES"
								:key="status"
								class="flex w-full items-center justify-between rounded-md px-2.5 py-2 text-sm text-ink-gray-7 hover:bg-surface-gray-2"
								@click="
									close();
									requestStatus(status);
								"
							>
								<span class="flex items-center gap-2">
									<span
										class="size-[7px] rounded-full"
										:class="dotClasses(status)"
									/>
									{{ status }}
								</span>
								<FeatherIcon
									v-if="status === doc.status"
									name="check"
									class="size-3.5 text-ink-blue-2"
								/>
							</button>
						</div>
					</template>
				</Popover>
			</div>
		</div>

		<ConfirmDialog
			v-model="confirmOpen"
			:title="confirmation.title"
			:message="confirmation.message"
			:note="confirmation.note"
			:confirm-label="confirmation.confirmLabel"
			:theme="confirmation.theme"
			:loading="setValue.loading"
			@confirm="confirmStatus"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { Dropdown, FeatherIcon, Popover, Rating, Tooltip } from "frappe-ui";

import {
	APPLICANT_STATUSES,
	ApplicantStatus,
	CandidateSummary,
	JobApplicant,
	classicDeskUrl,
	deskUrl,
	dotClasses,
	toStars,
	useMethod,
} from "../../data/jobApplicant";
import { raiseToast } from "../../utils";
import { isEmbedded, makeEmployeeInDesk, navigate } from "../../utils/embed";
import ConfirmDialog from "./ConfirmDialog.vue";
import IconButton from "./IconButton.vue";

const props = defineProps<{ doc: JobApplicant; summary?: CandidateSummary | null }>();
const emit = defineEmits<{ updated: []; "schedule-interview": [] }>();

const setValue = useMethod("frappe.client.set_value", () => emit("updated"));

const initial = computed(() => (props.doc.applicant_name || props.doc.name)[0]?.toUpperCase());
const applicantStars = computed(() => Math.round((props.doc.applicant_rating || 0) * 5));

const ratingScale = computed(() => props.summary?.rating_scale || 5);

// average of submitted Interview Feedback, on the interview rating scale
const teamScore = computed(() => {
	const feedback = props.summary?.feedback || [];
	if (!feedback.length) return null;
	const average =
		feedback.reduce((sum, row) => sum + (row.average_rating || 0), 0) / feedback.length;
	return toStars(average, props.summary?.rating_scale);
});

const teamScoreHint = computed(() => {
	const count = props.summary?.feedback?.length || 0;
	if (!count)
		return "Team Score is the average rating from submitted interview feedback. None yet.";
	return `Average rating from ${count} submitted interview feedback ${
		count === 1 ? "entry" : "entries"
	}. It updates as feedback comes in and can't be edited here.`;
});

// same rule as the Desk form's "Schedule Interview" button
const canScheduleInterview = computed(() => !["Rejected", "Accepted"].includes(props.doc.status));

// moves that stop the pipeline ask first; routine moves between the other stages don't
const CONFIRMATIONS: Partial<
	Record<
		ApplicantStatus,
		(
			name: string,
			from: string,
		) => {
			title: string;
			message: string;
			note: string;
			confirmLabel: string;
			theme: "gray" | "red";
		}
	>
> = {
	Rejected: (name, from) => ({
		title: `Reject ${name}?`,
		message: `${name}'s stage changes from ${from} to Rejected, which ends this application.`,
		note: "Interviews can't be scheduled for rejected applicants. You can move them back to another stage later.",
		confirmLabel: "Reject Candidate",
		theme: "red",
	}),
	Hold: (name, from) => ({
		title: `Put ${name} on hold?`,
		message: `${name}'s stage changes from ${from} to Hold, which pauses this application.`,
		note: "Nothing moves forward until you change the stage again.",
		confirmLabel: "Put on Hold",
		theme: "gray",
	}),
};

const confirmOpen = ref(false);
const pendingStatus = ref<ApplicantStatus | null>(null);
const confirmation = computed(() => {
	const build = pendingStatus.value && CONFIRMATIONS[pendingStatus.value];
	return build
		? build(props.doc.applicant_name, props.doc.status)
		: { title: "", message: "", note: "", confirmLabel: "", theme: "gray" as const };
});

function requestStatus(status: ApplicantStatus) {
	if (status === props.doc.status) return;
	if (CONFIRMATIONS[status]) {
		pendingStatus.value = status;
		confirmOpen.value = true;
		return;
	}
	setStatus(status);
}

function confirmStatus() {
	if (!pendingStatus.value) return;
	setStatus(pendingStatus.value).then(() => {
		if (!setValue.error) confirmOpen.value = false;
	});
}

function setStatus(status: ApplicantStatus) {
	// goes through doc.save(), so validate (and the Employee Referral status sync) runs like it does from Desk
	return setValue
		.submit({
			doctype: "Job Applicant",
			name: props.doc.name,
			fieldname: "status",
			value: status,
		})
		.then(() => {
			if (!setValue.error) raiseToast("success", `Moved to ${status}`);
		});
}

// saved as soon as a star is clicked (full document save, like stage changes)
function setRating(stars: number) {
	if (stars === applicantStars.value) return;
	setValue
		.submit({
			doctype: "Job Applicant",
			name: props.doc.name,
			fieldname: "applicant_rating",
			value: stars / 5,
		})
		.then(() => {
			if (!setValue.error) raiseToast("success", `Rating saved: ${stars} / 5`);
		});
}

// Create Employee runs the Desk form's own mapping; Desk hides its copy of the button
const canCreateEmployee = computed(
	() => props.doc.status === "Accepted" && !props.doc.__onload?.employee,
);

const moreOptions = computed(() => {
	const onload = props.doc.__onload || {};
	const options = [];

	if (onload.employee) {
		options.push({
			label: "View Employee",
			onClick: () => navigate(deskUrl("Employee", onload.employee)),
		});
	}
	if (onload.job_offer) {
		options.push({
			label: "View Job Offer",
			onClick: () => navigate(deskUrl("Job Offer", onload.job_offer)),
		});
	} else if (props.doc.status === "Accepted") {
		options.push({
			label: "Create Job Offer in Desk",
			onClick: () => navigate(classicDeskUrl(props.doc.name)),
		});
	}

	if (props.doc.job_title) {
		options.push({
			label: "View Job Opening",
			onClick: () => navigate(deskUrl("Job Opening", props.doc.job_title)),
		});
	}
	if (!isEmbedded)
		options.push({
			label: "Open in Desk",
			onClick: () => navigate(classicDeskUrl(props.doc.name)),
		});

	return options;
});
</script>
