<template>
	<div
		class="flex flex-col items-center gap-1.5 rounded-[9px] border border-dashed border-outline-gray-2 px-6 py-8 text-center"
	>
		<FeatherIcon :name="icon" class="mb-1 size-5 text-ink-gray-4" />
		<p class="text-sm font-semibold text-ink-gray-7">{{ title }}</p>
		<p v-if="description" class="max-w-xs text-xs text-ink-gray-5">{{ description }}</p>
		<slot />
	</div>
</template>

<script setup lang="ts">
import { FeatherIcon } from "frappe-ui";

defineProps<{ icon: string; title: string; description?: string }>();
</script>
