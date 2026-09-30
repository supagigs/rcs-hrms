<template>
	<section class="rounded-[9px] border border-outline-gray-2">
		<div class="flex items-center justify-between gap-3 px-4 pt-3.5">
			<h3 class="text-sm font-semibold text-ink-gray-8">Profile links &amp; referral</h3>
			<div v-if="changed.length" class="flex items-center gap-2">
				<Button
					variant="ghost"
					label="Discard"
					:disabled="save.loading"
					@click="discard"
				/>
				<Button
					variant="solid"
					theme="blue"
					label="Save"
					:loading="save.loading"
					:disabled="hasErrors"
					@click="submit"
				/>
			</div>
		</div>

		<div class="grid grid-cols-1 gap-x-4 gap-y-3.5 px-4 pb-4 pt-3 min-[1440px]:grid-cols-2">
			<div v-for="field in FIELDS" :key="field.fieldname">
				<FormControl
					v-model="draft[field.fieldname]"
					type="text"
					size="sm"
					:label="field.label"
					:placeholder="field.placeholder"
					@keydown.enter="submit"
				/>
				<p v-if="errors[field.fieldname]" class="mt-1 text-xs text-ink-red-4">
					{{ errors[field.fieldname] }}
				</p>
			</div>
		</div>

		<!-- referrals recorded through Employee Referral aren't edited here -->
		<div
			v-if="doc.employee_referral || doc.source_name"
			class="flex items-center justify-between gap-3 border-t border-outline-gray-1 px-4 py-3 text-sm"
		>
			<span class="text-ink-gray-5">Employee referral</span>
			<a
				:href="
					doc.employee_referral
						? deskUrl('Employee Referral', doc.employee_referral)
						: deskUrl('Employee', doc.source_name)
				"
				:target="linkTarget"
				class="truncate text-ink-gray-7 hover:underline"
			>
				{{ doc.employee_referral || doc.source_name }}
			</a>
		</div>
	</section>
</template>

<script setup lang="ts">
// Inline editing of the applicant's links and referrer. Saves through frappe.client.set_value,
// which loads the document and calls doc.save(), so validation and hooks run as in Desk.
import { computed, reactive, watch } from "vue";
import { Button, FormControl } from "frappe-ui";

import { JobApplicant, deskUrl, useMethod, webUrl } from "../../data/jobApplicant";
import { linkTarget } from "../../utils/embed";
import { raiseToast } from "../../utils";

type Fieldname =
	| "custom_linkedin_profile"
	| "custom_github_profile"
	| "custom_portfolio_url"
	| "custom_other_profile_url"
	| "custom_referrer_name"
	| "custom_referrer_email";

const FIELDS: {
	fieldname: Fieldname;
	label: string;
	placeholder: string;
	kind?: "url" | "email";
}[] = [
	{
		fieldname: "custom_linkedin_profile",
		label: "LinkedIn",
		placeholder: "https://linkedin.com/in/…",
		kind: "url",
	},
	{
		fieldname: "custom_github_profile",
		label: "GitHub",
		placeholder: "https://github.com/…",
		kind: "url",
	},
	{
		fieldname: "custom_portfolio_url",
		label: "Portfolio / Website",
		placeholder: "https://…",
		kind: "url",
	},
	{
		fieldname: "custom_other_profile_url",
		label: "Other Link",
		placeholder: "https://…",
		kind: "url",
	},
	{
		fieldname: "custom_referrer_name",
		label: "Referrer Name",
		placeholder: "Who referred them",
	},
	{
		fieldname: "custom_referrer_email",
		label: "Referrer Email",
		placeholder: "name@example.com",
		kind: "email",
	},
];

const props = defineProps<{ doc: JobApplicant }>();
const emit = defineEmits<{ updated: [] }>();

const current = () =>
	Object.fromEntries(
		FIELDS.map(({ fieldname }) => [fieldname, props.doc[fieldname] || ""]),
	) as Record<Fieldname, string>;

let saved = current();
const draft = reactive(current());

// after a reload, take the new values for fields that weren't being edited
watch(
	() => FIELDS.map(({ fieldname }) => props.doc[fieldname]),
	() => {
		const next = current();
		for (const { fieldname } of FIELDS) {
			if (draft[fieldname] === saved[fieldname]) draft[fieldname] = next[fieldname];
		}
		saved = next;
	},
);

const changed = computed(() =>
	FIELDS.filter(({ fieldname }) => draft[fieldname].trim() !== (props.doc[fieldname] || "")),
);

const errors = computed(() => {
	const messages: Partial<Record<Fieldname, string>> = {};
	for (const { fieldname, kind } of FIELDS) {
		const value = draft[fieldname].trim();
		if (!value) continue;
		if (kind === "url" && !webUrl(value))
			messages[fieldname] = "Enter a full link starting with http:// or https://";
		if (kind === "email" && !/^[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+$/.test(value))
			messages[fieldname] = "Enter a valid email address";
	}
	return messages;
});
const hasErrors = computed(() => Object.keys(errors.value).length > 0);

const save = useMethod("frappe.client.set_value", () => {
	raiseToast("success", "Profile links saved");
	emit("updated");
});

function submit() {
	if (!changed.value.length || hasErrors.value || save.loading) return;
	save.submit({
		doctype: "Job Applicant",
		name: props.doc.name,
		// one save for every changed field
		fieldname: Object.fromEntries(
			changed.value.map(({ fieldname }) => [fieldname, draft[fieldname].trim()]),
		),
	});
}

function discard() {
	Object.assign(draft, current());
}
</script>
