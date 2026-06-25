import { apiJson, apiRequest } from "./client";

export type ConversionJobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";
export type ConversionJobType = "stem_conversion" | "song_transposition";

export interface ConversionJobCreateInput {
  stemIds?: number[] | null;
  requestedBy?: string | null;
}

export interface ConversionJobBatch {
  jobIds: number[];
  status: ConversionJobStatus;
}

export interface ConversionJob {
  id: number;
  songId: number;
  stemId: number | null;
  songKeyId: number | null;
  jobType: ConversionJobType;
  targetKey: number | null;
  semitoneOffset: number | null;
  status: ConversionJobStatus;
  requestedBy: string | null;
  monoBitrateKbps: number;
  stereoBitrateKbps: number;
  targetSampleRate: number;
  durationToleranceMs: number;
  startedAt: string | null;
  finishedAt: string | null;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}

export function createConversionJobs(
  organizationId: number,
  songId: number,
  input: ConversionJobCreateInput = {},
): Promise<ConversionJobBatch> {
  return apiJson<ConversionJobBatch>(`/api/organizations/${organizationId}/admin/songs/${songId}/conversion-jobs`, input);
}

export function getConversionJob(organizationId: number, jobId: number): Promise<ConversionJob> {
  return apiRequest<ConversionJob>(`/api/organizations/${organizationId}/admin/conversion-jobs/${jobId}`);
}

export function listConversionJobs(organizationId: number, songId: number): Promise<ConversionJob[]> {
  return apiRequest<ConversionJob[]>(`/api/organizations/${organizationId}/admin/songs/${songId}/conversion-jobs`);
}
