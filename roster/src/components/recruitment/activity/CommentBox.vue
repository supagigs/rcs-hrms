<template>
	<div class="shrink-0 px-5 py-3">
		<!-- TextEditor reads `mentions` once when it mounts, so remount it when the user list arrives -->
		<TextEditor
			:key="users.data ? 'mentions-ready' : 'mentions-loading'"
			:content="content"
			:mentions="users.data || []"
			editor-class="prose-sm max-w-none min-h-[4.75rem] max-h-40 overflow-y-auto rounded-lg border border-outline-gray-2 bg-surface-white px-2.5 py-2 text-sm text-ink-gray-7 focus-within:border-outline-gray-4"
			placeholder="Share a message with your team here. You can use @-mentions to notify individual team members. Remember not to include sensitive information."
			@change="(value: string) => (content = value)"
		/>
		<div class="mt-2 flex justify-end">
			<button
				class="h-[30px] rounded-[7px] bg-blue-500 px-4 text-sm font-bold text-white hover:bg-surface-blue-3 disabled:cursor-not-allowed disabled:opacity-50"
				:disabled="
					(!stripHtml(content) && !content.includes('<img')) || addComment.loading
				"
				@click="submit"
			>
				Post
			</button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { inject, ref } from "vue";
import { TextEditor } from "frappe-ui";

import { JobApplicant, stripHtml, useMethod, useUsers } from "../../../data/jobApplicant";

const props = defineProps<{ doc: JobApplicant }>();
const emit = defineEmits<{ posted: [] }>();

const currentUser = inject<{ data: { name: string; full_name: string } }>("user")!;
const users = useUsers();
const content = ref("");

// mentions render as <span class="mention" data-id="user@example.com">, which Frappe picks up for notifications
const addComment = useMethod("frappe.desk.form.utils.add_comment", () => {
	content.value = "";
	emit("posted");
});

function submit() {
	addComment.submit({
		reference_doctype: "Job Applicant",
		reference_name: props.doc.name,
		content: content.value,
		comment_email: currentUser.data.name,
		comment_by: currentUser.data.full_name,
	});
}
</script>
