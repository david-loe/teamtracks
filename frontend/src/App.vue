<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";

import { useAdminStemsStore } from "@/stores/adminStems";
import { resolveApiUrl } from "@/api/client";
import { useOrganizationsStore } from "@/stores/organizations";
import { usePlayerStore } from "@/stores/player";
import { useSongsStore } from "@/stores/songs";

const route = useRoute();
const router = useRouter();
const organizationsStore = useOrganizationsStore();
const songsStore = useSongsStore();
const stemsStore = useAdminStemsStore();
const playerStore = usePlayerStore();

const platformArea = computed(() => Boolean(route.meta.platform || route.meta.platformLogin));
const organizationId = computed(() => Number(route.params.organizationId) || organizationsStore.activeOrganizationId);
const activeOrganization = computed(() =>
  platformArea.value
    ? null
    : organizationsStore.sessionOrganizations.find((organization) => organization.id === organizationId.value) ?? null,
);
const adminArea = computed(() => Boolean(route.meta.admin || route.meta.adminLogin));
const organizationHome = computed(() =>
  platformArea.value
    ? "/platform/organizations"
    : organizationId.value ? `/org/${organizationId.value}/${adminArea.value ? "admin/songs" : "songs"}` : "/organizations",
);

async function switchOrganization(event: Event): Promise<void> {
  const nextId = Number((event.target as HTMLSelectElement).value);
  if (!Number.isFinite(nextId) || nextId === organizationId.value) return;
  resetOrganizationState();
  organizationsStore.setActiveOrganization(nextId);
  await router.push({ name: "songs", params: { organizationId: nextId } });
}

async function exitAdmin(): Promise<void> {
  if (!organizationId.value) return;
  await organizationsStore.exitAdmin(organizationId.value);
  resetOrganizationState();
  await router.push({ name: "songs", params: { organizationId: organizationId.value } });
}

async function leaveCurrentOrganization(): Promise<void> {
  if (!organizationId.value) return;
  await organizationsStore.removeOrganization(organizationId.value);
  resetOrganizationState();
  const nextId = organizationsStore.activeOrganizationId;
  await router.push(nextId === null ? { name: "organizations" } : { name: "songs", params: { organizationId: nextId } });
}

async function logout(): Promise<void> {
  await organizationsStore.logout();
  resetOrganizationState();
  await router.push({ name: "organizations" });
}

function resetOrganizationState(): void {
  playerStore.reset();
  songsStore.reset();
  stemsStore.reset();
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink class="brand" :to="organizationHome">TeamTracks</RouterLink>
      <nav v-if="platformArea" class="nav">
        <RouterLink v-if="route.meta.platform" to="/platform/organizations">Organisationen</RouterLink>
        <RouterLink to="/organizations">Zur App</RouterLink>
      </nav>
      <nav v-if="activeOrganization" class="nav">
        <RouterLink :to="`/org/${organizationId}/songs`">Songs</RouterLink>
        <RouterLink :to="`/org/${organizationId}/settings`">Einstellungen</RouterLink>
        <RouterLink v-if="activeOrganization.isAdmin" :to="`/org/${organizationId}/admin/songs`">Admin</RouterLink>
        <RouterLink v-else :to="`/org/${organizationId}/admin/login`">Admin</RouterLink>
        <RouterLink v-if="activeOrganization.isAdmin" :to="`/org/${organizationId}/admin/organization`">Organisation</RouterLink>
        <img class="organization-avatar" :src="resolveApiUrl(activeOrganization.imageUrl)" :alt="activeOrganization.name" />
        <select class="organization-switcher" :value="organizationId" aria-label="Organisation" @change="switchOrganization">
          <option v-for="organization in organizationsStore.sessionOrganizations" :key="organization.id" :value="organization.id">
            {{ organization.name }}{{ organization.isAdmin ? " · Admin" : "" }}
          </option>
        </select>
        <RouterLink to="/organizations">Weitere Organisation</RouterLink>
        <button v-if="activeOrganization.isAdmin" class="nav-button" @click="exitAdmin">Admin verlassen</button>
        <button class="nav-button" @click="leaveCurrentOrganization">Organisation verlassen</button>
        <button class="nav-button" @click="logout">Logout</button>
      </nav>
    </header>

    <main class="main-content"><RouterView /></main>
  </div>
</template>
