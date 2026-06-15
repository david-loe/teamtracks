import { apiJson, apiRequest } from "./client";

export type SongStatus = "draft" | "ready" | "error";

export interface SongCreateInput {
  title: string;
  slug: string;
  description?: string | null;
}

export interface Song {
  id: number;
  title: string;
  slug: string;
  description: string | null;
  status: SongStatus;
  targetSampleRate: number | null;
  targetDurationMs: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface SongListItem {
  id: number;
  title: string;
  slug: string;
  status: SongStatus;
  stemCount: number;
  readyStemCount: number;
  durationMs: number | null;
}

export function listSongs(): Promise<SongListItem[]> {
  return apiRequest<SongListItem[]>("/api/admin/songs");
}

export function listPublicSongs(query = ""): Promise<SongListItem[]> {
  const params = new URLSearchParams();
  if (query.trim()) params.set("query", query.trim());
  const suffix = params.size ? `?${params}` : "";
  return apiRequest<SongListItem[]>(`/api/public/songs${suffix}`);
}

export function createSong(input: SongCreateInput): Promise<Song> {
  return apiJson<Song>("/api/admin/songs", input);
}

export function getSong(songId: number): Promise<Song> {
  return apiRequest<Song>(`/api/admin/songs/${songId}`);
}

export function deleteSong(songId: number): Promise<void> {
  return apiRequest<void>(`/api/admin/songs/${songId}`, { method: "DELETE" });
}
