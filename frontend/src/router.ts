import { createRouter, createWebHistory } from "vue-router";

import { getSession } from "./api/auth";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      redirect: "/songs",
    },
    {
      path: "/songs",
      name: "songs",
      component: () => import("./views/SongListView.vue"),
    },
    {
      path: "/settings",
      name: "user-settings",
      component: () => import("./views/UserSettingsView.vue"),
    },
    {
      path: "/admin/login",
      name: "admin-login",
      component: () => import("./views/AdminLoginView.vue"),
      meta: { adminLogin: true },
    },
    {
      path: "/admin/songs",
      name: "admin-songs",
      component: () => import("./views/AdminSongsView.vue"),
      meta: { admin: true },
    },
    {
      path: "/admin/settings",
      name: "admin-settings",
      component: () => import("./views/AdminSettingsView.vue"),
      meta: { admin: true },
    },
    {
      path: "/admin/songs/:id",
      name: "song-admin",
      component: () => import("./views/SongAdminView.vue"),
      props: true,
      meta: { admin: true },
    },
    {
      path: "/songs/:id",
      name: "song-player",
      component: () => import("./views/PlayerView.vue"),
      props: true,
    },
  ],
});

router.beforeEach(async (to) => {
  if (!to.meta.admin) return true;
  try {
    await getSession();
    return true;
  } catch {
    return { name: "admin-login", query: { redirect: to.fullPath } };
  }
});
