import type { OrganizationAdmin } from "./platform";
import { apiJson, apiRequest } from "./client";

export function getAdminOrganization(organizationId: number): Promise<OrganizationAdmin> {
  return apiRequest<OrganizationAdmin>(`/api/organizations/${organizationId}/admin/organization`);
}

export function updateAdminOrganization(
  organizationId: number,
  input: { name?: string; image?: File },
): Promise<OrganizationAdmin> {
  const form = new FormData();
  if (input.name !== undefined) form.set("name", input.name);
  if (input.image !== undefined) form.set("image", input.image);
  return apiRequest<OrganizationAdmin>(`/api/organizations/${organizationId}/admin/organization`, {
    method: "PATCH",
    body: form,
  });
}

export function updateOrganizationUserPassword(organizationId: number, newPassword: string): Promise<void> {
  return apiJson<void>(
    `/api/organizations/${organizationId}/admin/organization/user-password`,
    { newPassword },
    { method: "PUT" },
  );
}

export function updateOrganizationAdminPassword(
  organizationId: number,
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  return apiJson<void>(
    `/api/organizations/${organizationId}/admin/organization/admin-password`,
    { currentPassword, newPassword },
    { method: "PUT" },
  );
}

export function regenerateOrganizationInvite(organizationId: number): Promise<OrganizationAdmin> {
  return apiRequest<OrganizationAdmin>(
    `/api/organizations/${organizationId}/admin/organization/invite/regenerate`,
    { method: "POST" },
  );
}

export function deleteAdminOrganization(organizationId: number, adminPassword: string): Promise<void> {
  return apiJson<void>(
    `/api/organizations/${organizationId}/admin/organization`,
    { adminPassword },
    { method: "DELETE" },
  );
}
