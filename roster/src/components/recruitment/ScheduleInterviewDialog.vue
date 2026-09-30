<template>
	<Dialog v-model="open" :options="dialogOptions">
		<template #body-content>
			<div class="flex flex-col gap-4">
				<div>
					<label class="mb-1.5 block text-xs text-ink-gray-5">Interview Type</label>
					<Autocomplete
						v-model="interviewType"
						:options="interviewTypeOptions"
						placeholder="Select interview type"
					/>
				</div>
				<FormControl v-model="scheduledOn" type="date" label="Scheduled On" />
				<div class="grid grid-cols-2 gap-4">
					<FormControl v-model="fromTime" type="time" label="From Time" />
					<FormControl v-model="toTime" type="time" label="To Time" />
				</div>
				<div>
					<label class="mb-1.5 block text-xs text-ink-gray-5">Interviewers</label>
					<Autocomplete
						v-model="interviewers"
						:options="users.data || []"
						:multiple="true"
						placeholder="Select interviewers"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Autocomplete, Dialog, FormControl, dayjs, useCall, useList } from "frappe-ui";

import { JobApplicant, useMethod, userLabel, useUsers } from "../../data/jobApplicant";
import { raiseToast } from "../../utils";

type Option = { label: string; value: string };

const props = defineProps<{ doc: JobApplicant }>();
const emit = defineEmits<{ scheduled: [] }>();
const open = defineModel<boolean>({ default: false });

const interviewType = ref<Option | null>(null);
const scheduledOn = ref(dayjs().format("YYYY-MM-DD"));
const fromTime = ref("");
const toTime = ref("");
const interviewers = ref<Option[]>([]);

type InterviewType = { name: string; designation?: string };

const interviewTypes = useList({
	doctype: "Interview Type",
	fields: ["name", "designation"],
	limit: 500,
	immediate: false,
});

// same filter as the Desk dialog: types for the applicant's designation or for any designation
const interviewTypeOptions = computed(() =>
	(interviewTypes.data || [])
		.filter(
			(type: InterviewType) =>
				!type.designation ||
				!props.doc.designation ||
				type.designation === props.doc.designation,
		)
		.map((type: InterviewType) => ({ label: type.name, value: type.name })),
);

const users = useUsers();

const defaultInterviewers = useCall({
	url: "/api/v2/method/hrms.hr.doctype.interview.interview.get_interviewers",
	immediate: false,
	onSuccess(data: { interviewer: string }[]) {
		interviewers.value = (data || []).map((row) => ({
			label: userLabel(row.interviewer, users.data),
			value: row.interviewer,
		}));
	},
});

watch(open, (isOpen) => {
	if (isOpen && !interviewTypes.data) interviewTypes.reload();
});

watch(interviewType, (type) => {
	if (type?.value) defaultInterviewers.submit({ interview_type: type.value });
});

const schedule = useMethod(
	"hrms.hr.doctype.job_applicant.job_applicant.schedule_interview",
	() => {
		raiseToast("success", "Interview scheduled");
		open.value = false;
		interviewType.value = null;
		interviewers.value = [];
		emit("scheduled");
	},
);

function submit() {
	if (!interviewType.value || !scheduledOn.value || !fromTime.value || !toTime.value) {
		raiseToast("error", "Interview Type, date and times are required");
		return;
	}

	schedule.submit({
		job_applicant: props.doc.name,
		interview_type: interviewType.value.value,
		scheduled_on: scheduledOn.value,
		from_time: fromTime.value,
		to_time: toTime.value,
		interviewers: interviewers.value.map((user) => ({ interviewer: user.value })),
	});
}

const dialogOptions = computed(() => ({
	title: `Schedule Interview for ${props.doc.applicant_name}`,
	actions: [{ label: "Schedule", variant: "solid", loading: schedule.loading, onClick: submit }],
}));
</script>
