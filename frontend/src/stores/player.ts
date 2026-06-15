import { defineStore } from "pinia";
import { computed, ref, shallowRef } from "vue";

import * as manifestApi from "@/api/manifest";
import type { AudioEngine, StemLoadProgress } from "@/audio/AudioEngine";
import { ToneAudioEngine } from "@/audio/ToneAudioEngine";
import type { SongManifest } from "@/types/manifest";
import { isPlayableStem } from "@/types/manifest";

type PlaybackState = "stopped" | "paused" | "playing";

const CURRENT_TIME_INTERVAL_MS = 200;
const DEFAULT_FOCUSED_GAIN_DB = 0;
const DEFAULT_BACKGROUND_GAIN_DB = -12;

export const usePlayerStore = defineStore("player", () => {
  const manifest = ref<SongManifest | null>(null);
  const loadingManifest = ref(false);
  const activatingAudio = ref(false);
  const loadingAudio = ref(false);
  const audioEnabled = ref(false);
  const audioLoaded = ref(false);
  const playbackState = ref<PlaybackState>("stopped");
  const currentTimeSeconds = ref(0);
  const loadProgress = ref<Record<number, StemLoadProgress>>({});
  const error = ref<string | null>(null);
  const loadError = ref<string | null>(null);
  const mutedStems = ref<Record<number, boolean>>({});
  const stemGains = ref<Record<number, number>>({});
  const focusedStemId = ref<number | null>(null);
  const focusedGainDb = ref(DEFAULT_FOCUSED_GAIN_DB);
  const backgroundGainDb = ref(DEFAULT_BACKGROUND_GAIN_DB);
  const engine = shallowRef<AudioEngine | null>(null);
  let currentTimeTimer: number | null = null;

  const playableStems = computed(() => manifest.value?.stems.filter(isPlayableStem) ?? []);
  const durationSeconds = computed(() => Math.max(0, (manifest.value?.song.durationMs ?? 0) / 1000));
  const durationMs = computed(() => manifest.value?.song.durationMs ?? null);
  const controlsEnabled = computed(() => audioEnabled.value && audioLoaded.value && !loadingAudio.value);
  const loadProgressPercent = computed(() => {
    if (playableStems.value.length === 0) {
      return 0;
    }
    const totalRatio = playableStems.value.reduce((sum, stem) => {
      return sum + (loadProgress.value[stem.id]?.ratio ?? 0);
    }, 0);
    return Math.round((totalRatio / playableStems.value.length) * 100);
  });

  async function load(songId: number): Promise<void> {
    resetAudio();
    loadingManifest.value = true;
    error.value = null;
    loadError.value = null;
    try {
      manifest.value = await manifestApi.getSongManifest(songId);
      initializeStemControls();
    } catch (err) {
      manifest.value = null;
      error.value = getErrorMessage(err);
    } finally {
      loadingManifest.value = false;
    }
  }

  async function activateAndLoadAudio(): Promise<void> {
    if (!manifest.value || !manifest.value.playable || loadingAudio.value) {
      return;
    }

    activatingAudio.value = true;
    loadingAudio.value = true;
    loadError.value = null;
    loadProgress.value = {};

    try {
      const nextEngine = new ToneAudioEngine();
      engine.value?.dispose();
      engine.value = nextEngine;
      await nextEngine.initializeFromUserGesture();
      audioEnabled.value = true;
      await nextEngine.loadManifest(manifest.value, updateLoadProgress);
      applyAllEngineControls();
      audioLoaded.value = true;
      startCurrentTimeTimer();
    } catch (err) {
      audioLoaded.value = false;
      audioEnabled.value = false;
      engine.value?.dispose();
      engine.value = null;
      loadError.value = getErrorMessage(err);
    } finally {
      activatingAudio.value = false;
      loadingAudio.value = false;
    }
  }

  function play(): void {
    if (!controlsEnabled.value) {
      return;
    }
    engine.value?.play();
    playbackState.value = "playing";
    startCurrentTimeTimer();
  }

  function pause(): void {
    engine.value?.pause();
    playbackState.value = "paused";
    syncCurrentTime();
  }

  function stop(): void {
    engine.value?.stop();
    playbackState.value = "stopped";
    currentTimeSeconds.value = 0;
  }

  function seek(positionSeconds: number): void {
    const nextPosition = clampPosition(positionSeconds);
    engine.value?.seek(nextPosition);
    currentTimeSeconds.value = nextPosition;
  }

  function setStemMuted(stemId: number, muted: boolean): void {
    mutedStems.value = {
      ...mutedStems.value,
      [stemId]: muted,
    };
    engine.value?.setStemMuted(stemId, muted);
  }

  function setStemGain(stemId: number, gainDb: number): void {
    stemGains.value = {
      ...stemGains.value,
      [stemId]: gainDb,
    };
    engine.value?.setStemGain(stemId, gainDb);
  }

  function setFocusStem(stemId: number | null): void {
    focusedStemId.value = stemId;
    applyFocus();
  }

  function setFocusGains(nextFocusedGainDb: number, nextBackgroundGainDb: number): void {
    focusedGainDb.value = nextFocusedGainDb;
    backgroundGainDb.value = nextBackgroundGainDb;
    applyFocus();
  }

  function reset(): void {
    stopCurrentTimeTimer();
    resetAudio();
    manifest.value = null;
    loadingManifest.value = false;
    error.value = null;
    loadError.value = null;
  }

  function resetAudio(): void {
    engine.value?.dispose();
    engine.value = null;
    audioEnabled.value = false;
    audioLoaded.value = false;
    activatingAudio.value = false;
    loadingAudio.value = false;
    playbackState.value = "stopped";
    currentTimeSeconds.value = 0;
    loadProgress.value = {};
    mutedStems.value = {};
    stemGains.value = {};
    focusedStemId.value = null;
    focusedGainDb.value = DEFAULT_FOCUSED_GAIN_DB;
    backgroundGainDb.value = DEFAULT_BACKGROUND_GAIN_DB;
  }

  function updateLoadProgress(progress: StemLoadProgress): void {
    loadProgress.value = {
      ...loadProgress.value,
      [progress.stemId]: progress,
    };
  }

  function initializeStemControls(): void {
    const nextMuted: Record<number, boolean> = {};
    const nextGains: Record<number, number> = {};
    for (const stem of playableStems.value) {
      nextMuted[stem.id] = false;
      nextGains[stem.id] = 0;
    }
    mutedStems.value = nextMuted;
    stemGains.value = nextGains;
  }

  function applyAllEngineControls(): void {
    for (const stem of playableStems.value) {
      engine.value?.setStemMuted(stem.id, mutedStems.value[stem.id] ?? false);
      engine.value?.setStemGain(stem.id, stemGains.value[stem.id] ?? 0);
    }
    applyFocus();
  }

  function applyFocus(): void {
    engine.value?.setFocus({
      stemId: focusedStemId.value,
      focusedGainDb: focusedGainDb.value,
      backgroundGainDb: backgroundGainDb.value,
    });
  }

  function startCurrentTimeTimer(): void {
    if (currentTimeTimer !== null) {
      return;
    }
    currentTimeTimer = window.setInterval(syncCurrentTime, CURRENT_TIME_INTERVAL_MS);
  }

  function stopCurrentTimeTimer(): void {
    if (currentTimeTimer !== null) {
      window.clearInterval(currentTimeTimer);
      currentTimeTimer = null;
    }
  }

  function syncCurrentTime(): void {
    if (!engine.value) {
      return;
    }
    currentTimeSeconds.value = engine.value.getCurrentTime();
    if (playbackState.value === "playing" && durationSeconds.value > 0 && currentTimeSeconds.value >= durationSeconds.value) {
      playbackState.value = "stopped";
      engine.value.stop();
      currentTimeSeconds.value = 0;
    }
  }

  function clampPosition(positionSeconds: number): number {
    const safePosition = Number.isFinite(positionSeconds) ? positionSeconds : 0;
    if (durationSeconds.value <= 0) {
      return Math.max(0, safePosition);
    }
    return Math.min(Math.max(0, safePosition), durationSeconds.value);
  }

  return {
    manifest,
    loadingManifest,
    activatingAudio,
    loadingAudio,
    audioEnabled,
    audioLoaded,
    playbackState,
    currentTimeSeconds,
    durationSeconds,
    durationMs,
    loadProgress,
    loadProgressPercent,
    error,
    loadError,
    mutedStems,
    stemGains,
    focusedStemId,
    focusedGainDb,
    backgroundGainDb,
    playableStems,
    controlsEnabled,
    load,
    activateAndLoadAudio,
    play,
    pause,
    stop,
    seek,
    setStemMuted,
    setStemGain,
    setFocusStem,
    setFocusGains,
    reset,
  };
});

function getErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "Unbekannter Fehler";
}
