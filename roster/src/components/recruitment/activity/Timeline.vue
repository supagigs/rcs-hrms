<template>
	<div class="flex min-h-0 flex-1 flex-col">
		<div ref="scroller" class="flex-1 overflow-y-auto px-5 py-4">
			<template v-for="group in groups" :key="group.date">
				<div class="mb-3 mt-3.5 text-center text-xs text-ink-gray-4">{{ group.date }}</div>

				<template v-for="item in group.items" :key="item.key">
					<div
						v-if="item.type === 'comment'"
						class="mb-[18px] rounded-[9px] bg-surface-gray-2 px-3 py-2.5"
					>
						<div class="mb-1 flex items-center gap-2 text-xs">
							<span
								class="flex size-5 items-center justify-center rounded-full bg-surface-violet-1 text-2xs font-bold text-ink-violet-1"
							>
								{{ displayName(item.owner)[0] }}
							</span>
							<span class="font-semibold text-ink-gray-9">{{
								displayName(item.owner)
							}}</span>
							<span class="text-ink-gray-4">{{
								formatDateTime(item.creation)
							}}</span>
						</div>
						<!-- Comment content is sanitized server-side (Comment.validate) -->
						<div
							class="prose-sm max-w-none text-sm text-ink-gray-7"
							v-html="item.content"
						/>
					</div>

					<div
						v-else
						class="mb-[18px] text-center text-sm leading-relaxed text-ink-gray-7"
					>
						{{ displayName(item.owner) }} {{ item.text }}
						<div class="text-xs text-ink-gray-4">
							{{ formatDateTime(item.creation) }}
						</div>
					</div>
				</template>
			</template>
			<p
				v-if="docinfo && docinfo.versions.length >= 10"
				class="text-center text-xs text-ink-gray-4"
			>
				Only the latest 10 field changes are shown.
			</p>
		</div>

		<CommentBox :doc="doc" class="border-t border-outline-gray-1" @posted="emit('updated')" />
	</div>
</template>

<script setup lang="ts">
import { computed, inject, nextTick, ref, watch } from "vue";

import { DocInfo, JobApplicant, stripHtml, userLabel, useUsers } from "../../../data/jobApplicant";
import { dayjs } from "../../../utils";
import CommentBox from "./CommentBox.vue";

const props = defineProps<{
	doc: JobApplicant;
	docinfo?: DocInfo;
	openingTitle?: string | null;
}>();
const emit = defineEmits<{ updated: [] }>();

const currentUser = inject<{ data: { name: string } }>("user")!;
const users = useUsers();

// the web form inserts as Guest, so a Guest-created applicant applied themselves
const displayName = (owner: string) => {
	if (owner === currentUser.data?.name) return "You";
	if (owner === "Guest") return props.doc.applicant_name;
	return userLabel(owner, users.data);
};

type TimelineItem = {
	key: string;
	type: "comment" | "event";
	creation: string;
	owner: string;
	content?: string;
	text?: string;
};

const FIELD_LABELS: Record<string, string> = {
	applicant_rating: "rating",
	job_title: "job opening",
	custom_internal_notes: "internal notes",
	custom_linkedin_profile: "LinkedIn profile",
	custom_consent_given: "consent",
	custom_consent_given_on: "",
	resume_attachment: "resume",
};

const opening = computed(() => props.openingTitle || props.doc.job_title || "");
const onOpening = computed(() => (opening.value ? ` on ${opening.value}` : ""));

function describeChange([field, from, to]: [string, unknown, unknown]) {
	if (field === "status") return `updated stage ${from || "—"} → ${to || "—"}${onOpening.value}`;
	if (field === "applicant_rating")
		return `rated the applicant ${Math.round(Number(to || 0) * 5)} / 5`;

	const label = FIELD_LABELS[field] ?? field.replace(/^custom_/, "").replace(/_/g, " ");
	if (!label) return "";
	const show = (value: unknown) => stripHtml(String(value ?? "")).slice(0, 60) || "empty";
	// long or rich-text values (e.g. notes) only get a mention
	if (String(to ?? "").length > 60 || /<[a-z]/i.test(String(to ?? "")))
		return `updated ${label}`;
	return `changed ${label} from ${show(from)} to ${show(to)}`;
}

const items = computed<TimelineItem[]>(() => {
	const docinfo = props.docinfo;
	const out: TimelineItem[] = [
		{
			key: "created",
			type: "event",
			creation: props.doc.creation,
			owner: props.doc.owner,
			text:
				props.doc.owner === "Guest"
					? `applied${opening.value ? ` to ${opening.value}` : ""}`
					: "added this applicant",
		},
	];
	if (!docinfo) return out;

	for (const version of docinfo.versions) {
		let data: { changed?: [string, unknown, unknown][] } = {};
		try {
			data = JSON.parse(version.data);
		} catch {
			continue;
		}
		(data.changed || []).forEach((change, i) => {
			const text = describeChange(change);
			if (text)
				out.push({
					key: `${version.name}-${i}`,
					type: "event",
					creation: version.creation,
					owner: version.owner,
					text,
				});
		});
	}

	for (const comment of docinfo.comments) {
		out.push({
			key: comment.name,
			type: "comment",
			creation: comment.creation,
			owner: comment.owner,
			content: comment.content,
		});
	}

	for (const email of docinfo.communications) {
		const received = email.sent_or_received === "Received";
		out.push({
			key: email.name,
			type: "event",
			creation: email.communication_date || email.creation,
			owner: received ? email.sender_full_name || email.sender || "" : email.sender || "",
			text: `${received ? "emailed" : "sent an email"}: ${email.subject || "(no subject)"}`,
		});
	}

	return out.sort((a, b) => a.creation.localeCompare(b.creation));
});

const groups = computed(() => {
	const byDate: { date: string; items: TimelineItem[] }[] = [];
	for (const item of items.value) {
		const date = dayjs(item.creation).format("dddd, MMMM D");
		if (byDate.at(-1)?.date !== date) byDate.push({ date, items: [] });
		byDate.at(-1)!.items.push(item);
	}
	return byDate;
});

const formatDateTime = (value: string) => dayjs(value).format("MMM D, YYYY h:mm A");

// newest activity sits above the comment box, so keep the list scrolled to the bottom
const scroller = ref<HTMLElement | null>(null);
watch(
	() => items.value.length,
	() => nextTick(() => scroller.value?.scrollTo({ top: scroller.value.scrollHeight })),
	{ immediate: true },
);
</script>
