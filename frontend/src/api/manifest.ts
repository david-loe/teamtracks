import { apiRequest } from "./client";

import type { SongManifest } from "@/types/manifest";

export function getSongManifest(songId: number, key?: number | null): Promise<SongManifest> {
  const params = new URLSearchParams();
  if (key !== undefined && key !== null) params.set("key", String(key));
  const suffix = params.size ? `?${params}` : "";
  return apiRequest<SongManifest>(`/api/public/songs/${songId}/manifest${suffix}`);
}
