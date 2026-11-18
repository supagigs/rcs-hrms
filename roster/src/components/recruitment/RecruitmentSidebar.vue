<template>
	<aside
		class="relative flex shrink-0 flex-col border-r border-outline-gray-1 bg-surface-menu-bar transition-[width] duration-150"
		:class="collapsed ? 'w-16' : 'w-[252px]'"
	>
		<!-- workspace header -->
		<a
			href="/desk/recruitment"
			class="flex items-center gap-2.5 border-b border-outline-gray-1 py-3.5"
			:class="collapsed ? 'justify-center px-0' : 'px-4'"
		>
			<span
				class="flex size-[34px] shrink-0 items-center justify-center rounded-[9px] bg-[#16A085] text-white"
			>
				<FeatherIcon name="users" class="size-[17px]" />
			</span>
			<span v-if="!collapsed" class="min-w-0 flex-1">
				<span class="block text-[13.5px] font-bold text-ink-gray-9">Recruitment</span>
				<span class="block text-xs text-ink-gray-4">Frappe HR</span>
			</span>
		</a>

		<nav class="flex-1 overflow-y-auto overflow-x-hidden px-2.5 py-3">
			<template v-for="(group, i) in groups" :key="i">
				<div v-if="i > 0" class="h-2" />
				<template v-for="item in group" :key="item.label">
					<div v-if="item.children">
						<Tooltip :text="collapsed ? item.label : ''" placement="right">
							<button
								class="flex w-full items-center rounded-[7px] text-[13.5px] text-ink-gray-6 hover:bg-surface-gray-2"
								:class="
									collapsed ? 'justify-center p-2' : 'justify-between px-3 py-2'
								"
								@click="toggleGroup(item.label)"
							>
								<span class="flex items-center gap-2.5">
									<FeatherIcon
										:name="item.icon"
										class="size-[15px] shrink-0 text-ink-gray-4"
									/>
									<span v-if="!collapsed">{{ item.label }}</span>
								</span>
								<FeatherIcon
									v-if="!collapsed"
									name="chevron-right"
									class="size-3 text-ink-gray-4 transition-transform"
									:class="openGroups.includes(item.label) ? 'rotate-90' : ''"
								/>
							</button>
						</Tooltip>
						<div v-if="!collapsed && openGroups.includes(item.label)" class="mb-1">
							<a
								v-for="child in item.children"
								:key="child.label"
								:href="child.href"
								class="block rounded-[7px] py-1.5 pl-[37px] pr-3 text-[13px] text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-9"
							>
								{{ child.label }}
							</a>
						</div>
					</div>

					<Tooltip v-else :text="collapsed ? item.label : ''" placement="right">
						<a
							:href="item.href"
							class="flex items-center gap-2.5 whitespace-nowrap rounded-[7px] text-[13.5px]"
							:class="[
								collapsed ? 'justify-center p-2' : 'px-3 py-2',
								item.active
									? 'bg-surface-selected font-bold text-ink-gray-9 shadow-sm'
									: 'text-ink-gray-6 hover:bg-surface-gray-2 hover:text-ink-gray-9',
							]"
						>
							<FeatherIcon
								:name="item.icon"
								class="size-[15px] shrink-0"
								:class="item.active ? 'text-ink-gray-9' : 'text-ink-gray-4'"
							/>
							<span v-if="!collapsed">{{ item.label }}</span>
						</a>
					</Tooltip>
				</template>
			</template>
		</nav>

		<!-- current user -->
		<Dropdown :options="userOptions" placement="left">
			<button
				class="flex w-full items-center gap-2.5 border-t border-outline-gray-1 py-3.5 text-left hover:bg-surface-gray-2"
				:class="collapsed ? 'justify-center px-0' : 'px-4'"
			>
				<span
					class="flex size-8 shrink-0 items-center justify-center rounded-[8px] bg-surface-orange-1 text-[12.5px] font-bold text-ink-amber-3"
				>
					{{ initials }}
				</span>
				<span v-if="!collapsed" class="min-w-0">
					<span class="block truncate text-sm font-semibold text-ink-gray-9">
						{{ user.full_name }}
					</span>
					<span class="block truncate text-2xs text-ink-gray-4">{{ user.name }}</span>
				</span>
			</button>
		</Dropdown>

		<button
			class="absolute -right-[11px] bottom-[72px] z-10 flex size-[22px] items-center justify-center rounded-full border border-outline-gray-2 bg-surface-white text-ink-gray-5 shadow-sm hover:text-ink-gray-9"
			:title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
			@click="toggleCollapsed"
		>
			<FeatherIcon
				name="chevron-left"
				class="size-[11px]"
				:class="collapsed ? 'rotate-180' : ''"
			/>
		</button>
	</aside>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { Dropdown, FeatherIcon, Tooltip, createResource } from "frappe-ui";

