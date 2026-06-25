import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as organizationAdminApi from "@/api/organizationAdmin";
import * as organizationsApi from "@/api/organizations";
import AdminOrganizationView from "@/views/AdminOrganizationView.vue";

const { replace } = vi.hoisted(() => ({ replace: vi.fn() }));

vi.mock("vue-router", () => ({
  useRouter: () => ({ replace }),
}));

vi.mock("@/api/organizationAdmin", () => ({
  getAdminOrganization: vi.fn(),
  updateAdminOrganization: vi.fn(),
  updateOrganizationUserPassword: vi.fn(),
  updateOrganizationAdminPassword: vi.fn(),
  regenerateOrganizationInvite: vi.fn(),
  deleteAdminOrganization: vi.fn(),
}));

vi.mock("@/api/organizations", () => ({
  getBrowserSession: vi.fn(),
  listOrganizations: vi.fn(),
}));

const organization = {
  id: 7,
  name: "Band",
  imageUrl: "/api/organizations/7/image",
  inviteToken: "old-token",
  inviteUrl: "https://teamtracks.test/invite/old-token",
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
};

describe("AdminOrganizationView", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(organizationAdminApi.getAdminOrganization).mockResolvedValue(organization);
    vi.mocked(organizationsApi.getBrowserSession).mockResolvedValue({
      authenticated: false,
      organizations: [],
    });
    vi.mocked(organizationsApi.listOrganizations).mockResolvedValue([]);
  });

  it("regenerates an invite only after explicit confirmation", async () => {
    const regenerated = {
      ...organization,
      inviteToken: "new-token",
      inviteUrl: "https://teamtracks.test/invite/new-token",
      updatedAt: "2026-01-02T00:00:00Z",
    };
    vi.mocked(organizationAdminApi.regenerateOrganizationInvite).mockResolvedValue(regenerated);
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    const wrapper = mount(AdminOrganizationView, {
      props: { organizationId: "7" },
      global: { plugins: [createPinia()] },
    });
    await flushPromises();

    const regenerateButton = wrapper.findAll("button").find((button) => button.text().includes("regenerieren"));
    await regenerateButton!.trigger("click");
    expect(organizationAdminApi.regenerateOrganizationInvite).not.toHaveBeenCalled();

    await regenerateButton!.trigger("click");
    await flushPromises();
    expect(organizationAdminApi.regenerateOrganizationInvite).toHaveBeenCalledWith(7);
    expect(wrapper.get('input[aria-label="Invite-Link"]').element.getAttribute("value")).toContain("new-token");
    confirm.mockRestore();
  });

  it("deletes with the admin password and navigates to organization selection", async () => {
    vi.mocked(organizationAdminApi.deleteAdminOrganization).mockResolvedValue();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const wrapper = mount(AdminOrganizationView, {
      props: { organizationId: "7" },
      global: { plugins: [createPinia()] },
    });
    await flushPromises();

    const passwordInputs = wrapper.findAll('input[type="password"]');
    await passwordInputs.at(-1)!.setValue("admin-password");
    const deleteButton = wrapper.findAll("button").find((button) => button.text().includes("endgültig löschen"));
    await deleteButton!.trigger("submit");
    await flushPromises();

    expect(organizationAdminApi.deleteAdminOrganization).toHaveBeenCalledWith(7, "admin-password");
    expect(replace).toHaveBeenCalledWith({ name: "organizations" });
  });
});
