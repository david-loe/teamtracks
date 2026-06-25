<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { resolveApiUrl } from "@/api/client";
import type { OrganizationAdmin } from "@/api/platform";
import {
  createPlatformOrganization,
  deletePlatformOrganization,
  listPlatformOrganizations,
  updatePlatformOrganization,
} from "@/api/platform";
import { useOrganizationsStore } from "@/stores/organizations";
import { usePlatformStore } from "@/stores/platform";

interface EditDraft {
  name: string;
  userPassword: string;
  adminPassword: string;
  image: File | null;
  saving: boolean;
  error: string | null;
  saved: boolean;
}

const router = useRouter();
const platformStore = usePlatformStore();
const organizationsStore = useOrganizationsStore();
const organizations = ref<OrganizationAdmin[]>([]);
const drafts = reactive<Record<number, EditDraft>>({});
const loading = ref(false);
const error = ref<string | null>(null);
const creating = ref(false);
const createError = ref<string | null>(null);
const createForm = reactive({
  name: "",
  image: null as File | null,
  userPassword: "",
  adminPassword: "",
});

onMounted(() => void load());

async function load(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    organizations.value = await listPlatformOrganizations();
    for (const organization of organizations.value) {
      drafts[organization.id] ??= newDraft(organization);
    }
  } catch (err) {
    error.value = message(err, "Organisationen konnten nicht geladen werden.");
  } finally {
    loading.value = false;
  }
}

async function createOrganization(): Promise<void> {
  if (!createForm.image) {
    createError.value = "Bitte wähle ein Bild aus.";
    return;
  }
  creating.value = true;
  createError.value = null;
  try {
    const organization = await createPlatformOrganization({
      name: createForm.name,
      image: createForm.image,
      userPassword: createForm.userPassword,
      adminPassword: createForm.adminPassword,
    });
    organizations.value.push(organization);
    organizations.value.sort((left, right) => left.name.localeCompare(right.name));
    drafts[organization.id] = newDraft(organization);
    createForm.name = "";
    createForm.image = null;
    createForm.userPassword = "";
    createForm.adminPassword = "";
    resetFileInput("platform-create-image");
    await refreshBrowserOrganizations();
  } catch (err) {
    createError.value = message(err, "Organisation konnte nicht erstellt werden.");
  } finally {
    creating.value = false;
  }
}

async function saveOrganization(organization: OrganizationAdmin): Promise<void> {
  const draft = drafts[organization.id];
  draft.saving = true;
  draft.error = null;
  draft.saved = false;
  try {
    const updated = await updatePlatformOrganization(organization.id, {
      name: draft.name.trim() === organization.name ? undefined : draft.name,
      image: draft.image ?? undefined,
      userPassword: draft.userPassword || undefined,
      adminPassword: draft.adminPassword || undefined,
    });
    replaceOrganization(updated);
    drafts[organization.id] = { ...newDraft(updated), saved: true };
    resetFileInput(`platform-edit-image-${organization.id}`);
    await refreshBrowserOrganizations();
  } catch (err) {
    draft.error = message(err, "Organisation konnte nicht gespeichert werden.");
  } finally {
    drafts[organization.id].saving = false;
  }
}

async function removeOrganization(organization: OrganizationAdmin): Promise<void> {
  if (!window.confirm(`Organisation „${organization.name}“ inklusive aller Songs unwiderruflich löschen?`)) return;
  const draft = drafts[organization.id];
  draft.error = null;
  try {
    await deletePlatformOrganization(organization.id);
    organizations.value = organizations.value.filter((entry) => entry.id !== organization.id);
    delete drafts[organization.id];
    await refreshBrowserOrganizations();
  } catch (err) {
    draft.error = message(err, "Organisation konnte nicht gelöscht werden.");
  }
}

async function logout(): Promise<void> {
  await platformStore.logout();
  await router.replace({ name: "platform-login" });
}

function replaceOrganization(updated: OrganizationAdmin): void {
  organizations.value = organizations.value.map((organization) =>
    organization.id === updated.id ? updated : organization,
  );
  organizations.value.sort((left, right) => left.name.localeCompare(right.name));
}

async function refreshBrowserOrganizations(): Promise<void> {
  await organizationsStore.refreshSession();
  await organizationsStore.loadOrganizations();
}