import type { User } from "../../layouts/AppLayout.vue";
import { deskUrl } from "../../data/jobApplicant";
import { goTo } from "../../utils";

const props = defineProps<{ user: User }>();

type NavItem = {
	label: string;
	icon: string;
	href?: string;
	active?: boolean;
	children?: { label: string; href: string }[];
};

// mirrors hrms/workspace_sidebar/recruitment.json
const groups: NavItem[][] = [
	[
		{ label: "Home", icon: "home", href: "/desk/recruitment" },
		{ label: "Dashboard", icon: "grid", href: "/desk/dashboard-view/Recruitment" },
		{ label: "Hiring Pipeline", icon: "columns", href: "/desk/job-applicant/view/kanban" },
		{ label: "Job Opening", icon: "user-plus", href: deskUrl("Job Opening") },
		{ label: "Job Applicant", icon: "user", href: deskUrl("Job Applicant"), active: true },
		{ label: "Interview", icon: "video", href: deskUrl("Interview") },
		{ label: "Job Offer", icon: "user-check", href: deskUrl("Job Offer") },
		{ label: "Appointment Letter", icon: "file-text", href: deskUrl("Appointment Letter") },
	],
	[
		{
			label: "Planning",
			icon: "layout",
			children: ["Job Requisition", "Staffing Plan", "Employee Referral"].map((doctype) => ({
				label: doctype,
				href: deskUrl(doctype),
			})),
		},
		{
			label: "Reports",
			icon: "clipboard",
			children: [
				{
					label: "Recruitment Analytics",
					href: `/desk/query-report/${encodeURIComponent("Recruitment Analytics")}`,
				},
			],
		},
		{
			label: "Setup",
			icon: "database",
			children: [
				"Interview Type",
				"Job Opening Template",
				"Appointment Letter Template",
				"Job Offer Term Template",
			].map((doctype) => ({ label: doctype, href: deskUrl(doctype) })),
		},
	],
	[
		{ label: "Job Portal", icon: "globe", href: "/jobs" },
		{ label: "Settings", icon: "settings", href: deskUrl("HR Settings") },
	],
];

const storage = {
	get: (key: string) => {
		try {
			return window.localStorage.getItem(key);
		} catch {
			return null;
		}
	},
	set: (key: string, value: string) => {
		try {
			window.localStorage.setItem(key, value);
		} catch {
			// per-viewer convenience only
		}
	},
};

const COLLAPSED_KEY = "hrms:recruitment-sidebar:collapsed";
// on laptop widths the three content panes need the room, so start collapsed unless the user chose otherwise
const saved = storage.get(COLLAPSED_KEY);
const collapsed = ref(saved === null ? window.innerWidth < 1440 : saved === "1");

function toggleCollapsed() {
	collapsed.value = !collapsed.value;
	storage.set(COLLAPSED_KEY, collapsed.value ? "1" : "0");
}

const openGroups = ref<string[]>([]);
function toggleGroup(label: string) {
	if (collapsed.value) {
		collapsed.value = false;
		openGroups.value = [label];
		return;
	}
	openGroups.value = openGroups.value.includes(label)
		? openGroups.value.filter((open) => open !== label)
		: [...openGroups.value, label];
}

const initials = computed(() =>
	(props.user.full_name || props.user.name)
		.split(" ")
		.map((part) => part[0])
		.slice(0, 2)
		.join("")
		.toUpperCase(),
);

const logout = createResource({
	url: "logout",
	onSuccess: () => goTo("/login"),
});

const userOptions = [
	{ label: "My Account", onClick: () => goTo("/me") },
	{ label: "Switch to Desk", onClick: () => goTo("/desk") },
	{ label: "Log Out", onClick: () => logout.submit() },
];
</script>
