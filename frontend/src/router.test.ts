import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory } from "vue-router";

import * as organizationsApi from "@/api/organizations";
import * as platformApi from "@/api/platform";
import { ApiError } from "@/api/client";
import { createAppRouter } from "@/router";
import { useAdminStemsStore } from "@/stores/adminStems";
import { usePlayerStore } from "@/stores/player";
import { useSongsStore } from "@/stores/songs";

vi.mock("@/api/organizations", () => ({
  getBrowserSession: vi.fn(),
}));

vi.mock("@/api/platform", () => ({
  getPlatformSession: vi.fn(),
}));

const userOrganization = { id: 1, name: "User", imageUrl: "/user.png", isAdmin: false };
const adminOrganization = { id: 2, name: "Admin", imageUrl: "/admin.png", isAdmin: true };

describe("router guards", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.resetAllMocks();
    vi.mocked(platformApi.getPlatformSession).mockRejectedValue(new ApiError("Unauthorized", 401));
  });

  it("redirects users without organization access to selection", async () => {
    vi.mocked(organizationsApi.getBrowserSession).mockResolvedValue({ authenticated: false, organizations: [] });
    const router = createAppRouter(createMemoryHistory(), createPinia());

    await router.push("/org/7/songs");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("organizations");
    expect(router.currentRoute.value.query).toEqual({
      organizationId: "7",
      redirect: "/org/7/songs",
    });
  });

  it("requires the organization admin role for admin routes", async () => {
    vi.mocked(organizationsApi.getBrowserSession).mockResolvedValue({
      authenticated: true,
      organizations: [userOrganization],
    });
    const router = createAppRouter(createMemoryHistory(), createPinia());

    await router.push("/org/1/admin/songs");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("admin-login");
    expect(router.currentRoute.value.query.redirect).toBe("/org/1/admin/songs");
  });

  it("allows organization admins without granting platform access", async () => {
    vi.mocked(organizationsApi.getBrowserSession).mockResolvedValue({
      authenticated: true,
      organizations: [adminOrganization],
    });
    const router = createAppRouter(createMemoryHistory(), createPinia());

    await router.push("/org/2/admin/songs");
    await router.isReady();
    expect(router.currentRoute.value.name).toBe("admin-songs");

    await router.push("/platform/organizations");
    expect(router.currentRoute.value.name).toBe("platform-login");
  });

  it("allows an authenticated platform session", async () => {
    vi.mocked(platformApi.getPlatformSession).mockResolvedValue({ authenticated: true });
    const router = createAppRouter(createMemoryHistory(), createPinia());

    await router.push("/platform/organizations");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("platform-organizations");
  });

  it("resets organization-bound stores when the route switches organization", async () => {
    localStorage.setItem("teamtracks-active-organization", "1");
    vi.mocked(organizationsApi.getBrowserSession).mockResolvedValue({
      authenticated: true,
      organizations: [userOrganization, adminOrganization],
    });
    const appPinia = createPinia();
    const playerReset = vi.spyOn(usePlayerStore(appPinia), "reset");
    const songsReset = vi.spyOn(useSongsStore(appPinia), "reset");
    const stemsReset = vi.spyOn(useAdminStemsStore(appPinia), "reset");
    const router = createAppRouter(createMemoryHistory(), appPinia);

    await router.push("/org/2/songs");
    await router.isReady();

    expect(playerReset).toHaveBeenCalledTimes(1);
    expect(songsReset).toHaveBeenCalledTimes(1);
    expect(stemsReset).toHaveBeenCalledTimes(1);
  });
});
