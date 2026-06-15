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
  songId: number,
  input: ConversionJobCreateInput = {},
): Promise<ConversionJobBatch> {
  return apiJson<ConversionJobBatch>(`/api/admin/songs/${songId}/conversion-jobs`, input);
}

export function getConversionJob(jobId: number): Promise<ConversionJob> {
  return apiRequest<ConversionJob>(`/api/admin/conversion-jobs/${jobId}`);
}

export function listConversionJobs(songId: number): Promise<ConversionJob[]> {
  return apiRequest<ConversionJob[]>(`/api/admin/songs/${songId}/conversion-jobs`);
}
