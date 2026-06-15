import { apiJson, apiRequest } from "./client";

import type { SongStatus } from "@/api/songs";
import type { ConversionJobBatch } from "@/api/conversion";
import type { StemRole, StemStatus } from "@/api/stems";

export interface SongKey {
  id: number;
  songId: number;
  semitoneOffset: number;
  isOriginal: boolean;
  status: SongStatus;
  errorMessage: string | null;
}

export interface TransposeSongInput {
  targetKeys: number[];
}

export interface StemKeyAssetVariant {
  songKeyId: number;
  semitoneOffset: number;
  targetKey: number;
  status: StemStatus | SongStatus;
  errorMessage: string | null;
}

export interface StemKeyAssetInventoryItem {
  stemId: number;
  stemName: string;
  stemRole: StemRole;
  variants: StemKeyAssetVariant[];
}

export function transposeSong(songId: number, input: TransposeSongInput): Promise<ConversionJobBatch> {
  return apiJson<ConversionJobBatch>(`/api/admin/songs/${songId}/transpose`, input);
}

export function listKeyAssets(songId: number): Promise<StemKeyAssetInventoryItem[]> {
  return apiRequest<StemKeyAssetInventoryItem[]>(`/api/admin/songs/${songId}/key-assets`);
}
