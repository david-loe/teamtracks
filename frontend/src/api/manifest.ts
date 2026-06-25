import { apiRequest } from "./client";

import type { SongManifest } from "@/types/manifest";

export function getSongManifest(organizationId: number, songId: number, key?: number | null): Promise<SongManifest> {
  const params = new URLSearchParams();
  if (key !== undefined && key !== null) params.set("key", String(key));
  const suffix = params.size ? `?${params}` : "";
  return apiRequest<SongManifest>(`/api/organizations/${organizationId}/songs/${songId}/manifest${suffix}`);
}
