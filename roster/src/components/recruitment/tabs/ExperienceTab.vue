<template>
	<div class="flex-1 overflow-y-auto px-8 py-7">
		<div class="flex max-w-[640px] flex-col gap-7">
			<section>
				<div class="mb-4 flex items-baseline justify-between gap-3">
					<h2 class="text-[15px] font-bold text-ink-gray-9">Work Experience</h2>
					<span v-if="jobs.length" class="text-xs text-ink-gray-5">
						{{ totalExperience }}
					</span>
				</div>

				<ol v-if="jobs.length" class="relative">
					<li
						v-for="(job, index) in jobs"
						:key="job.name"
						class="relative flex gap-3.5 pb-5 last:pb-0"
					>
						<!-- timeline rail -->
						<div class="relative flex w-3 shrink-0 justify-center">
							<span
								class="mt-[5px] size-2.5 rounded-full"
								:class="
									job.currently_working
										? 'bg-[--ink-green-3]'
										: 'bg-[--ink-gray-4]'
								"
							/>
							<span
								v-if="index < jobs.length - 1"
								class="absolute bottom-[-6px] top-[14px] w-px bg-[--outline-gray-2]"
							/>
						</div>

						<div class="min-w-0 flex-1">
							<div class="flex flex-wrap items-baseline gap-x-2">
								<span class="text-sm font-semibold text-ink-gray-9">
									{{ job.designation || job.company_name }}
								</span>
								<StatusPill
									v-if="job.currently_working"
									label="Current"
									size="sm"
								/>
							</div>
							<div v-if="job.designation" class="text-sm text-ink-gray-7">
								{{ job.company_name }}
							</div>
							<div class="mt-0.5 text-xs text-ink-gray-5">
								{{ jobPeriod(job) }}
								<template v-if="job.location"> · {{ job.location }}</template>
							</div>
							<p
								v-if="job.description"
								class="mt-1.5 whitespace-pre-wrap text-[13px] text-ink-gray-7"
							>
								{{ job.description }}
							</p>
						</div>
					</li>
				</ol>
				<EmptyState
					v-else
					icon="briefcase"
					title="No work experience"
					description="Applicants add their jobs on the application form; HR can add them from the classic form."
				/>
			</section>

			<section>
				<h2 class="mb-4 text-[15px] font-bold text-ink-gray-9">Education</h2>

				<div v-if="education.length" class="flex flex-col gap-3">
					<div
						v-for="row in education"
						:key="row.name"
						class="rounded-[9px] border border-outline-gray-2 px-4 py-3"
					>
						<div class="flex items-baseline justify-between gap-3">
							<span class="text-sm font-semibold text-ink-gray-9">
								{{ row.qualification || row.school_univ }}
							</span>
							<span
								v-if="row.year_of_passing"
								class="shrink-0 text-xs text-ink-gray-5"
							>
								{{ row.year_of_passing }}
							</span>
						</div>
						<div
							v-if="row.qualification && row.school_univ"
							class="text-sm text-ink-gray-7"
						>
							{{ row.school_univ }}
						</div>
						<div v-if="educationDetails(row)" class="mt-0.5 text-xs text-ink-gray-5">
							{{ educationDetails(row) }}
						</div>
					</div>
				</div>
				<EmptyState v-else icon="book-open" title="No education added" />
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import {
	Education,
	JobApplicant,
	WorkExperience,
	formatDate,
	formatDuration,
} from "../../../data/jobApplicant";
import EmptyState from "../EmptyState.vue";
import StatusPill from "../StatusPill.vue";

const props = defineProps<{ doc: JobApplicant }>();

// most recent first; current jobs lead
const jobs = computed(() =>
	[...(props.doc.custom_work_experience || [])].sort(
		(a, b) =>
			(b.currently_working || 0) - (a.currently_working || 0) ||
			(b.from_date || "").localeCompare(a.from_date || ""),
	),
);

const education = computed(() =>
	[...(props.doc.custom_education || [])].sort(
		(a, b) => (b.year_of_passing || 0) - (a.year_of_passing || 0),
	),
);

// computed on save by the server (overlapping jobs count once)
const totalExperience = computed(() => {
	const years = props.doc.custom_total_experience_years || 0;
	if (!years) return "Less than a year in total";
	return `${years} ${years === 1 ? "year" : "years"} in total`;
});

function jobPeriod(job: WorkExperience) {
	if (!job.from_date) return "";
	const end = job.currently_working ? null : job.to_date;
	const from = formatDate(job.from_date, "MMM YYYY");
	const to = job.currently_working ? "Present" : formatDate(end, "MMM YYYY");
	if (!job.currently_working && !end) return from;
	return `${from} – ${to} · ${formatDuration(job.from_date, end)}`;
}

function educationDetails(row: Education) {
	return [row.level, row.maj_opt_subj, row.class_per && `Grade: ${row.class_per}`]
		.filter(Boolean)
		.join(" · ");
}
</script>
