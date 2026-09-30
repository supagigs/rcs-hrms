<template>
	<div
		role="tablist"
		class="flex overflow-x-auto"
		:class="size === 'lg' ? 'gap-7' : 'gap-x-3.5 min-[1440px]:gap-x-[18px]'"
	>
		<button
			v-for="tab in tabs"
			:key="tab.key"
			role="tab"
			:aria-selected="tab.key === modelValue"
			class="-mb-px shrink-0 rounded-t-sm border-b-2 transition-colors focus:outline-none focus-visible:bg-surface-gray-2"
			:class="[
				size === 'lg' ? 'py-2.5 text-[13.5px]' : 'pb-3 text-sm',
				tab.key === modelValue
					? 'border-[--ink-blue-2] font-semibold text-ink-gray-9'
					: 'border-transparent font-medium text-ink-gray-5 hover:text-ink-gray-8',
			]"
			@click="emit('update:modelValue', tab.key)"
		>
			<!-- the invisible semibold copy reserves the active width, so switching tabs never
			     shifts the row, and the underline (the button's border) spans exactly the text -->
			<span class="grid justify-items-center">
				<span class="col-start-1 row-start-1">{{ tab.label }}</span>
				<span class="invisible col-start-1 row-start-1 font-semibold" aria-hidden="true">
					{{ tab.label }}
				</span>
			</span>
		</button>
	</div>
</template>

<script setup lang="ts">
// Mockup-style underline tabs (2px accent underline). frappe-ui 0.1.105 Tabs has a fixed 1px gray indicator.
// No horizontal padding: the underline is the button's bottom border, so it matches the label's width.
withDefaults(
	defineProps<{
		tabs: { key: string; label: string }[];
		modelValue: string;
		size?: "lg" | "md";
	}>(),
	{ size: "lg" },
);
const emit = defineEmits<{ "update:modelValue": [key: string] }>();
</script>
