import { apiJson, apiRequest } from "./client";

export type ConversionJobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

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
  status: ConversionJobStatus;
  requestedBy: string | null;
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
  return apiJson<ConversionJobBatch>(`/api/songs/${songId}/conversion-jobs`, input);
}

export function getConversionJob(jobId: number): Promise<ConversionJob> {
  return apiRequest<ConversionJob>(`/api/conversion-jobs/${jobId}`);
}

export function listConversionJobs(songId: number): Promise<ConversionJob[]> {
  return apiRequest<ConversionJob[]>(`/api/songs/${songId}/conversion-jobs`);
}
