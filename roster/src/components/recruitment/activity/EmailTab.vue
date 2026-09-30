<template>
	<div class="flex-1 overflow-y-auto px-5 py-4">
		<template v-if="groups.length">
			<template v-for="group in groups" :key="group.date">
				<div class="mb-4 mt-1.5 text-center text-xs text-ink-gray-4">{{ group.date }}</div>

				<div
					v-for="email in group.emails"
					:key="email.name"
					class="mb-4"
					:class="email.sent ? 'text-right' : 'text-left'"
				>
					<div
						class="flex items-center gap-2"
						:class="email.sent ? 'flex-row-reverse' : ''"
					>
						<span
							class="flex size-6 shrink-0 items-center justify-center rounded-full text-2xs font-bold"
							:class="
								email.sent
									? 'bg-surface-orange-1 text-ink-amber-3'
									: 'bg-surface-violet-1 text-ink-violet-1'
							"
						>
							{{ email.from[0]?.toUpperCase() }}
						</span>
						<span class="truncate text-sm font-semibold text-ink-gray-9">{{
							email.from
						}}</span>
						<span class="shrink-0 text-2xs text-ink-gray-4">{{ email.time }}</span>
					</div>
					<!-- rendered as text: email bodies can come from outside senders -->
					<div
						class="mt-1.5 inline-block max-w-full rounded-[9px] px-3 py-2.5 text-left text-sm leading-relaxed text-ink-gray-7"
						:class="email.sent ? 'bg-surface-blue-2' : 'bg-surface-gray-2'"
					>
						<div class="font-semibold text-ink-gray-9">{{ email.subject }}</div>
						<p class="line-clamp-[8] whitespace-pre-line" v-text="email.body" />
					</div>
				</div>
			</template>
		</template>
		<EmptyState
			v-else
			icon="mail"
			title="No emails yet"
			description="Emails sent from here, and the applicant's replies, show up in this thread."
		/>

		<Dialog v-model="compose" :options="dialogOptions">
			<template #body-content>
				<div class="flex flex-col gap-4">
					<FormControl v-model="recipients" label="To" />
					<FormControl v-model="subject" label="Subject" />
					<TextEditor
						:content="message"
						:fixed-menu="true"
						editor-class="prose-sm max-w-none min-h-[10rem] rounded-b-lg border border-t-0 border-outline-gray-modals px-3 py-2"
						@change="(value: string) => (message = value)"
					/>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, inject, ref } from "vue";
import { Dialog, FormControl, TextEditor } from "frappe-ui";

import { Communication, JobApplicant, stripHtml, useMethod } from "../../../data/jobApplicant";
import { dayjs, raiseToast } from "../../../utils";
import EmptyState from "../EmptyState.vue";

const props = defineProps<{ doc: JobApplicant; communications: Communication[] }>();
const emit = defineEmits<{ updated: [] }>();
const compose = defineModel<boolean>("compose", { default: false });

const currentUser = inject<{ data: { name: string } }>("user")!;

// oldest first, like a chat thread
const groups = computed(() => {
	const emails = props.communications
		.filter((row) => (row.communication_medium || "Email") === "Email")
		.map((row) => {
			const sent = row.sent_or_received !== "Received";
			const at = row.communication_date || row.creation;
			return {
				name: row.name,
				at,
				sent,
				from:
					sent && row.sender === currentUser.data?.name
						? "You"
						: row.sender_full_name || row.sender || "",
				subject: row.subject || "(no subject)",
				body: stripHtml(row.content),
				time: dayjs(at).format("h:mm A"),
			};
		})
		.sort((a, b) => a.at.localeCompare(b.at));

	const byDate: { date: string; emails: typeof emails }[] = [];
	for (const email of emails) {
		const date = dayjs(email.at).format("dddd, MMMM D");
		if (byDate.at(-1)?.date !== date) byDate.push({ date, emails: [] });
		byDate.at(-1)!.emails.push(email);
	}
	return byDate;
});

const recipients = ref(props.doc.email_id);
const subject = ref("");
const message = ref("");

const sendEmail = useMethod("frappe.core.doctype.communication.email.make", () => {
	raiseToast("success", "Email sent");
	compose.value = false;
	subject.value = "";
	message.value = "";
	emit("updated");
});

function send() {
	if (!recipients.value || !subject.value || !stripHtml(message.value)) {
		raiseToast("error", "Recipient, subject and message are required");
		return;
	}

	sendEmail.submit({
		doctype: "Job Applicant",
		name: props.doc.name,
		recipients: recipients.value,
		subject: subject.value,
		content: message.value,
		communication_medium: "Email",
		sent_or_received: "Sent",
		send_email: 1,
	});
}

const dialogOptions = computed(() => ({
	title: "New Email",
	size: "2xl",
	actions: [{ label: "Send", variant: "solid", loading: sendEmail.loading, onClick: send }],
}));
</script>
