<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import {
  deleteAdminOrganization,
  getAdminOrganization,
  regenerateOrganizationInvite,
  updateAdminOrganization,
  updateOrganizationAdminPassword,
  updateOrganizationUserPassword,
} from "@/api/organizationAdmin";
import { ApiError, resolveApiUrl } from "@/api/client";
import type { OrganizationAdmin } from "@/api/platform";
import { useAdminStemsStore } from "@/stores/adminStems";
import { useOrganizationsStore } from "@/stores/organizations";
import { usePlayerStore } from "@/stores/player";
import { useSongsStore } from "@/stores/songs";

const props = defineProps<{ organizationId: string }>();
const organizationId = Number(props.organizationId);
const router = useRouter();
const organizationsStore = useOrganizationsStore();
const songsStore = useSongsStore();
const stemsStore = useAdminStemsStore();
const playerStore = usePlayerStore();

const organization = ref<OrganizationAdmin | null>(null);
const name = ref("");
const image = ref<File | null>(null);
const userPassword = ref("");
const currentAdminPassword = ref("");
const newAdminPassword = ref("");
const deletePassword = ref("");
const loading = ref(false);
const savingMetadata = ref(false);
const savingUserPassword = ref(false);
const savingAdminPassword = ref(false);
const regenerating = ref(false);
const deleting = ref(false);
const copied = ref(false);
const error = ref<string | null>(null);
const success = ref<string | null>(null);

const imageUrl = computed(() => {
  if (!organization.value) return "";
  return `${resolveApiUrl(organization.value.imageUrl)}?v=${encodeURIComponent(organization.value.updatedAt)}`;
});

onMounted(() => void load());

async function load(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    organization.value = await getAdminOrganization(organizationId);
    name.value = organization.value.name;
  } catch (err) {
    error.value = message(err, "Organisation konnte nicht geladen werden.");
  } finally {
    loading.value = false;
  }
}

async function saveMetadata(): Promise<void> {
  savingMetadata.value = true;
  beginAction();
  try {
    organization.value = await updateAdminOrganization(organizationId, {
      name: name.value,
      image: image.value ?? undefined,
    });
    name.value = organization.value.name;
    image.value = null;
    resetFileInput();
    await refreshSession();
    success.value = "Name und Bild wurden gespeichert.";
  } catch (err) {
    error.value = message(err, "Organisation konnte nicht gespeichert werden.");
  } finally {
    savingMetadata.value = false;
  }
}

async function saveUserPassword(): Promise<void> {
  savingUserPassword.value = true;
  beginAction();
  try {
    await updateOrganizationUserPassword(organizationId, userPassword.value);
    userPassword.value = "";
    await refreshSession();
    success.value = "Das User-Passwort wurde geändert. Bestehende User-Zugriffe wurden widerrufen.";
  } catch (err) {
    error.value = message(err, "User-Passwort konnte nicht geändert werden.");
  } finally {
    savingUserPassword.value = false;
  }
}

async function saveAdminPassword(): Promise<void> {
  savingAdminPassword.value = true;
  beginAction();
  try {
    await updateOrganizationAdminPassword(organizationId, currentAdminPassword.value, newAdminPassword.value);
    currentAdminPassword.value = "";
    newAdminPassword.value = "";
    await refreshSession();
    success.value = "Das Admin-Passwort wurde geändert. Bestehende Admin-Zugriffe wurden widerrufen.";
  } catch (err) {
    error.value = err instanceof ApiError && err.status === 401
      ? "Das aktuelle Admin-Passwort ist falsch."
      : message(err, "Admin-Passwort konnte nicht geändert werden.");
  } finally {
    savingAdminPassword.value = false;
  }
}

async function copyInvite(): Promise<void> {
  if (!organization.value) return;
  beginAction();
  try {
    await navigator.clipboard.writeText(organization.value.inviteUrl);
    copied.value = true;
    success.value = "Invite-Link wurde kopiert.";
  } catch {
    error.value = "Invite-Link konnte nicht kopiert werden. Bitte markiere ihn manuell.";
  }
}

async function regenerateInvite(): Promise<void> {
  if (!window.confirm("Aktuellen Invite-Link widerrufen und einen neuen Link erzeugen?")) return;
  regenerating.value = true;
  beginAction();
  try {
    organization.value = await regenerateOrganizationInvite(organizationId);
    success.value = "Ein neuer Invite-Link wurde erzeugt. Der bisherige Link ist ungültig.";
  } catch (err) {
    error.value = message(err, "Invite-Link konnte nicht erneuert werden.");
  } finally {
    regenerating.value = false;
  }
}

