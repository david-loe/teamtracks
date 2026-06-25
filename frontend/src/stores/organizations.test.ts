import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as organizationsApi from "@/api/organizations";
import { useOrganizationsStore } from "@/stores/organizations";

vi.mock("@/api/organizations", () => ({
  listOrganizations: vi.fn(),
  getBrowserSession: vi.fn(),
  loginToOrganization: vi.fn(),
  loginAsOrganizationAdmin: vi.fn(),
  leaveAdminMode: vi.fn(),
  leaveOrganization: vi.fn(),
  logoutBrowser: vi.fn(),
  acceptInvite: vi.fn(),
}));

const first = { id: 1, name: "First", imageUrl: "/first.png", isAdmin: false };
const second = { id: 2, name: "Second", imageUrl: "/second.png", isAdmin: true };

describe("useOrganizationsStore", () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
    vi.resetAllMocks();
    vi.mocked(organizationsApi.getBrowserSession).mockResolvedValue({
      authenticated: true,
      organizations: [first, second],
    });
  });

  it("restores the active organization and exposes roles", async () => {
    localStorage.setItem("teamtracks-active-organization", "2");
    setActivePinia(createPinia());
    const store = useOrganizationsStore();
    await store.initialize();

    expect(store.activeOrganizationId).toBe(2);
    expect(store.hasAccess(1)).toBe(true);
    expect(store.hasAdminAccess(2)).toBe(true);
    expect(store.hasAdminAccess(1)).toBe(false);
  });

  it("stores a newly logged-in organization as active", async () => {
    vi.mocked(organizationsApi.loginToOrganization).mockResolvedValue({
      authenticated: true,
      organizations: [first],
    });
    const store = useOrganizationsStore();
    await store.login(1, "password");

    expect(organizationsApi.loginToOrganization).toHaveBeenCalledWith(1, "password");
    expect(store.activeOrganizationId).toBe(1);
    expect(localStorage.getItem("teamtracks-active-organization")).toBe("1");
  });

  it("accepts invitations and selects the returned organization", async () => {
    vi.mocked(organizationsApi.acceptInvite).mockResolvedValue({
      organizationId: 2,
      session: { authenticated: true, organizations: [second] },
    });
    const store = useOrganizationsStore();
    const organizationId = await store.acceptInvitation("invite-token");

    expect(organizationId).toBe(2);
    expect(store.activeOrganizationId).toBe(2);
  });

  it("grants and revokes the admin role through refreshed session data", async () => {
    vi.mocked(organizationsApi.loginAsOrganizationAdmin).mockResolvedValue({
      authenticated: true,
      organizations: [{ ...first, isAdmin: true }],
    });
    const store = useOrganizationsStore();

    await store.loginAdmin(1, "admin-password");
    expect(store.hasAdminAccess(1)).toBe(true);

    vi.mocked(organizationsApi.getBrowserSession).mockResolvedValue({
      authenticated: true,
      organizations: [first],
    });
    vi.mocked(organizationsApi.leaveAdminMode).mockResolvedValue();
    await store.exitAdmin(1);

    expect(organizationsApi.leaveAdminMode).toHaveBeenCalledWith(1);
    expect(store.hasAdminAccess(1)).toBe(false);
  });

  it("falls back to the next organization when refreshed access is revoked", async () => {
    localStorage.setItem("teamtracks-active-organization", "2");
    setActivePinia(createPinia());
    const store = useOrganizationsStore();
    await store.initialize();

    vi.mocked(organizationsApi.getBrowserSession).mockResolvedValue({
      authenticated: true,
      organizations: [first],
    });
    await store.refreshSession();

    expect(store.activeOrganizationId).toBe(1);
    expect(localStorage.getItem("teamtracks-active-organization")).toBe("1");
  });
});
