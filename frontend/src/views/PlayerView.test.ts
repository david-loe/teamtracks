import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import * as manifestApi from "@/api/manifest";
import type { SongManifest } from "@/types/manifest";
import PlayerView from "@/views/PlayerView.vue";

const engineMocks = vi.hoisted(() => ({
  ToneAudioEngine: vi.fn(() => ({
    initializeFromUserGesture: vi.fn().mockResolvedValue(undefined),
    loadManifest: vi.fn(() => new Promise(() => undefined)),
    play: vi.fn(),
    pause: vi.fn(),
    stop: vi.fn(),
    seek: vi.fn(),
    setStemMuted: vi.fn(),
    setStemGain: vi.fn(),
    setFocus: vi.fn(),
    getCurrentTime: vi.fn(() => 0),
    getDuration: vi.fn(() => 120),
    dispose: vi.fn(),
  })),
}));

vi.mock("@/api/manifest", () => ({
  getSongManifest: vi.fn(),
}));

vi.mock("@/audio/ToneAudioEngine", () => ({
  ToneAudioEngine: engineMocks.ToneAudioEngine,
}));

const manifest: SongManifest = {
  song: {
    id: 10,
    title: "Test Song",
    slug: "test-song",
    durationMs: 120000,
    sampleRate: 48000,
  },
  playable: true,
  stems: [
    {
      id: 1,
      name: "Drums",
      role: "drums",
      status: "ready",
      url: "/media/songs/10/stems/1.m4a",
      codec: "aac",
      container: "m4a",
      channels: 2,
      sampleRate: 48000,
      durationMs: 120000,
      fileSizeBytes: 2048,
      bitrateKbps: 160,
      errorMessage: null,
    },
  ],
};

describe("PlayerView", () => {
  it("keeps playback, mixer, and focus controls disabled before audio load completes", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);

    const wrapper = mount(PlayerView, {
      props: { id: "10" },
      global: {
        plugins: [createPinia()],
        stubs: {
          RouterLink: {
            template: "<a><slot /></a>",
          },
        },
      },
    });

    await flushPromises();

    expect(buttonByText(wrapper, "Audio aktivieren").attributes("disabled")).toBeUndefined();
    expect(buttonByText(wrapper, "Play").attributes("disabled")).toBeDefined();
    expect(buttonByText(wrapper, "Pause").attributes("disabled")).toBeDefined();
    expect(buttonByText(wrapper, "Stop").attributes("disabled")).toBeDefined();
    expect(wrapper.find(".seek-control input").attributes("disabled")).toBeDefined();
    expect(wrapper.find(".mixer-row input[type='checkbox']").attributes("disabled")).toBeDefined();
    expect(wrapper.find(".focus-controls select").attributes("disabled")).toBeDefined();

    await buttonByText(wrapper, "Audio aktivieren").trigger("click");
    await flushPromises();

    expect(buttonByText(wrapper, "Play").attributes("disabled")).toBeDefined();
    expect(buttonByText(wrapper, "Pause").attributes("disabled")).toBeDefined();
    expect(buttonByText(wrapper, "Stop").attributes("disabled")).toBeDefined();
  });
});

function buttonByText(wrapper: ReturnType<typeof mount>, text: string) {
  const button = wrapper.findAll("button").find((candidate) => candidate.text() === text);
  if (!button) {
    throw new Error(`Button not found: ${text}`);
  }
  return button;
}
