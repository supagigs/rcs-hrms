<template>
	<div class="flex-1 overflow-y-auto px-8 py-7">
		<div class="max-w-[640px]">
			<div class="mb-4 flex items-baseline justify-between gap-3">
				<h2 class="text-[15px] font-bold text-ink-gray-9">Screening Questionnaire</h2>
				<span v-if="answers.length" class="text-xs text-ink-gray-5">
					{{ answeredCount }} of {{ answers.length }} answered
				</span>
			</div>

			<div v-if="answers.length" class="flex flex-col gap-[18px]">
				<div v-for="{ response, display, help } in answers" :key="response.name">
					<div class="text-sm font-semibold text-ink-gray-5">
						{{ response.question }}
					</div>
					<p v-if="help" class="mt-0.5 whitespace-pre-wrap text-xs text-ink-gray-4">
						{{ help }}
					</p>

					<div class="mt-1.5 text-[13.5px] text-ink-gray-9">
						<span v-if="display.kind === 'empty'" class="text-ink-gray-4">
							Not answered
						</span>
						<div v-else-if="display.kind === 'chips'" class="flex flex-wrap gap-1.5">
							<span
								v-for="item in display.items"
								:key="item"
								class="rounded-full bg-surface-gray-2 px-2.5 py-0.5 text-xs font-semibold text-ink-gray-7"
							>
								{{ item }}
							</span>
						</div>
						<StatusPill
							v-else-if="display.kind === 'pill'"
							:label="display.label"
							size="sm"
						/>
						<a
							v-else-if="display.kind === 'link'"
							:href="display.href"
							:target="display.external ? '_blank' : undefined"
							:rel="display.external ? 'noopener noreferrer' : undefined"
							class="break-all text-ink-blue-3 hover:underline"
						>
							{{ display.label }}
						</a>
						<span v-else class="whitespace-pre-wrap break-words">{{
							display.text
						}}</span>
					</div>
				</div>
			</div>
			<EmptyState
				v-else
				icon="help-circle"
				title="No screening answers"
				description="Questions are set on the Job Opening and answered on the public application form."
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { createResource } from "frappe-ui";

import {
	JobApplicant,
	ScreeningResponse,
	displayUrl,
	formatAmount,
	formatDate,
	webUrl,
} from "../../../data/jobApplicant";
import { dayjs } from "../../../utils";
import EmptyState from "../EmptyState.vue";
import StatusPill from "../StatusPill.vue";

const props = defineProps<{ doc: JobApplicant }>();

type Display =
	| { kind: "empty" }
	| { kind: "chips"; items: string[] }
	| { kind: "pill"; label: string }
	| { kind: "link"; href: string; label: string; external: boolean }
	| { kind: "text"; text: string };

// rendered from the copies of question text and type stored with each answer, so answers keep
// their meaning after the Job Opening's questions change
function toDisplay(response: ScreeningResponse): Display {
	const answer = (response.answer || "").trim();
	if (!answer) return { kind: "empty" };

	switch (response.question_type) {
		case "Multiple Select":
			return { kind: "chips", items: answer.split("\n").filter(Boolean) };
		case "Yes/No":
			return { kind: "pill", label: answer };
		case "URL": {
			const href = webUrl(answer);
			return href
				? { kind: "link", href, label: displayUrl(href), external: true }
				: { kind: "text", text: answer };
		}
		case "Email":
			return { kind: "link", href: `mailto:${answer}`, label: answer, external: false };
		case "Number":
		case "Currency": {
			const number = Number(answer.replace(/,/g, ""));
			if (!Number.isFinite(number)) return { kind: "text", text: answer };
			const currency = response.question_type === "Currency" ? response.currency : null;
			return { kind: "text", text: formatAmount(number, currency) };
		}
		case "Date": {
			const value = response.answer_date || answer;
			return { kind: "text", text: dayjs(value).isValid() ? formatDate(value) : answer };
		}
		default:
			return { kind: "text", text: answer };
	}
}

// help text isn't copied onto answers; show the question's current one while it still exists
const questions = createResource({
	url: "frappe.client.get_list",
	makeParams: () => ({
		doctype: "Job Opening Screening Question",
		parent: "Job Opening",
		fields: ["name", "description"],
		filters: { parent: props.doc.job_title, parenttype: "Job Opening" },
		limit_page_length: 100,
	}),
	auto: Boolean(props.doc.job_title && props.doc.custom_screening_responses?.length),
});

const helpText = computed(() => {
	const rows = (questions.data || []) as { name: string; description?: string }[];
	return Object.fromEntries(rows.map((row) => [row.name, row.description || ""]));
});

const answers = computed(() =>
	(props.doc.custom_screening_responses || []).map((response) => ({
		response,
		display: toDisplay(response),
		help: (response.question_row && helpText.value[response.question_row]) || "",
	})),
);

const answeredCount = computed(
	() => answers.value.filter((answer) => answer.display.kind !== "empty").length,
);
</script>