async function removeOrganization(): Promise<void> {
  if (!window.confirm("Organisation inklusive aller Songs und Dateien unwiderruflich löschen?")) return;
  deleting.value = true;
  beginAction();
  try {
    await deleteAdminOrganization(organizationId, deletePassword.value);
    resetOrganizationState();
    await organizationsStore.refreshSession();
    await organizationsStore.loadOrganizations();
    const nextId = organizationsStore.activeOrganizationId;
    await router.replace(nextId === null
      ? { name: "organizations" }
      : { name: "songs", params: { organizationId: nextId } });
  } catch (err) {
    error.value = err instanceof ApiError && err.status === 401
      ? "Das Admin-Passwort ist falsch. Die Organisation wurde nicht gelöscht."
      : message(err, "Organisation konnte nicht gelöscht werden.");
  } finally {
    deleting.value = false;
  }
}

async function refreshSession(): Promise<void> {
  await organizationsStore.refreshSession();
  await organizationsStore.loadOrganizations();
}

function setImage(event: Event): void {
  image.value = (event.target as HTMLInputElement).files?.[0] ?? null;
}

function beginAction(): void {
  error.value = null;
  success.value = null;
  copied.value = false;
}

function resetOrganizationState(): void {
  playerStore.reset();
  songsStore.reset();
  stemsStore.reset();
}

function resetFileInput(): void {
  const input = document.getElementById("organization-image") as HTMLInputElement | null;
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
        <p class="eyebrow">Organisations-Admin</p>
        <h1>Organisation verwalten</h1>
        <p class="muted">Stammdaten, Zugänge und Einladungen dieser Organisation verwalten.</p>
      </div>
    </div>

    <p v-if="loading" class="muted">Organisation wird geladen...</p>
    <p v-else-if="error && !organization" class="error-text">{{ error }}</p>
    <div v-else-if="organization" class="admin-organization-grid">
      <section class="panel">
        <h2>Name und Bild</h2>
        <div class="organization-preview">
          <img :src="imageUrl" :alt="organization.name" />
          <strong>{{ organization.name }}</strong>
        </div>
        <form class="stack-form section-block" @submit.prevent="saveMetadata">
          <label>Name<input v-model.trim="name" required maxlength="200" /></label>
          <label>
            Neues Bild
            <input id="organization-image" type="file" accept="image/png,image/jpeg,image/webp" @change="setImage" />
          </label>
          <button class="button button-primary" :disabled="savingMetadata">
            {{ savingMetadata ? "Speichern..." : "Name und Bild speichern" }}
          </button>
        </form>
      </section>

      <section class="panel">
        <h2>Invite-Link</h2>
        <p class="muted">Der Link meldet Empfänger direkt als User dieser Organisation an.</p>
        <div class="invite-row">
          <input :value="organization.inviteUrl" readonly aria-label="Invite-Link" @focus="($event.target as HTMLInputElement).select()" />
          <button class="button button-secondary" type="button" @click="copyInvite">
            {{ copied ? "Kopiert" : "Kopieren" }}
          </button>
        </div>
        <button class="button button-secondary section-block" type="button" :disabled="regenerating" @click="regenerateInvite">
          {{ regenerating ? "Link wird erneuert..." : "Invite-Link regenerieren" }}
        </button>
      </section>

      <section class="panel">
        <h2>User-Passwort ändern</h2>
        <p class="muted">Dadurch werden alle bisherigen User-Anmeldungen dieser Organisation ungültig.</p>
        <form class="stack-form" @submit.prevent="saveUserPassword">
          <label>
            Neues User-Passwort
            <input v-model="userPassword" type="password" minlength="8" autocomplete="new-password" required />
          </label>
          <button class="button button-primary" :disabled="savingUserPassword">
            {{ savingUserPassword ? "Passwort wird geändert..." : "User-Passwort ändern" }}
          </button>
        </form>
      </section>

      <section class="panel">
        <h2>Admin-Passwort ändern</h2>
        <p class="muted">Dadurch werden alle anderen Admin-Anmeldungen dieser Organisation ungültig.</p>
        <form class="stack-form" @submit.prevent="saveAdminPassword">
          <label>
            Aktuelles Admin-Passwort
            <input v-model="currentAdminPassword" type="password" autocomplete="current-password" required />
          </label>
          <label>
            Neues Admin-Passwort
            <input v-model="newAdminPassword" type="password" minlength="8" autocomplete="new-password" required />
          </label>
          <button class="button button-primary" :disabled="savingAdminPassword">
            {{ savingAdminPassword ? "Passwort wird geändert..." : "Admin-Passwort ändern" }}
          </button>
        </form>
      </section>

      <section class="panel danger-zone">
        <h2>Organisation löschen</h2>
        <p>Diese Aktion löscht alle Songs, Stems, Einstellungen und Zugänge unwiderruflich.</p>
        <form class="stack-form" @submit.prevent="removeOrganization">
          <label>
            Admin-Passwort zur Bestätigung
            <input v-model="deletePassword" type="password" autocomplete="current-password" required />
          </label>
          <button class="button button-danger" :disabled="deleting">
            {{ deleting ? "Organisation wird gelöscht..." : "Organisation endgültig löschen" }}
          </button>
        </form>
      </section>
    </div>

    <p v-if="error && organization" class="error-text">{{ error }}</p>
    <p v-if="success" class="success-text">{{ success }}</p>
  </section>
</template>
