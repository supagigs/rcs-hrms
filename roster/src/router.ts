import { createRouter, createWebHistory } from "vue-router";

const routes = [
	{
		path: "/",
		component: () => import("./layouts/AppLayout.vue"),
		children: [
			{
				path: "",
				redirect: "/roster",
			},
			{
				path: "roster",
				name: "Roster",
				component: () => import("./views/Home.vue"),
				meta: { title: "Roster" },
			},
			{
				// name is the applicant's email address, links must encodeURIComponent it
				path: "recruitment/job-applicant/:name",
				name: "JobApplicant",
				component: () => import("./views/recruitment/JobApplicant.vue"),
				props: true,
				// "workspace": Recruitment sidebar instead of the NavBar, follows the user's Desk theme
				meta: { title: "Job Applicant", layout: "workspace" },
			},
		],
	},
];

const router = createRouter({
	// served for every /hr/* route (see website_route_rules in hooks.py)
	history: createWebHistory("/hr"),
	routes,
});

router.afterEach((to) => {
	document.title = (to.meta.title as string) || "Frappe HR";
});

export default router;
