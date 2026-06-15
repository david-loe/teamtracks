import type { StemRole, StemStatus } from "@/api/stems";

export interface SongManifest {
  song: {
    id: number;
    title: string;
    slug: string;
    durationMs: number | null;
    sampleRate: number | null;
  };
  playable: boolean;
  stems: StemManifestItem[];
  playerSettings?: PlayerSettings;
}

export interface PlayerSettings {
  stemGainDefaultDb: number;
  stemGainMinDb: number;
  stemGainMaxDb: number;
  stemGainStepDb: number;
  focusGainDefaultDb: number;
  focusGainMinDb: number;
  focusGainMaxDb: number;
  backgroundGainDefaultDb: number;
  backgroundGainMinDb: number;
  backgroundGainMaxDb: number;
}

export interface StemManifestItem {
  id: number;
  name: string;
  role: StemRole;
  status: StemStatus;
  url: string | null;
  codec: string | null;
  container: "m4a" | null;
  channels: number | null;
  sampleRate: number | null;
  durationMs: number | null;
  fileSizeBytes: number | null;
  bitrateKbps: number | null;
  errorMessage: string | null;
}

export type PlayableStemManifestItem = StemManifestItem & {
  status: "ready";
  url: string;
};

export function isPlayableStem(stem: StemManifestItem): stem is PlayableStemManifestItem {
  return stem.status === "ready" && stem.url !== null;
}
