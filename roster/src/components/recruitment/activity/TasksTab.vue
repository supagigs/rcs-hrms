<template>
	<div class="flex min-h-0 flex-1 flex-col">
		<div class="flex-1 overflow-y-auto px-5 py-4">
			<div v-if="tasks.data?.length">
				<button
					v-for="task in tasks.data"
					:key="task.name"
					class="flex w-full items-start gap-2.5 rounded-md px-1 py-2.5 text-left hover:bg-surface-gray-1"
					:aria-pressed="task.status === 'Closed'"
					@click="toggle(task)"
				>
					<span
						class="mt-px flex size-[18px] shrink-0 items-center justify-center rounded-[5px] border-[1.5px]"
						:class="
							task.status === 'Closed'
								? 'border-[--ink-blue-2] bg-[--ink-blue-2]'
								: 'border-outline-gray-3 bg-surface-white'
						"
					>
						<FeatherIcon
							v-if="task.status === 'Closed'"
							name="check"
							class="size-[11px] text-ink-white"
							:stroke-width="3"
						/>
					</span>
					<span class="min-w-0">
						<span
							class="block text-[13.5px]"
							:class="
								task.status === 'Closed'
									? 'text-ink-gray-4 line-through'
									: 'text-ink-gray-7'
							"
						>
							{{ stripHtml(task.description) }}
						</span>
						<span class="block text-xs text-ink-gray-4">
							{{ userLabel(task.allocated_to, users.data) }}
						</span>
					</span>
				</button>
			</div>
			<EmptyState
				v-else
				icon="check-square"
				title="No tasks yet"
				description="Tasks are Assign To items on this applicant. Add one below."
			/>
		</div>

		<div class="flex shrink-0 flex-col gap-2 border-t border-outline-gray-1 px-5 py-3">
			<TextInput
				v-model="description"
				placeholder="New task, e.g. Verify degree certificate"
				@keydown.enter="addTask"
			/>
			<div class="flex items-center gap-2">
				<Autocomplete
					v-model="assignee"
					class="flex-1"
					:options="users.data || []"
					placeholder="Assign to (default: you)"
				/>
				<button
					class="h-[30px] rounded-[7px] bg-blue-500 px-4 text-sm font-bold text-white hover:bg-surface-blue-3 disabled:opacity-50"
					:disabled="!description.trim() || assign.loading"
					@click="addTask"
				>
					Add
				</button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { inject, ref } from "vue";
import { Autocomplete, FeatherIcon, TextInput, useList } from "frappe-ui";

import {
	JobApplicant,
	UserOption,
	stripHtml,
	useMethod,
	userLabel,
	useUsers,
} from "../../../data/jobApplicant";
import { raiseToast } from "../../../utils";
import EmptyState from "../EmptyState.vue";

const props = defineProps<{ doc: JobApplicant }>();
const emit = defineEmits<{ updated: [] }>();

const currentUser = inject<{ data: { name: string; full_name: string } }>("user")!;
const users = useUsers();

type Task = { name: string; description: string; allocated_to: string; status: string };

// ToDo's own permission rules apply: users see tasks assigned to or by them
const tasks = useList({
	doctype: "ToDo",
	fields: ["name", "description", "allocated_to", "status"],
	filters: () => ({
		reference_type: "Job Applicant",
		reference_name: props.doc.name,
		status: ["!=", "Cancelled"],
	}),
	orderBy: "creation asc",
	limit: 100,
	refetch: true,
	onError: (error: Error) => raiseToast("error", error.message),
});

function toggle(task: Task) {
	tasks.setValue
		.submit({ name: task.name, status: task.status === "Closed" ? "Open" : "Closed" })
		.then(() => {
			if (!tasks.setValue.error) emit("updated");
		});
}

const description = ref("");
const assignee = ref<UserOption | null>(null);

const assign = useMethod("frappe.desk.form.assign_to.add", () => {
	description.value = "";
	assignee.value = null;
	tasks.reload();
	emit("updated");
});

function addTask() {
	if (!description.value.trim()) return;

	assign.submit({
		args: {
			assign_to: [assignee.value?.value || currentUser.data.name],
			doctype: "Job Applicant",
			name: props.doc.name,
			description: description.value.trim(),
		},
	});
}
</script>
