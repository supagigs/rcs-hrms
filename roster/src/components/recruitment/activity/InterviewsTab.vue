<template>
	<div class="flex-1 overflow-y-auto px-5 py-4">
		<LoadingIndicator v-if="loading && !summary" class="mx-auto size-5 text-ink-gray-5" />
		<div v-else-if="summary?.interviews.length">
			<a
				v-for="interview in summary.interviews"
				:key="interview.name"
				:target="linkTarget"
				:href="deskUrl('Interview', interview.name)"
				class="mb-2.5 block rounded-[9px] border border-outline-gray-2 p-3.5 hover:bg-surface-gray-1"
			>
				<div class="flex items-center justify-between gap-2">
					<span class="truncate text-sm font-bold text-ink-gray-9">
						{{ interview.interview_type }}
					</span>
					<StatusPill :label="interview.status" size="sm" />
				</div>
				<div class="mt-1 text-xs text-ink-gray-5">{{ formatSchedule(interview) }}</div>
				<div
					v-if="interview.interviewers.length"
					class="mt-2 truncate text-xs text-ink-gray-4"
				>
					with {{ interview.interviewers.map((i) => i.full_name).join(", ") }}
				</div>
			</a>
		</div>
		<EmptyState
			v-else
			icon="calendar"
			title="No interviews yet"
			description="Scheduled interview rounds for this applicant show up here."
		/>
	</div>
</template>

<script setup lang="ts">
import { LoadingIndicator } from "frappe-ui";

import { CandidateSummary, Interview, deskUrl } from "../../../data/jobApplicant";
import { dayjs } from "../../../utils";
import { linkTarget } from "../../../utils/embed";
import EmptyState from "../EmptyState.vue";
import StatusPill from "../StatusPill.vue";

defineProps<{ summary?: CandidateSummary | null; loading?: boolean }>();

const formatTime = (time?: string) => (time ? dayjs(time, "HH:mm:ss").format("h:mm A") : "");

function formatSchedule(interview: Interview) {
	const times = [formatTime(interview.from_time), formatTime(interview.to_time)]
		.filter(Boolean)
		.join(" – ");
	return [dayjs(interview.scheduled_on).format("D MMM YYYY"), times].filter(Boolean).join(", ");
}
</script>
