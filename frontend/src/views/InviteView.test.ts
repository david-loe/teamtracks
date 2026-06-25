import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import * as organizationsApi from "@/api/organizations";
import InviteView from "@/views/InviteView.vue";

vi.mock("@/api/organizations", () => ({
  acceptInvite: vi.fn(),
}));

describe("InviteView", () => {
  beforeEach(() => vi.resetAllMocks());

  it("accepts a valid invite and opens the organization", async () => {
    vi.mocked(organizationsApi.acceptInvite).mockResolvedValue({
      organizationId: 7,
      session: {
        authenticated: true,
        organizations: [{ id: 7, name: "Band", imageUrl: "/band.png", isAdmin: false }],
      },
    });
    const { router } = await mountView();

    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe("/org/7/songs"));
    expect(organizationsApi.acceptInvite).toHaveBeenCalledWith("valid-token");
  });

  it("keeps the invite page and explains invalid tokens", async () => {
    vi.mocked(organizationsApi.acceptInvite).mockRejectedValue(new Error("Invite not found"));
    const { wrapper, router } = await mountView();
    await flushPromises();

    expect(router.currentRoute.value.fullPath).toBe("/invite/valid-token");
    expect(wrapper.text()).toContain("Einladung ungültig");
    expect(wrapper.text()).toContain("Invite not found");
  });
});

async function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/invite/:token", component: InviteView, props: true },
      { path: "/org/:organizationId/songs", name: "songs", component: { template: "<div />" } },
    ],
  });
  await router.push("/invite/valid-token");
  await router.isReady();
  const wrapper = mount(InviteView, {
    props: { token: "valid-token" },
    global: { plugins: [createPinia(), router] },
  });
  await flushPromises();
  return { wrapper, router };
}
