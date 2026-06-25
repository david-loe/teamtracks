import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import App from "@/App.vue";
import { useAdminStemsStore } from "@/stores/adminStems";
import { useOrganizationsStore } from "@/stores/organizations";
import { usePlayerStore } from "@/stores/player";
import { useSongsStore } from "@/stores/songs";

vi.mock("@/api/organizations", () => ({
  leaveAdminMode: vi.fn(),
  leaveOrganization: vi.fn(),
  logoutBrowser: vi.fn(),
  getBrowserSession: vi.fn(),
}));

describe("App organization switcher", () => {
  it("switches organization and resets all organization-bound stores", async () => {
    localStorage.clear();
    const appPinia = createPinia();
    const organizationsStore = useOrganizationsStore(appPinia);
    organizationsStore.$patch({
      initialized: true,
      activeOrganizationId: 1,
      sessionOrganizations: [
        { id: 1, name: "First", imageUrl: "/first.png", isAdmin: false },
        { id: 2, name: "Second", imageUrl: "/second.png", isAdmin: true },
      ],
    });
    const playerReset = vi.spyOn(usePlayerStore(appPinia), "reset");
    const songsReset = vi.spyOn(useSongsStore(appPinia), "reset");
    const stemsReset = vi.spyOn(useAdminStemsStore(appPinia), "reset");
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/org/:organizationId/songs", name: "songs", component: { template: "<div>songs</div>" } },
        { path: "/organizations", name: "organizations", component: { template: "<div>organizations</div>" } },
        { path: "/:pathMatch(.*)*", component: { template: "<div />" } },
      ],
    });
    await router.push("/org/1/songs");
    await router.isReady();
    const wrapper = mount(App, {
      global: { plugins: [appPinia, router] },
    });

    await wrapper.get(".organization-switcher").setValue("2");
    await flushPromises();

    expect(organizationsStore.activeOrganizationId).toBe(2);
    expect(router.currentRoute.value.fullPath).toBe("/org/2/songs");
    expect(playerReset).toHaveBeenCalledTimes(1);
    expect(songsReset).toHaveBeenCalledTimes(1);
    expect(stemsReset).toHaveBeenCalledTimes(1);
  });
});
