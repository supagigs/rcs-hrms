<template>
	<div class="flex min-h-0 flex-1 flex-col">
		<div
			class="flex shrink-0 items-center justify-between border-b border-outline-gray-1 px-6 py-4"
		>
			<h2 class="text-[17px] font-bold text-ink-gray-9">Resume / CV</h2>
			<div class="flex items-center gap-2.5">
				<IconButton
					v-if="resumeUrl"
					icon="download"
					label="Download"
					:href="resumeUrl"
					new-tab
				/>
				<FileUploader
					:upload-args="{ doctype: 'Job Applicant', docname: doc.name, private: true }"
					@success="setResume"
				>
					<template #default="{ openFileSelector, uploading, progress }">
						<button
							class="flex h-[34px] items-center gap-1.5 rounded-[7px] bg-blue-500 px-3.5 text-sm font-bold text-white hover:bg-surface-blue-3 disabled:opacity-60"
							:disabled="uploading || setValue.loading"
							@click="requestUpload(openFileSelector)"
						>
							<FeatherIcon name="upload" class="size-3.5" />
							{{ uploading ? `Uploading ${progress}%` : "Update Resume" }}
						</button>
					</template>
				</FileUploader>
			</div>
		</div>

		<ConfirmDialog
			v-model="confirmOpen"
			title="Replace the resume?"
			:message="replaceMessage"
			note="You'll pick the new file next. Nothing changes if you cancel the file picker."
			confirm-label="Choose New Resume"
			theme="blue"
			@confirm="confirmUpload"
		/>

		<div class="flex min-h-0 flex-1 bg-surface-gray-2 p-[26px]">
			<div
				v-if="previewType === 'pdf'"
				class="flex-1 overflow-hidden border border-outline-gray-1 bg-surface-cards shadow-md"
			>
				<iframe :src="resumeUrl" class="size-full border-0" title="Resume" />
			</div>
			<div v-else-if="previewType === 'image'" class="flex-1 overflow-auto">
				<!-- block + mx-auto (not flex centering) so a wide image scrolls instead of clipping its left edge -->
				<img
					:src="resumeUrl"
					alt="Resume"
					class="mx-auto block w-full max-w-[620px] border border-outline-gray-1 bg-surface-cards shadow-md"
				/>
			</div>
			<div
				v-else
				class="mx-auto flex w-full max-w-[620px] flex-col items-center justify-center gap-3 self-start border border-outline-gray-1 bg-surface-cards px-8 py-16 text-center shadow-md"
			>
				<FeatherIcon name="file-text" class="size-8 text-ink-gray-4" />
				<template v-if="resumeUrl">
					<p class="text-sm text-ink-gray-6">This resume can't be previewed here.</p>
					<a
						:href="resumeUrl"
						target="_blank"
						rel="noopener noreferrer"
						class="text-sm font-semibold text-ink-blue-3 hover:underline"
					>
						Open resume ↗
					</a>
				</template>
				<template v-else>
					<p class="text-sm font-semibold text-ink-gray-8">No resume yet</p>
					<p class="text-sm text-ink-gray-5">Upload one with Update Resume.</p>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { FeatherIcon, FileUploader } from "frappe-ui";

import { JobApplicant, useMethod } from "../../../data/jobApplicant";
import ConfirmDialog from "../ConfirmDialog.vue";
import IconButton from "../IconButton.vue";

const props = defineProps<{ doc: JobApplicant }>();
const emit = defineEmits<{ updated: [] }>();

// the attachment wins over the link, the Desk form only previews resume_link
const resumeUrl = computed(() => props.doc.resume_attachment || props.doc.resume_link || "");

const previewType = computed(() => {
	const path = resumeUrl.value.split("?")[0].toLowerCase();
	if (path.endsWith(".pdf")) return "pdf";
	if (/\.(png|jpe?g|gif|webp)$/.test(path)) return "image";
	return null;
});

const setValue = useMethod("frappe.client.set_value", () => emit("updated"));

// replacing an existing resume asks first; the first upload doesn't
const confirmOpen = ref(false);
let openSelector: (() => void) | null = null;

const fileName = (url: string) => {
	const last = url.split("?")[0].split("/").filter(Boolean).pop() || url;
	try {
		return decodeURIComponent(last);
	} catch {
		return last;
	}
};

const replaceMessage = computed(() => {
	if (props.doc.resume_attachment)
		return `The current resume, ${fileName(
			props.doc.resume_attachment,
		)}, will be replaced by the file you upload. The old file stays attached and is listed under Documents.`;
	return "The file you upload will be shown as the resume instead of the current resume link. The link itself is kept.";
});

function requestUpload(open: () => void) {
	if (!resumeUrl.value) {
		open();
		return;
	}
	openSelector = open;
	confirmOpen.value = true;
}

function confirmUpload() {
	confirmOpen.value = false;
	openSelector?.();
	openSelector = null;
}

// the uploaded File is attached to the applicant; also point the resume field at it
function setResume(file: { file_url: string }) {
	setValue.submit({
		doctype: "Job Applicant",
		name: props.doc.name,
		fieldname: "resume_attachment",
		value: file.file_url,
	});
}
</script>
