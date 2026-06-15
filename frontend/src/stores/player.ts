import { defineStore } from "pinia";
import { computed, ref, shallowRef } from "vue";

import * as manifestApi from "@/api/manifest";
import type { AudioEngine, StemLoadProgress } from "@/audio/AudioEngine";
import { ToneAudioEngine } from "@/audio/ToneAudioEngine";
import type { PlayerSettings, SongManifest } from "@/types/manifest";
import { isPlayableStem } from "@/types/manifest";

type PlaybackState = "stopped" | "paused" | "playing";

const CURRENT_TIME_INTERVAL_MS = 200;
const DEFAULT_PLAYER_SETTINGS: PlayerSettings = {
  stemGainDefaultDb: 0, stemGainMinDb: -24, stemGainMaxDb: 6, stemGainStepDb: 1,
  focusGainDefaultDb: 0, focusGainMinDb: -12, focusGainMaxDb: 6,
  backgroundGainDefaultDb: -12, backgroundGainMinDb: -24, backgroundGainMaxDb: 0,
};

export const usePlayerStore = defineStore("player", () => {
  const manifest = ref<SongManifest | null>(null);
  const loadingManifest = ref(false);
  const loadingAudio = ref(false);
  const audioLoaded = ref(false);
  const startingPlayback = ref(false);
  const playbackState = ref<PlaybackState>("stopped");
  const currentTimeSeconds = ref(0);
  const loadProgress = ref<Record<number, StemLoadProgress>>({});
  const error = ref<string | null>(null);
  const loadError = ref<string | null>(null);
  const playbackError = ref<string | null>(null);
  const mutedStems = ref<Record<number, boolean>>({});
  const stemGains = ref<Record<number, number>>({});
  const focusedStemId = ref<number | null>(null);
  const playerSettings = computed(() => manifest.value?.playerSettings ?? DEFAULT_PLAYER_SETTINGS);
  const focusedGainDb = ref(DEFAULT_PLAYER_SETTINGS.focusGainDefaultDb);
  const backgroundGainDb = ref(DEFAULT_PLAYER_SETTINGS.backgroundGainDefaultDb);
  const engine = shallowRef<AudioEngine | null>(null);
  let currentTimeTimer: number | null = null;
  let pageLoadId = 0;
  let audioLoadId = 0;
  let playAttemptId = 0;

  const playableStems = computed(() => manifest.value?.stems.filter(isPlayableStem) ?? []);
  const durationSeconds = computed(() => Math.max(0, (manifest.value?.song.durationMs ?? 0) / 1000));
  const durationMs = computed(() => manifest.value?.song.durationMs ?? null);
  const controlsEnabled = computed(() => audioLoaded.value && !loadingAudio.value);
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
    const requestId = ++pageLoadId;
    resetAudio();
    manifest.value = null;
    loadingManifest.value = true;
    error.value = null;
    loadError.value = null;
    playbackError.value = null;
    try {
      const nextManifest = await manifestApi.getSongManifest(songId);
      if (requestId !== pageLoadId) {
        return;
      }
      manifest.value = nextManifest;
      focusedGainDb.value = playerSettings.value.focusGainDefaultDb;
      backgroundGainDb.value = playerSettings.value.backgroundGainDefaultDb;
      initializeStemControls();
    } catch (err) {
      if (requestId === pageLoadId) {
        manifest.value = null;
        error.value = getErrorMessage(err);
      }
    } finally {
      if (requestId === pageLoadId) {
        loadingManifest.value = false;
      }
    }

    if (requestId === pageLoadId && manifest.value?.playable) {
      await loadAudio();
    }
  }

  async function loadAudio(): Promise<void> {
    if (!manifest.value || !manifest.value.playable || loadingAudio.value) {
      return;
    }

    const requestId = ++audioLoadId;
    const manifestToLoad = manifest.value;
    loadingAudio.value = true;
    audioLoaded.value = false;
    loadError.value = null;
    playbackError.value = null;
    loadProgress.value = {};

    const nextEngine = new ToneAudioEngine();
    engine.value?.dispose();
    engine.value = nextEngine;

    try {
      await nextEngine.loadManifest(manifestToLoad, (progress) => updateLoadProgress(requestId, progress));
      if (requestId !== audioLoadId || engine.value !== nextEngine) {
        return;
      }
      applyAllEngineControls();
      audioLoaded.value = true;
    } catch (err) {
      if (requestId === audioLoadId && engine.value === nextEngine) {
        audioLoaded.value = false;
        nextEngine.dispose();
        engine.value = null;
        loadError.value = getErrorMessage(err);
      }
    } finally {
      if (requestId === audioLoadId) {
        loadingAudio.value = false;
      }
    }
  }

  async function play(): Promise<void> {
    if (!controlsEnabled.value || startingPlayback.value || !engine.value) {
      return;
    }

    const requestId = ++playAttemptId;
    const currentEngine = engine.value;
    startingPlayback.value = true;
    playbackError.value = null;

    try {
      await currentEngine.initializeFromUserGesture();
      if (requestId !== playAttemptId || engine.value !== currentEngine || !controlsEnabled.value) {
        return;
      }
      currentEngine.play();
      playbackState.value = "playing";
      startCurrentTimeTimer();
    } catch (err) {
      if (requestId === playAttemptId && engine.value === currentEngine) {
        playbackError.value = getErrorMessage(err);
      }
    } finally {
      if (requestId === playAttemptId) {
        startingPlayback.value = false;
      }
    }
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
    pageLoadId += 1;
    stopCurrentTimeTimer();
    resetAudio();
    manifest.value = null;
    loadingManifest.value = false;
    error.value = null;
    loadError.value = null;
    playbackError.value = null;
  }

  function resetAudio(): void {
    audioLoadId += 1;
    playAttemptId += 1;
    stopCurrentTimeTimer();
    engine.value?.dispose();
    engine.value = null;
    audioLoaded.value = false;
    loadingAudio.value = false;
    startingPlayback.value = false;
    playbackState.value = "stopped";
    currentTimeSeconds.value = 0;
    loadProgress.value = {};
    mutedStems.value = {};
    stemGains.value = {};
    focusedStemId.value = null;
    focusedGainDb.value = DEFAULT_PLAYER_SETTINGS.focusGainDefaultDb;
    backgroundGainDb.value = DEFAULT_PLAYER_SETTINGS.backgroundGainDefaultDb;
  }

  function updateLoadProgress(requestId: number, progress: StemLoadProgress): void {
    if (requestId !== audioLoadId) {
      return;
    }
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
      nextGains[stem.id] = playerSettings.value.stemGainDefaultDb;
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
    loadingAudio,
    audioLoaded,
    startingPlayback,
    playbackState,
    currentTimeSeconds,
    durationSeconds,
    durationMs,
    loadProgress,
    loadProgressPercent,
    error,
    loadError,
    playbackError,
    mutedStems,
    stemGains,
    focusedStemId,
    focusedGainDb,
    backgroundGainDb,
    playerSettings,
    playableStems,
    controlsEnabled,
    load,
    retryAudioLoad: loadAudio,
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
