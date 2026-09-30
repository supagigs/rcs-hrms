<template>
	<Dialog v-model="open" :options="{ title, size: 'md' }">
		<template #body-content>
			<p class="text-sm leading-relaxed text-ink-gray-7">{{ message }}</p>
			<p v-if="note" class="mt-2 text-xs leading-relaxed text-ink-gray-5">{{ note }}</p>
		</template>
		<template #actions="{ close }">
			<div class="flex justify-end gap-2">
				<Button variant="subtle" label="Cancel" :disabled="loading" @click="close()" />
				<Button
					variant="solid"
					:theme="theme"
					:label="confirmLabel"
					:loading="loading"
					@click="emit('confirm')"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
// Confirmation before actions that stop or replace something: Cancel plus a confirm button
// that names the action. The parent closes it once the action has finished.
import { Button, Dialog } from "frappe-ui";

withDefaults(
	defineProps<{
		title: string;
		message: string;
		note?: string;
		confirmLabel: string;
		theme?: "gray" | "blue" | "red";
		loading?: boolean;
	}>(),
	{ theme: "red", note: "", loading: false },
);
const emit = defineEmits<{ confirm: [] }>();
const open = defineModel<boolean>({ default: false });
</script>
