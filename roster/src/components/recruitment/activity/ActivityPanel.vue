<template>
	<div class="flex flex-col overflow-hidden">
		<UnderlineTabs
			v-model="tab"
			:tabs="tabs"
			size="md"
			class="shrink-0 border-b border-outline-gray-1 px-5 pt-4"
		/>

		<div class="flex shrink-0 items-center justify-between gap-2 px-5 pt-4">
			<h3 class="text-[15px] font-bold text-ink-gray-9">{{ title }}</h3>
			<button
				v-if="tab === 'email'"
				class="h-[30px] rounded-[7px] bg-blue-500 px-3 text-xs font-bold text-white hover:bg-surface-blue-3"
				@click="showCompose = true"
			>
				Compose Email
			</button>
			<button
				v-else-if="tab === 'interviews' && canScheduleInterview"
				class="h-[30px] rounded-[7px] border border-outline-gray-2 px-3 text-xs font-bold text-ink-gray-7 hover:bg-surface-gray-2"
				@click="emit('schedule-interview')"
			>
				+ Schedule
			</button>
		</div>

		<Timeline
			v-if="tab === 'discussion'"
			:doc="doc"
			:docinfo="docinfo"
			:opening-title="summary?.job_opening_title"
			@updated="emit('updated')"
		/>
		<EmailTab
			v-else-if="tab === 'email'"
			v-model:compose="showCompose"
			:doc="doc"
			:communications="docinfo?.communications || []"
			@updated="emit('updated')"
		/>
		<InterviewsTab
			v-else-if="tab === 'interviews'"
			:summary="summary"
			:loading="summaryLoading"
		/>
		<ScorecardsTab
			v-else-if="tab === 'scorecards'"
			:summary="summary"
			:loading="summaryLoading"
		/>
		<TasksTab v-else :doc="doc" @updated="emit('updated')" />
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

import { CandidateSummary, DocInfo, JobApplicant } from "../../../data/jobApplicant";
import UnderlineTabs from "../UnderlineTabs.vue";

import EmailTab from "./EmailTab.vue";
import InterviewsTab from "./InterviewsTab.vue";
import ScorecardsTab from "./ScorecardsTab.vue";
import TasksTab from "./TasksTab.vue";
import Timeline from "./Timeline.vue";

const props = defineProps<{
	doc: JobApplicant;
	docinfo?: DocInfo;
	summary?: CandidateSummary | null;
	summaryLoading?: boolean;
}>();
const emit = defineEmits<{ updated: []; "schedule-interview": [] }>();

// the mockup's Notes and SMS tabs are left out: comments are team-visible and SMS isn't linked to documents
const tabs = [
	{ key: "discussion", label: "Discussion", title: "Team Discussion" },
	{ key: "email", label: "Email", title: "Email" },
	{ key: "interviews", label: "Interviews", title: "Interviews" },
	{ key: "scorecards", label: "Scorecards", title: "Interview Scorecards" },
	{ key: "tasks", label: "Tasks", title: "Tasks" },
];
const tab = ref("discussion");
const title = computed(() => tabs.find((t) => t.key === tab.value)?.title);
const showCompose = ref(false);

// same rule as the Desk form's "Schedule Interview" button
const canScheduleInterview = computed(() => !["Rejected", "Accepted"].includes(props.doc.status));
</script>
