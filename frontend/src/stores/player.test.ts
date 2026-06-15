import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as manifestApi from "@/api/manifest";
import type { SongManifest } from "@/types/manifest";
import { usePlayerStore } from "@/stores/player";

const engineMocks = vi.hoisted(() => ({
  instances: [] as any[],
  ToneAudioEngine: vi.fn(() => {
    const engine = {
      initializeFromUserGesture: vi.fn().mockResolvedValue(undefined),
      loadManifest: vi.fn(async (_manifest, onProgress) => {
        onProgress({ stemId: 1, loadedBytes: 100, totalBytes: 100, ratio: 1 });
        onProgress({ stemId: 2, loadedBytes: 100, totalBytes: 100, ratio: 1 });
      }),
      play: vi.fn(),
      pause: vi.fn(),
      stop: vi.fn(),
      seek: vi.fn(),
      setStemMuted: vi.fn(),
      setStemGain: vi.fn(),
      setFocus: vi.fn(),
      getCurrentTime: vi.fn(() => 12),
      getDuration: vi.fn(() => 120),
      dispose: vi.fn(),
    };
    engineMocks.instances.push(engine);
    return engine;
  }),
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
    {
      id: 2,
      name: "Bass",
      role: "bass",
      status: "ready",
      url: "/media/songs/10/stems/2.m4a",
      codec: "aac",
      container: "m4a",
      channels: 1,
      sampleRate: 48000,
      durationMs: 120000,
      fileSizeBytes: 1024,
      bitrateKbps: 96,
      errorMessage: null,
    },
  ],
};

describe("usePlayerStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useRealTimers();
    vi.clearAllMocks();
    engineMocks.instances.length = 0;
  });

  it("loads a manifest and initializes playable stem controls", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);

    const store = usePlayerStore();
    await store.load(10);

    expect(store.manifest).toEqual(manifest);
    expect(store.playableStems).toHaveLength(2);
    expect(store.mutedStems).toEqual({ 1: false, 2: false });
    expect(store.stemGains).toEqual({ 1: 0, 2: 0 });
    expect(store.controlsEnabled).toBe(false);
  });

  it("activates audio, loads stems with progress, and enables controls", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);

    const store = usePlayerStore();
    await store.load(10);
    await store.activateAndLoadAudio();

    const engine = engineMocks.instances[0];
    expect(engine.initializeFromUserGesture).toHaveBeenCalledTimes(1);
    expect(engine.loadManifest).toHaveBeenCalledWith(manifest, expect.any(Function));
    expect(engine.setStemMuted).toHaveBeenCalledWith(1, false);
    expect(engine.setStemGain).toHaveBeenCalledWith(2, 0);
    expect(engine.setFocus).toHaveBeenLastCalledWith({
      stemId: null,
      focusedGainDb: 0,
      backgroundGainDb: -12,
    });
    expect(store.loadProgressPercent).toBe(100);
    expect(store.controlsEnabled).toBe(true);
    store.reset();
  });

  it("gates playback before audio has loaded", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);

    const store = usePlayerStore();
    await store.load(10);
    store.play();

    expect(engineMocks.instances).toEqual([]);
    expect(store.playbackState).toBe("stopped");
  });

  it("forwards playback, seek, focus, and mute commands to the engine", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);

    const store = usePlayerStore();
    await store.load(10);
    await store.activateAndLoadAudio();
    const engine = engineMocks.instances[0];

    store.play();
    store.seek(999);
    store.setStemMuted(2, true);
    store.setStemGain(2, -6);
    store.setFocusStem(1);
    store.setFocusGains(0, -18);

    expect(engine.play).toHaveBeenCalledTimes(1);
    expect(engine.seek).toHaveBeenCalledWith(120);
    expect(engine.setStemMuted).toHaveBeenLastCalledWith(2, true);
    expect(engine.setStemGain).toHaveBeenLastCalledWith(2, -6);
    expect(engine.setFocus).toHaveBeenLastCalledWith({
      stemId: 1,
      focusedGainDb: 0,
      backgroundGainDb: -18,
    });
    store.reset();
  });

  it("disposes audio resources on reset", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);

    const store = usePlayerStore();
    await store.load(10);
    await store.activateAndLoadAudio();
    const engine = engineMocks.instances[0];
    store.reset();

    expect(engine.dispose).toHaveBeenCalledTimes(1);
    expect(store.manifest).toBeNull();
    expect(store.controlsEnabled).toBe(false);
  });
});
