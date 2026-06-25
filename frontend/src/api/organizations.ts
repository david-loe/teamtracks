import { apiJson, apiRequest } from "./client";

export interface PublicOrganization {
  id: number;
  name: string;
  imageUrl: string;
}

export interface SessionOrganization extends PublicOrganization {
  isAdmin: boolean;
}

export interface BrowserSession {
  authenticated: boolean;
  organizations: SessionOrganization[];
}

export interface InviteAcceptResult {
  organizationId: number;
  session: BrowserSession;
}

export function listOrganizations(): Promise<PublicOrganization[]> {
  return apiRequest<PublicOrganization[]>("/api/organizations");
}

export function getBrowserSession(): Promise<BrowserSession> {
  return apiRequest<BrowserSession>("/api/session");
}

export function loginToOrganization(organizationId: number, password: string): Promise<BrowserSession> {
  return apiJson<BrowserSession>(`/api/organizations/${organizationId}/session`, { password });
}

export function loginAsOrganizationAdmin(organizationId: number, password: string): Promise<BrowserSession> {
  return apiJson<BrowserSession>(`/api/organizations/${organizationId}/admin/session`, { password });
}

export function leaveAdminMode(organizationId: number): Promise<void> {
  return apiRequest<void>(`/api/organizations/${organizationId}/admin/session`, { method: "DELETE" });
}

export function leaveOrganization(organizationId: number): Promise<void> {
  return apiRequest<void>(`/api/organizations/${organizationId}/session`, { method: "DELETE" });
}

export function logoutBrowser(): Promise<void> {
  return apiRequest<void>("/api/session", { method: "DELETE" });
}

export function acceptInvite(token: string): Promise<InviteAcceptResult> {
  return apiRequest<InviteAcceptResult>(`/api/invites/${encodeURIComponent(token)}/accept`, { method: "POST" });
}
