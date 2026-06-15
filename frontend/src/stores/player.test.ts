import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as manifestApi from "@/api/manifest";
import { usePlayerStore } from "@/stores/player";
import type { SongManifest } from "@/types/manifest";

const engineMocks = vi.hoisted(() => {
  const behavior = {
    loadPromise: null as Promise<void> | null,
    loadError: null as Error | null,
    startPromise: null as Promise<void> | null,
    startError: null as Error | null,
  };
  const instances: any[] = [];
  const ToneAudioEngine = vi.fn(function ToneAudioEngine() {
    const engine = {
      initializeFromUserGesture: vi.fn(async () => {
        await behavior.startPromise;
        if (behavior.startError) {
          throw behavior.startError;
        }
      }),
      loadManifest: vi.fn(async (_manifest, onProgress) => {
        await behavior.loadPromise;
        if (behavior.loadError) {
          throw behavior.loadError;
        }
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
    instances.push(engine);
    return engine;
  });
  return { behavior, instances, ToneAudioEngine };
});

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
    artist: "Test Artist",
    slug: "test-song",
    originalKey: 0,
    durationMs: 120000,
    sampleRate: 48000,
  },
  keyVariants: [{ id: 100, semitoneOffset: 0, isOriginal: true, status: "ready", errorMessage: null }],
  selectedKeyId: 100,
  playable: true,
  stems: [
    {
      id: 1,
      name: "Drums",
      role: "drums",
      key: null,
      focusable: true,
      status: "ready",
      url: "/media/songs/10/keys/100/stems/1.m4a",
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
      key: 0,
      focusable: true,
      status: "ready",
      url: "/media/songs/10/keys/100/stems/2.m4a",
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
    engineMocks.behavior.loadPromise = null;
    engineMocks.behavior.loadError = null;
    engineMocks.behavior.startPromise = null;
    engineMocks.behavior.startError = null;
  });

  it("loads playable stems automatically without starting the audio context", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);

    const store = usePlayerStore();
    await store.load(10);

    const engine = engineMocks.instances[0];
    expect(store.manifest).toEqual(manifest);
    expect(store.mutedStems).toEqual({ 1: false, 2: false });
    expect(store.stemGains).toEqual({ 1: 0, 2: 0 });
    expect(engine.loadManifest).toHaveBeenCalledWith(manifest, expect.any(Function));
    expect(engine.initializeFromUserGesture).not.toHaveBeenCalled();
    expect(engine.setStemMuted).toHaveBeenCalledWith(1, false);
    expect(engine.setStemGain).toHaveBeenCalledWith(2, 0);
    expect(store.loadProgressPercent).toBe(100);
    expect(store.controlsEnabled).toBe(true);
    store.reset();
  });

  it("applies player defaults delivered by the manifest", async () => {
    const configuredManifest: SongManifest = {
      ...manifest,
      playerSettings: {
        stemGainDefaultDb: -3,
        stemGainMinDb: -30,
        stemGainMaxDb: 3,
        stemGainStepDb: 2,
        focusGainDefaultDb: 1,
        focusGainMinDb: -10,
        focusGainMaxDb: 5,
        backgroundGainDefaultDb: -16,
        backgroundGainMinDb: -30,
        backgroundGainMaxDb: -1,
      },
    };
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(configuredManifest);

    const store = usePlayerStore();
    await store.load(10);

    expect(store.stemGains).toEqual({ 1: -3, 2: -3 });
    expect(store.focusedGainDb).toBe(1);
    expect(store.backgroundGainDb).toBe(-16);
    expect(engineMocks.instances[0].setStemGain).toHaveBeenCalledWith(2, -3);
    store.reset();
  });

  it("keeps playback disabled while stems are loading", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);
    const pendingLoad = deferred<void>();
    engineMocks.behavior.loadPromise = pendingLoad.promise;

    const store = usePlayerStore();
    const loadPromise = store.load(10);
    await vi.waitFor(() => expect(engineMocks.instances).toHaveLength(1));

    await store.play();

    expect(store.controlsEnabled).toBe(false);
    expect(engineMocks.instances[0].initializeFromUserGesture).not.toHaveBeenCalled();
    pendingLoad.resolve();
    await loadPromise;
    store.reset();
  });

  it("starts the audio context before playback and forwards player controls", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);

    const store = usePlayerStore();
    await store.load(10);
    const engine = engineMocks.instances[0];

    await store.play();
    store.seek(999);
    store.setStemMuted(2, true);
    store.setStemGain(2, -6);
    store.setFocusStem(1);
    store.setFocusGains(0, -18);

    expect(engine.initializeFromUserGesture).toHaveBeenCalledTimes(1);
    expect(engine.initializeFromUserGesture.mock.invocationCallOrder[0]).toBeLessThan(engine.play.mock.invocationCallOrder[0]);
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

  it("ignores repeated play clicks while the audio context is starting", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);
    const pendingStart = deferred<void>();
    engineMocks.behavior.startPromise = pendingStart.promise;

    const store = usePlayerStore();
    await store.load(10);
    const engine = engineMocks.instances[0];

    const firstPlay = store.play();
    const secondPlay = store.play();

    expect(engine.initializeFromUserGesture).toHaveBeenCalledTimes(1);
    expect(store.startingPlayback).toBe(true);
    pendingStart.resolve();
    await Promise.all([firstPlay, secondPlay]);
    expect(engine.play).toHaveBeenCalledTimes(1);
    store.reset();
  });

  it("reports audio context start errors without discarding loaded stems", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);
    engineMocks.behavior.startError = new Error("Audio context blocked");

    const store = usePlayerStore();
    await store.load(10);
    const engine = engineMocks.instances[0];

    await store.play();

    expect(engine.play).not.toHaveBeenCalled();
    expect(store.playbackError).toBe("Audio context blocked");
    expect(store.controlsEnabled).toBe(true);
    expect(store.playbackState).toBe("stopped");
    store.reset();
  });

  it("retries a failed stem load with a fresh engine", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);
    engineMocks.behavior.loadError = new Error("Network error");

    const store = usePlayerStore();
    await store.load(10);

    expect(store.loadError).toBe("Network error");
    expect(store.controlsEnabled).toBe(false);
    expect(engineMocks.instances[0].dispose).toHaveBeenCalledTimes(1);

    engineMocks.behavior.loadError = null;
    await store.retryAudioLoad();

    expect(engineMocks.instances).toHaveLength(2);
    expect(store.loadError).toBeNull();
    expect(store.controlsEnabled).toBe(true);
    store.reset();
  });

  it("ignores an audio load that finishes after the player was reset", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);
    const pendingLoad = deferred<void>();
    engineMocks.behavior.loadPromise = pendingLoad.promise;

    const store = usePlayerStore();
    const loadPromise = store.load(10);
    await vi.waitFor(() => expect(engineMocks.instances).toHaveLength(1));
    const engine = engineMocks.instances[0];

    store.reset();
    pendingLoad.resolve();
    await loadPromise;

    expect(engine.dispose).toHaveBeenCalledTimes(1);
    expect(store.manifest).toBeNull();
    expect(store.audioLoaded).toBe(false);
    expect(store.loadError).toBeNull();
  });

  it("disposes audio resources on reset", async () => {
    vi.mocked(manifestApi.getSongManifest).mockResolvedValue(manifest);

    const store = usePlayerStore();
    await store.load(10);
    const engine = engineMocks.instances[0];
    store.reset();

    expect(engine.dispose).toHaveBeenCalledTimes(1);
    expect(store.manifest).toBeNull();
    expect(store.controlsEnabled).toBe(false);
  });
});

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}
