import { defineStore } from "pinia";
import { computed, ref } from "vue";

import type { BrowserSession, PublicOrganization, SessionOrganization } from "@/api/organizations";
import * as organizationsApi from "@/api/organizations";

const ACTIVE_ORGANIZATION_KEY = "teamtracks-active-organization";

export const useOrganizationsStore = defineStore("organizations", () => {
  const organizations = ref<PublicOrganization[]>([]);
  const sessionOrganizations = ref<SessionOrganization[]>([]);
  const activeOrganizationId = ref<number | null>(readStoredOrganizationId());
  const initialized = ref(false);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const activeOrganization = computed(() =>
    sessionOrganizations.value.find((organization) => organization.id === activeOrganizationId.value) ?? null,
  );

  async function initialize(): Promise<void> {
    if (initialized.value) return;
    try {
      await refreshSession();
    } catch (err) {
      sessionOrganizations.value = [];
      error.value = message(err);
    } finally {
      initialized.value = true;
    }
  }

  async function loadOrganizations(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      organizations.value = await organizationsApi.listOrganizations();
    } catch (err) {
      error.value = message(err);
    } finally {
      loading.value = false;
    }
  }

  async function refreshSession(): Promise<void> {
    applySession(await organizationsApi.getBrowserSession());
  }

  async function login(organizationId: number, password: string): Promise<void> {
    applySession(await organizationsApi.loginToOrganization(organizationId, password));
    setActiveOrganization(organizationId);
  }

  async function loginAdmin(organizationId: number, password: string): Promise<void> {
    applySession(await organizationsApi.loginAsOrganizationAdmin(organizationId, password));
    setActiveOrganization(organizationId);
  }

  async function acceptInvitation(token: string): Promise<number> {
    const result = await organizationsApi.acceptInvite(token);
    applySession(result.session);
    setActiveOrganization(result.organizationId);
    return result.organizationId;
  }

  async function exitAdmin(organizationId: number): Promise<void> {
    await organizationsApi.leaveAdminMode(organizationId);
    await refreshSession();
  }

  async function removeOrganization(organizationId: number): Promise<void> {
    await organizationsApi.leaveOrganization(organizationId);
    await refreshSession();
  }

  async function logout(): Promise<void> {
    await organizationsApi.logoutBrowser();
    applySession({ authenticated: false, organizations: [] });
  }

  function setActiveOrganization(organizationId: number | null): void {
    activeOrganizationId.value = organizationId;
    if (organizationId === null) {
      localStorage.removeItem(ACTIVE_ORGANIZATION_KEY);
    } else {
      localStorage.setItem(ACTIVE_ORGANIZATION_KEY, String(organizationId));
    }
  }

  function hasAccess(organizationId: number): boolean {
    return sessionOrganizations.value.some((organization) => organization.id === organizationId);
  }

  function hasAdminAccess(organizationId: number): boolean {
    return sessionOrganizations.value.some(
      (organization) => organization.id === organizationId && organization.isAdmin,
    );
  }

  function applySession(session: BrowserSession): void {
    sessionOrganizations.value = session.organizations;
    if (activeOrganizationId.value !== null && !hasAccess(activeOrganizationId.value)) {
      setActiveOrganization(session.organizations[0]?.id ?? null);
    }
  }

  return {
    organizations,
    sessionOrganizations,
    activeOrganizationId,
    activeOrganization,
    initialized,
    loading,
    error,
    initialize,
    loadOrganizations,
    refreshSession,
    login,
    loginAdmin,
    acceptInvitation,
    exitAdmin,
    removeOrganization,
    logout,
    setActiveOrganization,
    hasAccess,
    hasAdminAccess,
  };
});

function readStoredOrganizationId(): number | null {
  const value = localStorage.getItem(ACTIVE_ORGANIZATION_KEY);
  if (value === null || !/^[1-9]\d*$/.test(value)) return null;
  return Number(value);
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : "Unbekannter Fehler";
}
