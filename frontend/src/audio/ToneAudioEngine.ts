import * as Tone from "tone";

import { resolveApiUrl } from "@/api/client";
import type { AudioEngine, FocusOptions, StemLoadProgress } from "@/audio/AudioEngine";
import type { SongManifest } from "@/types/manifest";
import { isPlayableStem, type PlayableStemManifestItem } from "@/types/manifest";

interface StemNode {
  player: Tone.Player;
  gain: Tone.Gain<"decibels">;
  baseGainDb: number;
  muted: boolean;
  focusable: boolean;
}

type PlaybackState = "stopped" | "paused" | "playing";

const SCHEDULE_OFFSET_SECONDS = 0.05;
const SILENT_GAIN_DB = -Infinity;

export class ToneAudioEngine implements AudioEngine {
  private readonly stems = new Map<number, StemNode>();
  private abortController: AbortController | null = null;
  private focus: FocusOptions = {
    stemId: null,
    focusedGainDb: 0,
    backgroundGainDb: -12,
  };
  private durationSeconds = 0;
  private playbackState: PlaybackState = "stopped";
  private offsetSeconds = 0;
  private startedAtSeconds = 0;

  async initializeFromUserGesture(): Promise<void> {
    await Tone.start();
  }

  async loadManifest(manifest: SongManifest, onProgress: (progress: StemLoadProgress) => void): Promise<void> {
    this.disposeNodes();
    this.durationSeconds = Math.max(0, (manifest.song.durationMs ?? 0) / 1000);
    this.abortController = new AbortController();

    const playableStems = manifest.stems.filter(isPlayableStem);
    await Promise.all(
      playableStems.map(async (stem) => {
        const audioBuffer = await this.loadAudioBuffer(stem, onProgress, this.abortController?.signal);
        const player = new Tone.Player(audioBuffer);
        const gain = new Tone.Gain(0, "decibels").toDestination();
        player.connect(gain);
        this.stems.set(stem.id, {
          player,
          gain,
          baseGainDb: 0,
          muted: false,
          focusable: stem.focusable,
        });
        this.applyStemGain(stem.id);
      }),
    );
  }

  play(): void {
    if (this.playbackState === "playing" || this.stems.size === 0) {
      return;
    }

    const offset = this.clampPosition(this.offsetSeconds);
    if (offset >= this.durationSeconds && this.durationSeconds > 0) {
      this.offsetSeconds = 0;
    }

    const startOffset = this.clampPosition(this.offsetSeconds);
    const startTime = Tone.now() + SCHEDULE_OFFSET_SECONDS;
    const duration = this.durationSeconds > 0 ? Math.max(0, this.durationSeconds - startOffset) : undefined;

    for (const node of this.stems.values()) {
      node.player.start(startTime, startOffset, duration);
    }

    this.startedAtSeconds = startTime;
    this.playbackState = "playing";
  }

  pause(): void {
    if (this.playbackState !== "playing") {
      return;
    }
    this.offsetSeconds = this.getCurrentTime();
    this.stopPlayers();
    this.playbackState = "paused";
  }

  stop(): void {
    this.stopPlayers();
    this.offsetSeconds = 0;
    this.playbackState = "stopped";
  }

  seek(positionSeconds: number): void {
    const nextPosition = this.clampPosition(positionSeconds);
    const wasPlaying = this.playbackState === "playing";
    this.stopPlayers();
    this.offsetSeconds = nextPosition;
    this.playbackState = wasPlaying ? "paused" : this.playbackState;
    if (wasPlaying) {
      this.play();
    }
  }

  setStemMuted(stemId: number, muted: boolean): void {
    const node = this.stems.get(stemId);
    if (!node) {
      return;
    }
    node.muted = muted;
    this.applyStemGain(stemId);
  }

  setStemGain(stemId: number, gainDb: number): void {
    const node = this.stems.get(stemId);
    if (!node) {
      return;
    }
    node.baseGainDb = gainDb;
    this.applyStemGain(stemId);
  }

