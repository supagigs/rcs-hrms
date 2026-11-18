<template>
	<div class="flex-1 overflow-y-auto px-8 py-7">
		<div class="max-w-[640px]">
			<div class="mb-4 flex items-center justify-between">
				<h2 class="text-[15px] font-bold text-ink-gray-9">Documents</h2>
				<FileUploader
					:upload-args="{ doctype: 'Job Applicant', docname: doc.name, private: true }"
					@success="emit('updated')"
				>
					<template #default="{ openFileSelector, uploading, progress }">
						<button
							class="h-8 rounded-[7px] border border-outline-gray-2 bg-surface-white px-3 text-sm font-bold text-ink-gray-7 hover:bg-surface-gray-2 disabled:opacity-60"
							:disabled="uploading"
							@click="openFileSelector()"
						>
							{{ uploading ? `Uploading ${progress}%` : "+ Upload Document" }}
						</button>
					</template>
				</FileUploader>
			</div>

			<div v-if="attachments.length" class="flex flex-col gap-2">
				<div
					v-for="file in attachments"
					:key="file.name"
					class="flex items-center gap-3 rounded-[9px] border border-outline-gray-2 px-3.5 py-3 hover:bg-surface-gray-1"
				>
					<FeatherIcon name="file" class="size-[17px] shrink-0 text-ink-gray-5" />
					<div class="min-w-0 flex-1">
						<div class="truncate text-sm font-semibold text-ink-gray-9">
							{{ file.file_name }}
						</div>
						<div class="text-xs text-ink-gray-4">{{ describe(file) }}</div>
					</div>
					<a
						:href="file.file_url"
						target="_blank"
						rel="noopener noreferrer"
						class="text-sm font-semibold text-ink-blue-3 hover:underline"
					>
						View
					</a>
				</div>
			</div>
			<EmptyState
				v-else
				icon="paperclip"
				title="No documents yet"
				description="Resumes and supporting documents from the application form show up here."
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { FeatherIcon, FileUploader } from "frappe-ui";

import { Attachment, JobApplicant } from "../../../data/jobApplicant";
import EmptyState from "../EmptyState.vue";

const props = defineProps<{ doc: JobApplicant; attachments: Attachment[] }>();
const emit = defineEmits<{ updated: [] }>();

// label files that are also referenced by an Attach field
const roles = computed(() => {
	const labels: Record<string, string> = {};
	const fields: [string | undefined, string][] = [
		[props.doc.resume_attachment, "Resume"],
		[props.doc.custom_supporting_document_1, "Supporting Document 1"],
		[props.doc.custom_supporting_document_2, "Supporting Document 2"],
	];
	for (const [url, label] of fields) if (url) labels[url] = label;
	return labels;
});

const describe = (file: Attachment) =>
	[roles.value[file.file_url], file.is_private ? "Private" : "Public"]
		.filter(Boolean)
		.join(" · ");
</script>