function setCreateImage(event: Event): void {
  createForm.image = (event.target as HTMLInputElement).files?.[0] ?? null;
}

function setEditImage(organizationId: number, event: Event): void {
  drafts[organizationId].image = (event.target as HTMLInputElement).files?.[0] ?? null;
}

function newDraft(organization: OrganizationAdmin): EditDraft {
  return {
    name: organization.name,
    userPassword: "",
    adminPassword: "",
    image: null,
    saving: false,
    error: null,
    saved: false,
  };
}

function imageUrl(organization: OrganizationAdmin): string {
  return `${resolveApiUrl(organization.imageUrl)}?v=${encodeURIComponent(organization.updatedAt)}`;
}

function resetFileInput(id: string): void {
  const input = document.getElementById(id) as HTMLInputElement | null;
  if (input) input.value = "";
}

function message(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}
</script>

<template>
  <section>
    <div class="page-header">
      <div>
        <p class="eyebrow">Plattformverwaltung</p>
        <h1>Organisationen</h1>
        <p class="muted">Organisationen erstellen, bearbeiten und vollständig löschen.</p>
      </div>
      <button class="button button-secondary" @click="logout">Plattform-Logout</button>
    </div>

    <section class="panel">
      <h2>Organisation erstellen</h2>
      <form class="management-form" @submit.prevent="createOrganization">
        <label>Name<input v-model.trim="createForm.name" required maxlength="200" /></label>
        <label>
          Bild
          <input id="platform-create-image" type="file" accept="image/png,image/jpeg,image/webp" required @change="setCreateImage" />
        </label>
        <label>
          User-Passwort
          <input v-model="createForm.userPassword" type="password" minlength="8" autocomplete="new-password" required />
        </label>
        <label>
          Admin-Passwort
          <input v-model="createForm.adminPassword" type="password" minlength="8" autocomplete="new-password" required />
        </label>
        <p v-if="createError" class="error-text form-wide">{{ createError }}</p>
        <div class="form-wide">
          <button class="button button-primary" :disabled="creating">
            {{ creating ? "Organisation wird erstellt..." : "Organisation erstellen" }}
          </button>
        </div>
      </form>
    </section>

    <p v-if="loading" class="muted section-block">Organisationen werden geladen...</p>
    <p v-else-if="error" class="error-text">{{ error }}</p>
    <div v-else class="management-list section-block">
      <article v-for="organization in organizations" :key="organization.id" class="panel organization-management-card">
        <div class="organization-management-heading">
          <img :src="imageUrl(organization)" :alt="organization.name" />
          <div>
            <p class="eyebrow">Organisation {{ organization.id }}</p>
            <h2>{{ organization.name }}</h2>
          </div>
        </div>
        <form class="management-form" @submit.prevent="saveOrganization(organization)">
          <label>Name<input v-model.trim="drafts[organization.id].name" required maxlength="200" /></label>
          <label>
            Neues Bild
            <input
              :id="`platform-edit-image-${organization.id}`"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              @change="setEditImage(organization.id, $event)"
            />
          </label>
          <label>
            Neues User-Passwort
            <input v-model="drafts[organization.id].userPassword" type="password" minlength="8" autocomplete="new-password" />
          </label>
          <label>
            Neues Admin-Passwort
            <input v-model="drafts[organization.id].adminPassword" type="password" minlength="8" autocomplete="new-password" />
          </label>
          <p class="muted form-wide">Leere Passwortfelder bleiben unverändert.</p>
          <p v-if="drafts[organization.id].error" class="error-text form-wide">{{ drafts[organization.id].error }}</p>
          <p v-if="drafts[organization.id].saved" class="success-text form-wide">Organisation gespeichert.</p>
          <div class="form-actions form-wide">
            <button class="button button-primary" :disabled="drafts[organization.id].saving">
              {{ drafts[organization.id].saving ? "Speichern..." : "Änderungen speichern" }}
            </button>
            <button class="button button-danger" type="button" @click="removeOrganization(organization)">
              Organisation löschen
            </button>
          </div>
        </form>
      </article>
      <p v-if="organizations.length === 0" class="panel muted">Noch keine Organisation vorhanden.</p>
    </div>
  </section>
</template>
