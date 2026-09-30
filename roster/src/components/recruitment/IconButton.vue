<template>
	<Tooltip :text="label">
		<component
			:is="href ? 'a' : 'button'"
			:href="href"
			:target="href ? (newTab ? '_blank' : linkTarget) : undefined"
			:rel="href && newTab ? 'noopener noreferrer' : undefined"
			:aria-label="label"
			:disabled="!href && disabled"
			class="flex size-[34px] shrink-0 items-center justify-center rounded-lg transition-colors disabled:cursor-not-allowed disabled:opacity-50"
			:class="
				theme === 'red'
					? 'bg-surface-red-2 text-ink-red-4 hover:bg-surface-red-3'
					: 'border border-outline-gray-2 bg-surface-white text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8'
			"
			@click="!href && !disabled && emit('click')"
		>
			<FeatherIcon :name="icon" class="size-4" />
		</component>
	</Tooltip>
</template>

<script setup lang="ts">
import { FeatherIcon, Tooltip } from "frappe-ui";

import { linkTarget } from "../../utils/embed";

defineProps<{
	icon: string;
	label: string;
	href?: string;
	newTab?: boolean;
	disabled?: boolean;
	theme?: "gray" | "red";
}>();
const emit = defineEmits<{ click: [] }>();
</script>