  setFocus(options: FocusOptions): void {
    this.focus = options;
    for (const stemId of this.stems.keys()) {
      this.applyStemGain(stemId);
    }
  }

  getCurrentTime(): number {
    if (this.playbackState !== "playing") {
      return this.clampPosition(this.offsetSeconds);
    }

    const elapsed = Math.max(0, Tone.now() - this.startedAtSeconds);
    return this.clampPosition(this.offsetSeconds + elapsed);
  }

  getDuration(): number {
    return this.durationSeconds;
  }

  dispose(): void {
    this.abortController?.abort();
    this.abortController = null;
    this.disposeNodes();
  }

  private async loadAudioBuffer(
    stem: PlayableStemManifestItem,
    onProgress: (progress: StemLoadProgress) => void,
    signal?: AbortSignal,
  ): Promise<AudioBuffer> {
    const arrayBuffer = await fetchArrayBufferWithProgress(resolveApiUrl(stem.url), stem.id, onProgress, signal);
    return Tone.getContext().decodeAudioData(arrayBuffer);
  }

  private applyStemGain(stemId: number): void {
    const node = this.stems.get(stemId);
    if (!node) {
      return;
    }

    node.gain.gain.value = node.muted ? SILENT_GAIN_DB : node.baseGainDb + this.getFocusGain(stemId);
  }

  private getFocusGain(stemId: number): number {
    if (this.focus.stemId === null) {
      return 0;
    }
    const node = this.stems.get(stemId);
    if (!node?.focusable) {
      return 0;
    }
    return stemId === this.focus.stemId ? this.focus.focusedGainDb : this.focus.backgroundGainDb;
  }

  private stopPlayers(): void {
    const now = Tone.now();
    for (const node of this.stems.values()) {
      node.player.stop(now);
    }
  }

  private disposeNodes(): void {
    this.stopPlayers();
    for (const node of this.stems.values()) {
      node.player.dispose();
      node.gain.dispose();
    }
    this.stems.clear();
    this.playbackState = "stopped";
    this.offsetSeconds = 0;
    this.startedAtSeconds = 0;
  }

  private clampPosition(positionSeconds: number): number {
    const safePosition = Number.isFinite(positionSeconds) ? positionSeconds : 0;
    if (this.durationSeconds <= 0) {
      return Math.max(0, safePosition);
    }
    return Math.min(Math.max(0, safePosition), this.durationSeconds);
  }
}

async function fetchArrayBufferWithProgress(
  url: string,
  stemId: number,
  onProgress: (progress: StemLoadProgress) => void,
  signal?: AbortSignal,
): Promise<ArrayBuffer> {
  const response = await fetch(url, { signal });
  if (!response.ok) {
    throw new Error(`Audio-Datei konnte nicht geladen werden (${response.status}).`);
  }

  const totalBytes = parseContentLength(response.headers.get("content-length"));
  const reader = response.body?.getReader();
  if (!reader) {
    const buffer = await response.arrayBuffer();
    onProgress({
      stemId,
      loadedBytes: buffer.byteLength,
      totalBytes: buffer.byteLength,
      ratio: 1,
    });
    return buffer;
  }

  const chunks: Uint8Array[] = [];
  let loadedBytes = 0;
  onProgress({ stemId, loadedBytes, totalBytes, ratio: 0 });

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    chunks.push(value);
    loadedBytes += value.byteLength;
    onProgress({
      stemId,
      loadedBytes,
      totalBytes,
      ratio: totalBytes === null ? 0 : Math.min(1, loadedBytes / totalBytes),
    });
  }

  const buffer = mergeChunks(chunks, loadedBytes);
  onProgress({ stemId, loadedBytes, totalBytes: totalBytes ?? loadedBytes, ratio: 1 });
  return buffer;
}

function parseContentLength(value: string | null): number | null {
  if (value === null) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function mergeChunks(chunks: Uint8Array[], totalBytes: number): ArrayBuffer {
  const bytes = new Uint8Array(totalBytes);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return bytes.buffer;
}
