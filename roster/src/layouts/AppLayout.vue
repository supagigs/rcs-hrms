<template>
	<template v-if="user.data">
		<!-- inside the Desk form: Desk provides the sidebar, breadcrumbs and user menu -->
		<div v-if="isEmbedded" class="h-screen overflow-hidden bg-surface-white text-ink-gray-9">
			<router-view />
		</div>
		<div
			v-else-if="isWorkspace"
			class="flex h-screen overflow-hidden bg-surface-white text-ink-gray-9"
		>
			<RecruitmentSidebar :user="user.data" />
			<main class="min-w-0 flex-1">
				<router-view />
			</main>
		</div>
		<div v-else class="min-h-screen">
			<NavBar :user="user.data" />
			<router-view />
		</div>
		<Toasts />
	</template>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, provide, ref, watchEffect } from "vue";
import { useRoute } from "vue-router";
import { Toasts, createResource } from "frappe-ui";

import NavBar from "../components/NavBar.vue";
import RecruitmentSidebar from "../components/recruitment/RecruitmentSidebar.vue";
import { followDeskTheme, isEmbedded, navigate } from "../utils/embed";

export type User = {
	[K in "name" | "first_name" | "full_name" | "user_image"]: string;
} & {
	roles: string[];
	desk_theme?: "Light" | "Dark" | "Automatic";
};

const route = useRoute();
const isWorkspace = computed(() => route.meta.layout === "workspace");

// RESOURCES

const user = createResource({
	url: "hrms.api.get_current_user_info",
	auto: true,
	onError() {
		// embedded: the Desk session expired too, so log in again for the Desk page
		const location = isEmbedded ? window.top!.location : window.location;
		navigate(`/login?redirect-to=${encodeURIComponent(location.pathname + location.search)}`);
	},
});

provide("user", user);

// Workspace pages use frappe-ui's semantic colours, so they can follow the Desk theme.
// Roster's month view uses fixed light colours and stays light.
// Embedded, the page mirrors the Desk window's current theme (live, if the user switches it).
const deskTheme = ref<string | null>(null);
const stopFollowingDesk = followDeskTheme((theme) => (deskTheme.value = theme));
onBeforeUnmount(stopFollowingDesk);

watchEffect(() => {
	const theme = user.data?.desk_theme;
	const dark = deskTheme.value
		? deskTheme.value === "dark"
		: isWorkspace.value &&
		  (theme === "Dark" ||
				(theme === "Automatic" &&
					window.matchMedia("(prefers-color-scheme: dark)").matches));
	document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
});
</script>
