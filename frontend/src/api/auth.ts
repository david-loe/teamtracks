import { apiJson, apiRequest } from "./client";

export interface SessionStatus {
  authenticated: boolean;
}

export function login(password: string): Promise<SessionStatus> {
  return apiJson<SessionStatus>("/api/admin/session", { password });
}

export function getSession(): Promise<SessionStatus> {
  return apiRequest<SessionStatus>("/api/admin/session");
}

export function logout(): Promise<void> {
  return apiRequest<void>("/api/admin/session", { method: "DELETE" });
}
