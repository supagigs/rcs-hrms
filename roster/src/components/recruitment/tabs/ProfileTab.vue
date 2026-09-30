<template>
	<div class="flex-1 overflow-y-auto px-8 py-7">
		<div class="flex max-w-[640px] flex-col gap-5">
			<ProfileLinksForm :doc="doc" @updated="emit('updated')" />

			<div
				class="flex items-center justify-between gap-3 rounded-[9px] border border-outline-gray-2 px-4 py-3.5"
			>
				<span class="text-sm text-ink-gray-7">Data processing consent</span>
				<span class="flex items-center gap-2">
					<span v-if="doc.custom_consent_given_on" class="text-xs text-ink-gray-4">
						{{ formatDateTime(doc.custom_consent_given_on) }}
					</span>
					<StatusPill
						:label="doc.custom_consent_given ? 'Given' : 'Not recorded'"
						size="sm"
					/>
				</span>
			</div>

			<div class="rounded-[9px] border border-outline-gray-2">
				<div class="flex items-center justify-between gap-3 px-4 py-3.5">
					<span class="text-sm text-ink-gray-7">Duplicate applicant check</span>
					<StatusPill :label="duplicateLabel" size="sm" />
				</div>
				<div
					v-if="otherApplications.data?.length"
					class="border-t border-outline-gray-1 px-2 py-1.5"
				>
					<a
						v-for="application in otherApplications.data"
						:key="application.name"
						:href="applicationUrl(application.name)"
						:target="linkTarget"
						class="flex items-center justify-between rounded-md px-2 py-2 hover:bg-surface-gray-2"
					>
						<span class="truncate text-sm text-ink-gray-8">
							{{ application.job_title || "No Job Opening" }}
						</span>
						<StatusPill :label="application.status" size="sm" />
					</a>
				</div>
			</div>

			<div>
				<div class="mb-1.5 flex items-center justify-between">
					<span class="text-sm text-ink-gray-5"
						>Internal notes (not visible to applicant)</span
					>
					<button
						v-if="notesChanged"
						class="h-7 rounded-[7px] bg-blue-500 px-3 text-xs font-bold text-white hover:bg-surface-blue-3 disabled:opacity-60"
						:disabled="setValue.loading"
						@click="saveNotes"
					>
						Save
					</button>
				</div>
				<TextEditor
					:content="notes"
					editor-class="prose-sm max-w-none min-h-[7rem] rounded-lg border border-outline-gray-2 bg-surface-white px-2.5 py-2 text-sm text-ink-gray-7 focus-within:border-outline-gray-4"
					placeholder="Add a hiring summary for the team…"
					@change="(value: string) => (notes = value)"
				/>
			</div>

			<div>
				<div class="mb-1.5 text-sm text-ink-gray-5">Cover letter</div>
				<p
					v-if="doc.cover_letter"
					class="whitespace-pre-wrap text-sm leading-relaxed text-ink-gray-7"
					v-text="doc.cover_letter"
				/>
				<p v-else class="text-sm text-ink-gray-4">No cover letter.</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { TextEditor, useList } from "frappe-ui";

import { JobApplicant, deskUrl, useMethod } from "../../../data/jobApplicant";
import { isEmbedded, linkTarget } from "../../../utils/embed";
import { dayjs } from "../../../utils";
import ProfileLinksForm from "../ProfileLinksForm.vue";
import StatusPill from "../StatusPill.vue";

const props = defineProps<{ doc: JobApplicant }>();
const emit = defineEmits<{ updated: [] }>();

const notes = ref(props.doc.custom_internal_notes || "");
watch(
	() => props.doc.custom_internal_notes,
	(value) => (notes.value = value || ""),
);
const notesChanged = computed(() => notes.value !== (props.doc.custom_internal_notes || ""));

const setValue = useMethod("frappe.client.set_value", () => emit("updated"));

function saveNotes() {
	setValue.submit({
		doctype: "Job Applicant",
		name: props.doc.name,
		fieldname: "custom_internal_notes",
		value: notes.value,
	});
}

// names are email based, so re-applications share the email_id
const otherApplications = useList({
	doctype: "Job Applicant",
	fields: ["name", "job_title", "status"],
	filters: () => ({ email_id: props.doc.email_id, name: ["!=", props.doc.name] }),
	orderBy: "creation desc",
	limit: 20,
	refetch: true,
});

const duplicateLabel = computed(() => {
	const count = otherApplications.data?.length || 0;
	if (!count) return "No duplicates found";
	return count === 1 ? "1 other application" : `${count} other applications`;
});

// embedded, open them as Desk forms (which show this page) in the whole window
const applicationUrl = (name: string) =>
	isEmbedded
		? deskUrl("Job Applicant", name)
		: `/hr/recruitment/job-applicant/${encodeURIComponent(name)}`;

const formatDateTime = (value: string) => dayjs(value).format("D MMM YYYY, h:mm A");
</script>
