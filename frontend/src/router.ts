import type { Pinia } from "pinia";
import { createRouter, createWebHistory, type RouterHistory } from "vue-router";

import { pinia } from "./pinia";
import { useOrganizationsStore } from "./stores/organizations";
import { useAdminStemsStore } from "./stores/adminStems";
import { usePlayerStore } from "./stores/player";
import { usePlatformStore } from "./stores/platform";
import { useSongsStore } from "./stores/songs";

export function createAppRouter(history: RouterHistory = createWebHistory(), appPinia: Pinia = pinia) {
  const router = createRouter({
    history,
    routes: [
    { path: "/", name: "home", component: () => import("./views/OrganizationSelectView.vue") },
    { path: "/organizations", name: "organizations", component: () => import("./views/OrganizationSelectView.vue") },
    { path: "/invite/:token", name: "invite", component: () => import("./views/InviteView.vue"), props: true },
    {
      path: "/platform/login",
      name: "platform-login",
      component: () => import("./views/PlatformLoginView.vue"),
      meta: { platformLogin: true },
    },
    {
      path: "/platform/organizations",
      name: "platform-organizations",
      component: () => import("./views/PlatformOrganizationsView.vue"),
      meta: { platform: true },
    },
    { path: "/songs", redirect: () => legacyRedirect("songs", appPinia) },
    { path: "/settings", redirect: () => legacyRedirect("user-settings", appPinia) },
    {
      path: "/org/:organizationId/songs",
      name: "songs",
      component: () => import("./views/SongListView.vue"),
      props: true,
      meta: { organization: true },
    },
    {
      path: "/org/:organizationId/settings",
      name: "user-settings",
      component: () => import("./views/UserSettingsView.vue"),
      props: true,
      meta: { organization: true },
    },
    {
      path: "/org/:organizationId/admin/login",
      name: "admin-login",
      component: () => import("./views/AdminLoginView.vue"),
      props: true,
      meta: { organization: true, adminLogin: true },
    },
    {
      path: "/org/:organizationId/admin/songs",
      name: "admin-songs",
      component: () => import("./views/AdminSongsView.vue"),
      props: true,
      meta: { organization: true, admin: true },
    },
    {
      path: "/org/:organizationId/admin/settings",
      name: "admin-settings",
      component: () => import("./views/AdminSettingsView.vue"),
      props: true,
      meta: { organization: true, admin: true },
    },
    {
      path: "/org/:organizationId/admin/organization",
      name: "admin-organization",
      component: () => import("./views/AdminOrganizationView.vue"),
      props: true,
      meta: { organization: true, admin: true },
    },
    {
      path: "/org/:organizationId/admin/songs/:id",
      name: "song-admin",
      component: () => import("./views/SongAdminView.vue"),
      props: true,
      meta: { organization: true, admin: true },
    },
    {
      path: "/org/:organizationId/songs/:id",
      name: "song-player",
      component: () => import("./views/PlayerView.vue"),
      props: true,
      meta: { organization: true },
    },
    ],
  });

  router.beforeEach(async (to) => {
    if (to.meta.platform || to.meta.platformLogin) {
      const platformStore = usePlatformStore(appPinia);
      await platformStore.initialize();
      if (to.meta.platform && !platformStore.authenticated) {
        return { name: "platform-login", query: { redirect: to.fullPath } };
      }
      if (to.meta.platformLogin && platformStore.authenticated) {
        return { name: "platform-organizations" };
      }
      return true;
    }

    const store = useOrganizationsStore(appPinia);
    await store.initialize();

    if (!to.meta.organization) {
      if (to.name === "home" && store.activeOrganizationId !== null) {
        return { name: "songs", params: { organizationId: store.activeOrganizationId } };
      }
      return true;
    }

    const organizationId = parseOrganizationId(to.params.organizationId);
    if (organizationId === null || !store.hasAccess(organizationId)) {
      return { name: "organizations", query: { organizationId: to.params.organizationId, redirect: to.fullPath } };
    }
    if (store.activeOrganizationId !== organizationId) {
      usePlayerStore(appPinia).reset();
      useSongsStore(appPinia).reset();
      useAdminStemsStore(appPinia).reset();
      store.setActiveOrganization(organizationId);
    }

    if (to.meta.admin && !store.hasAdminAccess(organizationId)) {
      return {
        name: "admin-login",
        params: { organizationId },
        query: { redirect: to.fullPath },
      };
    }
    return true;
  });

  return router;
}

export const router = createAppRouter();

function legacyRedirect(name: "songs" | "user-settings", appPinia: Pinia) {
  const store = useOrganizationsStore(appPinia);
  return store.activeOrganizationId === null
    ? { name: "organizations" }
    : { name, params: { organizationId: store.activeOrganizationId } };
}

function parseOrganizationId(value: unknown): number | null {
  if (typeof value !== "string" || !/^[1-9]\d*$/.test(value)) return null;
  return Number(value);
}
