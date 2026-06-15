<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { login } from "@/api/auth";
import { ApiError } from "@/api/client";

const route = useRoute();
const router = useRouter();
const password = ref("");
const submitting = ref(false);
const error = ref<string | null>(null);

async function submit(): Promise<void> {
  submitting.value = true;
  error.value = null;
  try {
    await login(password.value);
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/admin/songs";
    await router.replace(redirect);
  } catch (err) {
    error.value = err instanceof ApiError && err.status === 401
      ? "Falsches Passwort."
      : err instanceof Error ? err.message : "Anmeldung fehlgeschlagen.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="auth-panel panel">
    <p class="eyebrow">Admin</p><h1>Anmelden</h1>
    <p class="muted">Der Verwaltungsbereich ist passwortgeschützt.</p>
    <form class="stack-form section-block" @submit.prevent="submit">
      <label for="admin-password">Passwort</label>
      <input id="admin-password" v-model="password" name="password" type="password" autocomplete="current-password" required autofocus />
      <p v-if="error" class="error-text">{{ error }}</p>
      <button class="button button-primary" :disabled="submitting">{{ submitting ? "Anmeldung..." : "Anmelden" }}</button>
    </form>
  </section>
</template>
