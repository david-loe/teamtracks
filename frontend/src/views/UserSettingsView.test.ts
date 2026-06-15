import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import UserSettingsView from "@/views/UserSettingsView.vue";

const storageMocks = vi.hoisted(() => ({
  get: vi.fn(),
  save: vi.fn(),
}));

vi.mock("@/storage/userPlayerSettings", () => ({
  DEFAULT_USER_PLAYER_SETTINGS: { focusedGainDb: 0, backgroundGainDb: -12 },
  getUserPlayerSettings: storageMocks.get,
  saveUserPlayerSettings: storageMocks.save,
}));

describe("UserSettingsView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    storageMocks.get.mockResolvedValue({ focusedGainDb: 2, backgroundGainDb: -18 });
    storageMocks.save.mockResolvedValue(undefined);
  });

  it("loads values and saves slider changes automatically", async () => {
    const wrapper = mount(UserSettingsView);
    await flushPromises();

    expect(wrapper.find<HTMLInputElement>("#user-focus-gain").element.value).toBe("2");
    expect(wrapper.find<HTMLInputElement>("#user-background-gain").element.value).toBe("-18");

    await wrapper.find("#user-focus-gain").setValue("-4");
    await flushPromises();

    expect(storageMocks.save).toHaveBeenCalledWith({ focusedGainDb: -4, backgroundGainDb: -18 });
    expect(wrapper.text()).toContain("Gespeichert.");
  });

  it("shows storage errors without removing the controls", async () => {
    storageMocks.save.mockRejectedValue(new Error("Speichern fehlgeschlagen"));
    const wrapper = mount(UserSettingsView);
    await flushPromises();

    await wrapper.find("#user-background-gain").setValue("-20");
    await flushPromises();

    expect(wrapper.text()).toContain("Speichern fehlgeschlagen");
    expect(wrapper.find("#user-focus-gain").exists()).toBe(true);
  });
});
