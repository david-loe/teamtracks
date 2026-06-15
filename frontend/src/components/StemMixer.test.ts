import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import StemMixer from "@/components/StemMixer.vue";
import type { PlayableStemManifestItem } from "@/types/manifest";

const stem: PlayableStemManifestItem = {
  id: 1,
  name: "Drums",
  role: "drums",
  key: 0,
  focusable: true,
  status: "ready",
  url: "/drums.m4a",
  codec: "aac",
  container: "m4a",
  channels: 2,
  sampleRate: 48000,
  durationMs: 120000,
  fileSizeBytes: 2048,
  bitrateKbps: 160,
  errorMessage: null,
};

describe("StemMixer", () => {
  it("renders compact stem details and toggles mute with a button", async () => {
    const wrapper = mount(StemMixer, {
      props: {
        stems: [stem],
        muted: { 1: false },
        gains: { 1: -3 },
        disabled: false,
        minGainDb: -24,
        maxGainDb: 6,
        stepGainDb: 1,
      },
    });

    expect(wrapper.text()).toContain("Drums");
    expect(wrapper.text()).toContain("drums");
    expect(wrapper.text()).not.toContain("2 ch");
    expect(wrapper.find("input[type='checkbox']").exists()).toBe(false);

    const muteButton = wrapper.find(".mute-button");
    expect(muteButton.attributes("aria-pressed")).toBe("false");
    await muteButton.trigger("click");
    expect(wrapper.emitted("setMuted")).toEqual([[1, true]]);
  });
});
