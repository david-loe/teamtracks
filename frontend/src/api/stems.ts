import { apiRequest } from "./client";

export type StemRole = "drums" | "bass" | "vocals" | "guitar" | "keys" | "click_cue" | "other";
export type StemStatus = "uploaded" | "converting" | "ready" | "error";

export const STEM_ROLES: StemRole[] = ["drums", "bass", "vocals", "guitar", "keys", "click_cue", "other"];

export interface Stem {
  id: number;
  songId: number;
  name: string;
  role: StemRole;
  key: number | null;
  status: StemStatus;
  sourceFilename: string | null;
  sourceFormat: string;
  codec: string | null;
  sampleRate: number | null;
  channels: number | null;
  durationMs: number | null;
  fileSizeBytes: number | null;
  bitrateKbps: number | null;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface StemUploadInput {
  name: string;
  role: StemRole;
  key?: number | null;
  file: File;
}

export type StemUploadResult =
  | { input: StemUploadInput; stem: Stem; error: null }
  | { input: StemUploadInput; stem: null; error: string };

export function listStems(organizationId: number, songId: number): Promise<Stem[]> {
  return apiRequest<Stem[]>(`/api/organizations/${organizationId}/admin/songs/${songId}/stems`);
}

export function uploadStem(organizationId: number, songId: number, input: StemUploadInput): Promise<Stem> {
  const formData = new FormData();
  formData.set("name", input.name);
  formData.set("role", input.role);
  if (input.key !== undefined && input.key !== null) {
    formData.set("key", String(input.key));
  }
  formData.set("file", input.file);

  return apiRequest<Stem>(`/api/organizations/${organizationId}/admin/songs/${songId}/stems/upload`, {
    method: "POST",
    body: formData,
  });
}

export function deleteStem(organizationId: number, stemId: number): Promise<void> {
  return apiRequest<void>(`/api/organizations/${organizationId}/admin/stems/${stemId}`, { method: "DELETE" });
}
