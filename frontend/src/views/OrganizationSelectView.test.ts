import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { ApiError } from "@/api/client";
import * as organizationsApi from "@/api/organizations";
import OrganizationSelectView from "@/views/OrganizationSelectView.vue";

vi.mock("@/api/organizations", () => ({
  listOrganizations: vi.fn(),
  loginToOrganization: vi.fn(),
}));

const organization = { id: 7, name: "Test Band", imageUrl: "/band.png" };

describe("OrganizationSelectView", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(organizationsApi.listOrganizations).mockResolvedValue([organization]);
  });

  it("lists organizations and logs in with the user password", async () => {
    vi.mocked(organizationsApi.loginToOrganization).mockResolvedValue({
      authenticated: true,
      organizations: [{ ...organization, isAdmin: false }],
    });
    const { wrapper, router } = await mountView();

    await wrapper.get(".organization-card").trigger("click");
    await wrapper.get('input[type="password"]').setValue("user-password");
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(organizationsApi.loginToOrganization).toHaveBeenCalledWith(7, "user-password");
    expect(router.currentRoute.value.fullPath).toBe("/org/7/songs");
  });

  it("shows a specific error for a wrong user password", async () => {
    vi.mocked(organizationsApi.loginToOrganization).mockRejectedValue(new ApiError("Unauthorized", 401));
    const { wrapper } = await mountView();

    await wrapper.get(".organization-card").trigger("click");
    await wrapper.get('input[type="password"]').setValue("wrong");
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(wrapper.text()).toContain("Das User-Passwort ist falsch.");
  });
});

async function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/organizations", component: OrganizationSelectView },
      { path: "/org/:organizationId/songs", name: "songs", component: { template: "<div />" } },
      { path: "/platform/login", component: { template: "<div />" } },
    ],
  });
  await router.push("/organizations");
  await router.isReady();
  const wrapper = mount(OrganizationSelectView, {
    global: { plugins: [createPinia(), router] },
  });
  await flushPromises();
  return { wrapper, router };
}
