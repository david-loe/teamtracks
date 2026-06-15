import type { SongManifest } from "@/types/manifest";

export interface StemLoadProgress {
  stemId: number;
  loadedBytes: number;
  totalBytes: number | null;
  ratio: number;
}

export interface FocusOptions {
  stemId: number | null;
  focusedGainDb: number;
  backgroundGainDb: number;
}

export interface AudioEngine {
  initializeFromUserGesture(): Promise<void>;
  loadManifest(manifest: SongManifest, onProgress: (progress: StemLoadProgress) => void): Promise<void>;
  play(): void;
  pause(): void;
  stop(): void;
  seek(positionSeconds: number): void;
  setStemMuted(stemId: number, muted: boolean): void;
  setStemGain(stemId: number, gainDb: number): void;
  setFocus(options: FocusOptions): void;
  getCurrentTime(): number;
  getDuration(): number;
  dispose(): void;
}
