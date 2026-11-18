<template>
	<span class="inline-flex items-center gap-1">
		<svg
			v-for="star in 5"
			:key="star"
			viewBox="0 0 24 24"
			class="size-[13px]"
			:class="
				star <= filled
					? 'fill-[#F5B301] stroke-[#F5B301]'
					: 'fill-none stroke-[--outline-gray-3]'
			"
			stroke-width="1.4"
			aria-hidden="true"
		>
			<path
				d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z"
			/>
		</svg>
		<span v-if="label" class="ml-1 text-xs text-ink-gray-5">{{ label }}</span>
	</span>
</template>

<script setup lang="ts">
import { computed } from "vue";

// read-only 5-star display, `value` is 0-5
const props = defineProps<{ value: number; label?: string }>();
const filled = computed(() => Math.round(props.value));
</script>
