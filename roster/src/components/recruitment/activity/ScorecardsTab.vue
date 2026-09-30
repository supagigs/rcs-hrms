<template>
	<div class="flex-1 overflow-y-auto px-5 py-4">
		<LoadingIndicator v-if="loading && !summary" class="mx-auto size-5 text-ink-gray-5" />
		<template
			v-else-if="summary && (summary.feedback.length || summary.pending_feedback.length)"
		>
			<a
				v-for="feedback in summary.feedback"
				:key="feedback.name"
				:target="linkTarget"
				:href="deskUrl('Interview Feedback', feedback.name)"
				class="mb-2.5 block rounded-[9px] border border-outline-gray-2 p-3.5 hover:bg-surface-gray-1"
			>
				<div class="flex items-center justify-between gap-2">
					<span class="truncate text-sm font-bold text-ink-gray-9">
						{{ feedback.interview_type }}
					</span>
					<span class="shrink-0 text-xs text-ink-gray-5">{{
						feedback.interviewer_name
					}}</span>
				</div>
				<div class="mt-2 flex items-center justify-between gap-2">
					<StarRating
						:value="toStars(feedback.average_rating)"
						:label="`${toStars(feedback.average_rating, summary.rating_scale)} / ${
							summary.rating_scale
						}`"
					/>
					<StatusPill v-if="feedback.result" :label="feedback.result" size="sm" />
				</div>
				<p
					v-if="feedback.feedback"
					class="mt-1.5 whitespace-pre-line text-[12.5px] text-ink-gray-6"
					v-text="feedback.feedback"
				/>
			</a>

			<div
				v-for="pending in summary.pending_feedback"
				:key="`${pending.interview}-${pending.user}`"
				class="mb-2.5 rounded-[9px] border border-outline-gray-2 p-3.5"
			>
				<div class="flex items-center justify-between gap-2">
					<span class="truncate text-sm font-bold text-ink-gray-9">
						{{ pending.interview_type }}
					</span>
					<span class="shrink-0 text-xs text-ink-gray-5">{{ pending.full_name }}</span>
				</div>
				<div class="mt-2"><StarRating :value="0" label="Pending" /></div>
				<p class="mt-1.5 text-[12.5px] text-ink-gray-6">Not yet submitted.</p>
			</div>

			<section v-if="summary.skill_ratings.length" class="mt-4">
				<h4 class="mb-2 text-xs font-bold uppercase tracking-wide text-ink-gray-4">
					Average by skill
				</h4>
				<div
					v-for="skill in summary.skill_ratings"
					:key="skill.skill"
					class="flex items-center justify-between py-1"
				>
					<span class="truncate text-sm text-ink-gray-7">{{ skill.skill }}</span>
					<StarRating
						:value="toStars(skill.rating)"
						:label="String(toStars(skill.rating))"
					/>
				</div>
			</section>
		</template>
		<EmptyState
			v-else
			icon="star"
			title="No scorecards yet"
			description="Interview Feedback from each interviewer shows up here once it's submitted."
		/>
	</div>
</template>

<script setup lang="ts">
import { LoadingIndicator } from "frappe-ui";

import { CandidateSummary, deskUrl, toStars } from "../../../data/jobApplicant";
import { linkTarget } from "../../../utils/embed";
import EmptyState from "../EmptyState.vue";
import StarRating from "../StarRating.vue";
import StatusPill from "../StatusPill.vue";

defineProps<{ summary?: CandidateSummary | null; loading?: boolean }>();
</script>
