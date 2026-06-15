import { apiRequest } from "./client";

import type { SongManifest } from "@/types/manifest";

export function getSongManifest(songId: number): Promise<SongManifest> {
  return apiRequest<SongManifest>(`/api/songs/${songId}/manifest`);
}
