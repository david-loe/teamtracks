import { apiJson, apiRequest } from "./client";

export type SongStatus = "draft" | "ready" | "error";

export interface SongCreateInput {
  title: string;
  artist: string;
  slug: string;
  description?: string | null;
  originalKey: number;
}

export interface SongUpdateInput {
  title: string;
  artist: string;
  originalKey: number;
}

export interface Song {
  id: number;
  title: string;
  artist: string;
  slug: string;
  description: string | null;
  status: SongStatus;
  originalKey: number;
  targetSampleRate: number | null;
  targetDurationMs: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface SongListItem {
  id: number;
  title: string;
  artist: string;
  slug: string;
  status: SongStatus;
  originalKey: number;
  stemCount: number;
  readyStemCount: number;
  durationMs: number | null;
}

export function listSongs(organizationId: number): Promise<SongListItem[]> {
  return apiRequest<SongListItem[]>(`/api/organizations/${organizationId}/admin/songs`);
}

export function listPublicSongs(organizationId: number, query = ""): Promise<SongListItem[]> {
  const params = new URLSearchParams();
  if (query.trim()) params.set("query", query.trim());
  const suffix = params.size ? `?${params}` : "";
  return apiRequest<SongListItem[]>(`/api/organizations/${organizationId}/songs${suffix}`);
}

export function createSong(organizationId: number, input: SongCreateInput): Promise<Song> {
  return apiJson<Song>(`/api/organizations/${organizationId}/admin/songs`, input);
}

export function getSong(organizationId: number, songId: number): Promise<Song> {
  return apiRequest<Song>(`/api/organizations/${organizationId}/admin/songs/${songId}`);
}

export function updateSong(organizationId: number, songId: number, input: SongUpdateInput): Promise<Song> {
  return apiJson<Song>(`/api/organizations/${organizationId}/admin/songs/${songId}`, input, { method: "PATCH" });
}

export function deleteSong(organizationId: number, songId: number): Promise<void> {
  return apiRequest<void>(`/api/organizations/${organizationId}/admin/songs/${songId}`, { method: "DELETE" });
}
