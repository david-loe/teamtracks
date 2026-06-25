import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import * as platformApi from "@/api/platform";
import { usePlatformStore } from "@/stores/platform";

vi.mock("@/api/platform", () => ({
  getPlatformSession: vi.fn(),
  loginPlatform: vi.fn(),
  logoutPlatform: vi.fn(),
}));

describe("usePlatformStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
  });

  it("treats an unauthorized session as logged out", async () => {
    vi.mocked(platformApi.getPlatformSession).mockRejectedValue(new ApiError("Unauthorized", 401));
    const store = usePlatformStore();

    await store.initialize();

    expect(store.initialized).toBe(true);
    expect(store.authenticated).toBe(false);
  });

  it("logs in and logs out independently from organization sessions", async () => {
    vi.mocked(platformApi.loginPlatform).mockResolvedValue({ authenticated: true });
    vi.mocked(platformApi.logoutPlatform).mockResolvedValue();
    const store = usePlatformStore();

    await store.login("platform-password");
    expect(store.authenticated).toBe(true);

    await store.logout();
    expect(store.authenticated).toBe(false);
  });
});
