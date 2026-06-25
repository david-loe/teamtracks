<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import type { PublicOrganization } from "@/api/organizations";
import { ApiError } from "@/api/client";
import { resolveApiUrl } from "@/api/client";
import { useOrganizationsStore } from "@/stores/organizations";

const route = useRoute();
const router = useRouter();
const store = useOrganizationsStore();
const selected = ref<PublicOrganization | null>(null);
const password = ref("");
const submitting = ref(false);
const loginError = ref<string | null>(null);

onMounted(async () => {
  await store.loadOrganizations();
  const requestedId = Number(route.query.organizationId);
  selected.value = store.organizations.find((organization) => organization.id === requestedId) ?? null;
});

async function selectOrganization(organization: PublicOrganization): Promise<void> {
  if (store.hasAccess(organization.id)) {
    store.setActiveOrganization(organization.id);
    await router.push({ name: "songs", params: { organizationId: organization.id } });
    return;
  }
  selected.value = organization;
  password.value = "";
  loginError.value = null;
}

async function login(): Promise<void> {
  if (!selected.value) return;
  submitting.value = true;
  loginError.value = null;
  try {
    await store.login(selected.value.id, password.value);
    const redirect = typeof route.query.redirect === "string"
      ? route.query.redirect
      : `/org/${selected.value.id}/songs`;
    await router.replace(redirect);
  } catch (error) {
    loginError.value = error instanceof ApiError && error.status === 401
      ? "Das User-Passwort ist falsch."
      : error instanceof Error ? error.message : "Die Anmeldung ist fehlgeschlagen.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section>
    <div class="page-header">
      <div><p class="eyebrow">TeamTracks</p><h1>Organisation auswählen</h1><p class="muted">Wähle eine Organisation, um auf deren Songs zuzugreifen.</p></div>
    </div>
    <p v-if="store.loading" class="muted">Organisationen werden geladen...</p>
    <p v-else-if="store.error" class="error-text">{{ store.error }}</p>
    <div v-else class="organization-grid">
      <button
        v-for="organization in store.organizations"
        :key="organization.id"
        class="organization-card panel"
        type="button"
        @click="selectOrganization(organization)"
      >
        <img :src="resolveApiUrl(organization.imageUrl)" :alt="organization.name" />
        <strong>{{ organization.name }}</strong>
      </button>
    </div>

    <section v-if="selected" class="auth-panel panel">
      <p class="eyebrow">{{ selected.name }}</p><h2>Organisation öffnen</h2>
      <form class="stack-form" @submit.prevent="login">
        <label>User-Passwort<input v-model="password" type="password" required autofocus /></label>
        <p v-if="loginError" class="error-text">{{ loginError }}</p>
        <button class="button button-primary" :disabled="submitting">{{ submitting ? "Anmeldung..." : "Anmelden" }}</button>
      </form>
    </section>
    <p v-if="store.sessionOrganizations.length === 0" class="platform-login-link">
      <RouterLink to="/platform/login">Plattformverwaltung</RouterLink>
    </p>
  </section>
</template>
