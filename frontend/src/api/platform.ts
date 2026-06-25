import { apiJson, apiRequest } from "./client";

export interface PlatformSession {
  authenticated: boolean;
}

export interface OrganizationAdmin {
  id: number;
  name: string;
  imageUrl: string;
  inviteToken: string;
  inviteUrl: string;
  createdAt: string;
  updatedAt: string;
}

export interface OrganizationCreateInput {
  name: string;
  image: File;
  userPassword: string;
  adminPassword: string;
}

export interface OrganizationUpdateInput {
  name?: string;
  image?: File;
  userPassword?: string;
  adminPassword?: string;
}

export function getPlatformSession(): Promise<PlatformSession> {
  return apiRequest<PlatformSession>("/api/platform/session");
}

export function loginPlatform(password: string): Promise<PlatformSession> {
  return apiJson<PlatformSession>("/api/platform/session", { password });
}

export function logoutPlatform(): Promise<void> {
  return apiRequest<void>("/api/platform/session", { method: "DELETE" });
}

export function listPlatformOrganizations(): Promise<OrganizationAdmin[]> {
  return apiRequest<OrganizationAdmin[]>("/api/platform/organizations");
}

export function createPlatformOrganization(input: OrganizationCreateInput): Promise<OrganizationAdmin> {
  return apiRequest<OrganizationAdmin>("/api/platform/organizations", {
    method: "POST",
    body: organizationFormData(input),
  });
}

export function updatePlatformOrganization(
  organizationId: number,
  input: OrganizationUpdateInput,
): Promise<OrganizationAdmin> {
  return apiRequest<OrganizationAdmin>(`/api/platform/organizations/${organizationId}`, {
    method: "PATCH",
    body: organizationFormData(input),
  });
}

export function deletePlatformOrganization(organizationId: number): Promise<void> {
  return apiRequest<void>(`/api/platform/organizations/${organizationId}`, { method: "DELETE" });
}

function organizationFormData(input: OrganizationCreateInput | OrganizationUpdateInput): FormData {
  const form = new FormData();
  if (input.name !== undefined) form.set("name", input.name);
  if (input.image !== undefined) form.set("image", input.image);
  if (input.userPassword !== undefined) form.set("userPassword", input.userPassword);
  if (input.adminPassword !== undefined) form.set("adminPassword", input.adminPassword);
  return form;
}
