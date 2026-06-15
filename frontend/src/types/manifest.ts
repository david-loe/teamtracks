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
