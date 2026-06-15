import { apiJson, apiRequest } from "./client";

export interface AppSettings {
  monoBitrateKbps: number;
  stereoBitrateKbps: number;
  targetSampleRate: 44100 | 48000;
  durationToleranceMs: number;
  stemGainDefaultDb: number;
  stemGainMinDb: number;
  stemGainMaxDb: number;
  stemGainStepDb: number;
  focusGainDefaultDb: number;
  focusGainMinDb: number;
  focusGainMaxDb: number;
  backgroundGainDefaultDb: number;
  backgroundGainMinDb: number;
  backgroundGainMaxDb: number;
}

export function getSettings(): Promise<AppSettings> {
  return apiRequest<AppSettings>("/api/admin/settings");
}

export function updateSettings(settings: AppSettings): Promise<AppSettings> {
  return apiJson<AppSettings>("/api/admin/settings", settings, { method: "PUT" });
}
