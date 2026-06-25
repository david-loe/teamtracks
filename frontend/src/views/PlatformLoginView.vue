<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ApiError } from "@/api/client";
import { usePlatformStore } from "@/stores/platform";

const route = useRoute();
const router = useRouter();
const platformStore = usePlatformStore();
const password = ref("");
const submitting = ref(false);
const error = ref<string | null>(null);

async function submit(): Promise<void> {
  submitting.value = true;
  error.value = null;
  try {
    await platformStore.login(password.value);
    const redirect = typeof route.query.redirect === "string"
      ? route.query.redirect
      : "/platform/organizations";
    await router.replace(redirect);
  } catch (err) {
    error.value = err instanceof ApiError && err.status === 401
      ? "Das Plattform-Admin-Passwort ist falsch."
      : err instanceof Error ? err.message : "Die Anmeldung ist fehlgeschlagen.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="auth-panel panel">
    <p class="eyebrow">Plattformverwaltung</p>
    <h1>Anmelden</h1>
    <p class="muted">Dieser Bereich verwaltet alle Organisationen und ist separat geschützt.</p>
    <form class="stack-form section-block" @submit.prevent="submit">
      <label>
        Plattform-Admin-Passwort
        <input v-model="password" type="password" autocomplete="current-password" required autofocus />
      </label>
      <p v-if="error" class="error-text">{{ error }}</p>
      <button class="button button-primary" :disabled="submitting">
        {{ submitting ? "Anmeldung läuft..." : "Anmelden" }}
      </button>
    </form>
  </section>
</template>
