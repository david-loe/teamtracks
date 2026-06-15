import { apiRequest } from "./client";

import type { SongManifest } from "@/types/manifest";

export function getSongManifest(songId: number, keyId?: number | null): Promise<SongManifest> {
  const params = new URLSearchParams();
  if (keyId !== undefined && keyId !== null) params.set("keyId", String(keyId));
  const suffix = params.size ? `?${params}` : "";
  return apiRequest<SongManifest>(`/api/public/songs/${songId}/manifest${suffix}`);
}
