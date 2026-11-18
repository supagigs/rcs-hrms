<template>
	<div class="flex h-full flex-col bg-surface-white">
		<div v-if="!doc && applicant.loading" class="flex flex-1 items-center justify-center">
			<LoadingIndicator class="size-6 text-ink-gray-5" />
		</div>

		<div
			v-else-if="!doc"
			class="flex flex-1 flex-col items-center justify-center gap-3 text-ink-gray-6"
		>
			<FeatherIcon name="alert-circle" class="size-6" />
			<p class="text-base">{{ errorMessage }}</p>
			<div class="flex gap-2">
				<Button label="Back to list" @click="navigate(deskUrl('Job Applicant'))" />
				<Button
					v-if="applicant.error?.exc_type !== 'DoesNotExistError'"
					label="Open in Desk"
					@click="navigate(classicDeskUrl(props.name))"
				/>
			</div>
		</div>

		<template v-else>
			<header class="shrink-0 border-b border-outline-gray-1 px-6 pt-4">
				<ApplicantHeader
					:doc="doc"
					:summary="summary.data"
					@updated="onChanged"
					@schedule-interview="showScheduleDialog = true"
				/>
				<UnderlineTabs v-model="leftTab" :tabs="leftTabs" class="mt-[18px]" />
			</header>

			<div class="flex min-h-0 flex-1 overflow-hidden">
				<section class="flex min-w-0 flex-1 flex-col overflow-hidden">
					<ResumeTab v-if="leftTab === 'resume'" :doc="doc" @updated="onChanged" />
					<ExperienceTab v-else-if="leftTab === 'experience'" :doc="doc" />
					<DocumentsTab
						v-else-if="leftTab === 'documents'"
						:doc="doc"
						:attachments="docinfo?.attachments || []"
						@updated="onChanged"
					/>
					<ScreeningTab v-else-if="leftTab === 'screening'" :doc="doc" />
					<ProfileTab v-else :doc="doc" @updated="onChanged" />
				</section>

				<!-- narrower on laptop widths so the content pane keeps ~500px -->
				<ActivityPanel
					class="w-[380px] shrink-0 border-l border-outline-gray-1 min-[1440px]:w-[420px]"
					:doc="doc"
					:docinfo="docinfo"
					:summary="summary.data"
					:summary-loading="summary.loading"
					@updated="onChanged"
					@schedule-interview="showScheduleDialog = true"
				/>

				<DetailsSidebar
					class="w-[256px] shrink-0 border-l border-outline-gray-1 min-[1440px]:w-[300px]"
					:doc="doc"
					:opening-title="summary.data?.job_opening_title"
					@updated="onChanged"
				/>
			</div>

			<ScheduleInterviewDialog
				v-model="showScheduleDialog"
				:doc="doc"
				@scheduled="onChanged"
			/>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { Button, FeatherIcon, LoadingIndicator } from "frappe-ui";

import { classicDeskUrl, deskUrl, useJobApplicant } from "../../data/jobApplicant";
import { navigate, notifyDesk, onDeskReload } from "../../utils/embed";

import ApplicantHeader from "../../components/recruitment/ApplicantHeader.vue";
import DetailsSidebar from "../../components/recruitment/DetailsSidebar.vue";
import ScheduleInterviewDialog from "../../components/recruitment/ScheduleInterviewDialog.vue";
import UnderlineTabs from "../../components/recruitment/UnderlineTabs.vue";
import ActivityPanel from "../../components/recruitment/activity/ActivityPanel.vue";
import DocumentsTab from "../../components/recruitment/tabs/DocumentsTab.vue";
import ExperienceTab from "../../components/recruitment/tabs/ExperienceTab.vue";
import ProfileTab from "../../components/recruitment/tabs/ProfileTab.vue";
import ResumeTab from "../../components/recruitment/tabs/ResumeTab.vue";
import ScreeningTab from "../../components/recruitment/tabs/ScreeningTab.vue";

const props = defineProps<{ name: string }>();

const { applicant, summary, doc, docinfo, reload } = useJobApplicant(() => props.name);

const leftTabs = [
	{ key: "resume", label: "Resume / CV" },
	{ key: "experience", label: "Experience" },
	{ key: "documents", label: "Documents" },
	{ key: "screening", label: "Questionnaires" },
	{ key: "profile", label: "More" },
];
const leftTab = ref("resume");
const showScheduleDialog = ref(false);

const errorMessage = computed(() => {
	if (applicant.error?.exc_type === "PermissionError")
		return "You don't have permission to view this job applicant.";
	if (applicant.error?.exc_type === "DoesNotExistError")
		return `Job Applicant ${props.name} does not exist.`;
	return `Job Applicant ${props.name} could not be loaded.`;
});

function onChanged() {
	reload();
	notifyDesk(props.name);
}

// embedded in the Desk form: Desk asks for a refetch after changes made from its own header buttons
const stopListening = onDeskReload((name) => {
	if (name === props.name) reload();
});
onBeforeUnmount(stopListening);

watch(
	() => props.name,
	() => reload(),
);

watch(doc, (value) => {
	if (value) document.title = `${value.applicant_name} · Job Applicant`;
});
</script>
