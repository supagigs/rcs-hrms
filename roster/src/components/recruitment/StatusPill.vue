<template>
	<span
		class="inline-flex shrink-0 items-center whitespace-nowrap rounded-full font-bold"
		:class="[
			size === 'sm' ? 'px-[9px] py-[3px] text-2xs' : 'px-2.5 py-[3px] text-xs',
			pillClasses(label),
		]"
	>
		{{ label }}
	</span>
</template>

<script setup lang="ts">
import { pillClasses } from "../../data/jobApplicant";

withDefaults(defineProps<{ label: string; size?: "sm" | "md" }>(), { size: "md" });
</script>
