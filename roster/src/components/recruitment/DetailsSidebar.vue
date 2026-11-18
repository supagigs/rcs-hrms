<template>
	<aside class="overflow-y-auto px-[22px] py-5">
		<h3 class="mb-4 text-[15px] font-bold text-ink-gray-9">Details</h3>

		<div class="flex flex-col gap-4 text-sm text-ink-gray-7">
			<div v-for="row in detailRows" :key="row.icon" class="flex items-start gap-2.5">
				<FeatherIcon :name="row.icon" class="mt-px size-[15px] shrink-0 text-ink-gray-4" />
				<StatusPill v-if="row.pill" :label="row.pill" />
				<a
					v-else-if="row.href"
					:href="row.href"
					:target="row.external ? '_blank' : row.desk ? linkTarget : undefined"
					:rel="row.external ? 'noopener noreferrer' : undefined"
					class="min-w-0 break-words hover:underline"
					:class="row.strong ? 'font-semibold text-ink-gray-9' : 'text-ink-gray-7'"
				>
					{{ row.value }}
				</a>
				<span
					v-else
					class="min-w-0 break-words"
					:class="row.strong ? 'font-semibold text-ink-gray-9' : ''"
				>
					{{ row.value }}
				</span>
			</div>
		</div>

		<div class="my-[18px] h-px bg-surface-gray-2" />

		<div class="mb-2 flex items-center justify-between">
			<span class="text-sm font-bold text-ink-gray-9">Tags</span>
			<button
				class="rounded p-0.5 text-ink-gray-4 hover:bg-surface-gray-2 hover:text-ink-gray-7"
				aria-label="Add tag"
				@click="showTagInput = true"
			>
				<FeatherIcon name="plus" class="size-3.5" />
			</button>
		</div>
		<div v-if="tags.length" class="mb-2 flex flex-wrap gap-1.5">
			<span
				v-for="tag in tags"
				:key="tag"
				class="inline-flex items-center gap-1 rounded-full bg-surface-gray-2 py-0.5 pl-2.5 pr-1.5 text-xs font-semibold text-ink-gray-7"
			>
				{{ tag }}
				<button
					class="text-ink-gray-4 hover:text-ink-gray-8"
					:aria-label="`Remove ${tag}`"
					@click="removeTag.submit({ tag, dt: 'Job Applicant', dn: doc.name })"
				>
					<FeatherIcon name="x" class="size-3" />
				</button>
			</span>
		</div>
		<TextInput
			v-if="showTagInput"
			v-model="newTag"
			size="sm"
			placeholder="Type a tag and press Enter"
			@keydown.enter="submitTag"
			@keydown.esc="showTagInput = false"
		/>
		<button
			v-else-if="!tags.length"
			class="text-xs text-ink-gray-4 hover:text-ink-gray-7"
			@click="showTagInput = true"
		>
			+ Add tags
		</button>
	</aside>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { FeatherIcon, TextInput } from "frappe-ui";

import {
	JobApplicant,
	deskUrl,
	displayUrl,
	formatAmount,
	useMethod,
	webUrl,
} from "../../data/jobApplicant";
import { linkTarget } from "../../utils/embed";
import StatusPill from "./StatusPill.vue";

const props = defineProps<{ doc: JobApplicant; openingTitle?: string | null }>();
const emit = defineEmits<{ updated: [] }>();

type DetailRow = {
	icon: string;
	value?: string;
	href?: string;
	external?: boolean;
	strong?: boolean;
	pill?: string;
	desk?: boolean;
};

const detailRows = computed(() => {
	const doc = props.doc;
	const rows: DetailRow[] = [
		{ icon: "user", value: doc.applicant_name, strong: true },
		{
			icon: "briefcase",
			value: props.openingTitle || doc.job_title,
			href: doc.job_title && deskUrl("Job Opening", doc.job_title),
			desk: true,
		},
		{ icon: "award", value: doc.designation },
		{ icon: "credit-card", value: doc.status, pill: doc.status },
		{
			icon: "phone",
			value: doc.phone_number,
			href: doc.phone_number && `tel:${doc.phone_number}`,
		},
		{ icon: "mail", value: doc.email_id, href: `mailto:${doc.email_id}` },
		{ icon: "map-pin", value: doc.country },
		{ icon: "dollar-sign", value: salaryExpectation.value },
		...profileLinks.value,
		{ icon: "tag", value: doc.source && `Source: ${doc.source}` },
	];
	return rows.filter((row) => row.value);
});

// applicant's own links, shown only when set (edited in the More tab); only plain web links
// become clickable
const profileLinks = computed(() => {
	const doc = props.doc;
	const links: [string, string | undefined, (url: string) => string][] = [
		["linkedin", doc.custom_linkedin_profile, () => "LinkedIn profile"],
		["github", doc.custom_github_profile, displayUrl],
		["globe", doc.custom_portfolio_url, displayUrl],
		["link", doc.custom_other_profile_url, displayUrl],
	];
	return links.flatMap(([icon, url, label]): DetailRow[] => {
		const href = webUrl(url);
		if (href) return [{ icon, value: label(href), href, external: true }];
		return url ? [{ icon, value: url }] : [];
	});
});

const salaryExpectation = computed(() => {
	const { lower_range: lower, upper_range: upper, currency } = props.doc;
	if (!lower && !upper) return "";
	const format = (value?: number) => (value ? formatAmount(value, currency || "USD") : "");
	return [format(lower), format(upper)].filter(Boolean).join(" – ");
});

const tags = computed(() => (props.doc._user_tags || "").split(",").filter(Boolean));

const showTagInput = ref(false);
const newTag = ref("");
const addTag = useMethod("frappe.desk.doctype.tag.tag.add_tag", () => {
	newTag.value = "";
	showTagInput.value = false;
	emit("updated");
});
const removeTag = useMethod("frappe.desk.doctype.tag.tag.remove_tag", () => emit("updated"));

function submitTag() {
	const tag = newTag.value.trim();
	if (tag) addTag.submit({ tag, dt: "Job Applicant", dn: props.doc.name });
}
</script>
