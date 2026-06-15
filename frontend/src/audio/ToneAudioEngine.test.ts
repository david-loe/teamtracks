import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SongManifest } from "@/types/manifest";
import { ToneAudioEngine } from "@/audio/ToneAudioEngine";

const toneMocks = vi.hoisted(() => ({
  players: [] as any[],
  gains: [] as any[],
  currentTime: 10,
  decodeAudioData: vi.fn(async (buffer: ArrayBuffer) => ({ buffer })),
  start: vi.fn().mockResolvedValue(undefined),
  now: vi.fn(() => toneMocks.currentTime),
  getContext: vi.fn(() => ({ decodeAudioData: toneMocks.decodeAudioData })),
  Player: vi.fn(function Player(audioBuffer) {
    const player = {
      audioBuffer,
      connect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
      dispose: vi.fn(),
    };
    toneMocks.players.push(player);
    return player;
  }),
  Gain: vi.fn(function Gain(initialGain) {
    const gain = {
      gain: { value: initialGain },
      toDestination: vi.fn(function toDestination() {
        return gain;
      }),
      dispose: vi.fn(),
    };
    toneMocks.gains.push(gain);
    return gain;
  }),
}));

vi.mock("tone", () => ({
  start: toneMocks.start,
  now: toneMocks.now,
  getContext: toneMocks.getContext,
  Player: toneMocks.Player,
  Gain: toneMocks.Gain,
}));

const manifest: SongManifest = {
  song: {
    id: 10,
    title: "Test Song",
    artist: "Test Artist",
    slug: "test-song",
    originalKey: 0,
    durationMs: 100000,
    sampleRate: 48000,
  },
  keyVariants: [{ id: 100, semitoneOffset: 0, isOriginal: true, status: "ready", playable: true, errorMessage: null }],
  selectedKeyId: 100,
  playable: true,
  stems: [
    {
      id: 1,
      name: "Click/Cue",
      role: "click_cue",
      key: null,
      focusable: false,
      status: "ready",
      url: "/media/songs/10/keys/100/stems/1.m4a",
      codec: "aac",
      container: "m4a",
      channels: 2,
      sampleRate: 48000,
      durationMs: 100000,
      fileSizeBytes: 100,
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
      durationMs: 100000,
      fileSizeBytes: 100,
      bitrateKbps: 96,
      errorMessage: null,
    },
  ],
};

describe("ToneAudioEngine", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    toneMocks.players.length = 0;
    toneMocks.gains.length = 0;
    toneMocks.currentTime = 10;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        headers: new Headers({ "content-length": "4" }),
        body: null,
        arrayBuffer: async () => new Uint8Array([1, 2, 3, 4]).buffer,
      })),
    );
  });

  it("initializes Tone from a user gesture", async () => {
    const engine = new ToneAudioEngine();
    await engine.initializeFromUserGesture();

    expect(toneMocks.start).toHaveBeenCalledTimes(1);
  });

  it("loads playable stems and reports progress", async () => {
    const engine = new ToneAudioEngine();
    const progress = vi.fn();

    await engine.loadManifest(manifest, progress);

    expect(fetch).toHaveBeenCalledTimes(2);
    expect(toneMocks.Player).toHaveBeenCalledTimes(2);
    expect(toneMocks.Gain).toHaveBeenCalledTimes(2);
    expect(toneMocks.players[0].connect).toHaveBeenCalledWith(toneMocks.gains[0]);
    expect(progress).toHaveBeenCalledWith({ stemId: 1, loadedBytes: 4, totalBytes: 4, ratio: 1 });
  });

  it("applies focus gain on top of per-stem gain", async () => {
    const engine = new ToneAudioEngine();
    await engine.loadManifest(manifest, vi.fn());

    engine.setStemGain(2, -3);
    engine.setFocus({ stemId: 1, focusedGainDb: 0, backgroundGainDb: -12 });

    expect(toneMocks.gains[0].gain.value).toBe(0);
    expect(toneMocks.gains[1].gain.value).toBe(-15);
  });

  it("keeps muted stems silent when focus changes", async () => {
    const engine = new ToneAudioEngine();
    await engine.loadManifest(manifest, vi.fn());

    engine.setStemMuted(2, true);
    engine.setFocus({ stemId: 1, focusedGainDb: 0, backgroundGainDb: -12 });
    engine.setFocus({ stemId: null, focusedGainDb: 0, backgroundGainDb: -12 });

    expect(toneMocks.gains[1].gain.value).toBe(-Infinity);
  });

  it("starts all players at the same scheduled time", async () => {
    const engine = new ToneAudioEngine();
    await engine.loadManifest(manifest, vi.fn());

    engine.play();

    expect(toneMocks.players[0].start).toHaveBeenCalledWith(10.05, 0, 100);
    expect(toneMocks.players[1].start).toHaveBeenCalledWith(10.05, 0, 100);
  });

  it("stops and disposes all audio nodes", async () => {
    const engine = new ToneAudioEngine();
    await engine.loadManifest(manifest, vi.fn());

    engine.dispose();

    expect(toneMocks.players[0].stop).toHaveBeenCalledWith(10);
    expect(toneMocks.players[1].stop).toHaveBeenCalledWith(10);
    expect(toneMocks.players[0].dispose).toHaveBeenCalledTimes(1);
    expect(toneMocks.players[1].dispose).toHaveBeenCalledTimes(1);
    expect(toneMocks.gains[0].dispose).toHaveBeenCalledTimes(1);
    expect(toneMocks.gains[1].dispose).toHaveBeenCalledTimes(1);
  });
});
