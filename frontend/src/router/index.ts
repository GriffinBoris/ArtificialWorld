import { useAuthStore } from "@/stores/base";
import { createRouter, createWebHashHistory } from "vue-router";

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/worlds/",
      name: "worlds",
      component: () => import("@/views/Worlds/WorldsView.vue"),
      meta: { requiresAuth: true, immersive: true, title: "Little World" },
    },
    {
      path: "/",
      redirect: { name: "worlds" },
    },
    {
      path: "/home/",
      name: "home",
      component: () => import("@/views/Home/HomeView.vue"),
      meta: { requiresAuth: true, title: "Home" },
    },
    {
      path: "/login/",
      name: "login",
      component: () => import("@/views/Login/LoginView.vue"),
      meta: { guestOnly: true, title: "Sign In" },
    },
    {
      path: "/signup/",
      name: "signup",
      component: () => import("@/views/Signup/SignupView.vue"),
      meta: { guestOnly: true, title: "Create Account" },
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: { name: "worlds" },
    },
  ],
});

router.beforeEach((to) => {
  const authStore = useAuthStore();

  if (authStore.localWorldAccess) {
    if (to.meta.guestOnly || to.name === "home") return { name: "worlds" };

    if (to.name === "worlds") return true;
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: "login", query: { redirect: to.fullPath } };
  }

  if (to.meta.guestOnly && authStore.isAuthenticated) {
    const redirect = typeof to.query.redirect === "string" ? to.query.redirect : null;

    if (redirect && redirect.startsWith("/")) {
      return redirect;
    }

    return { name: "home" };
  }

  return true;
});

export default router;
