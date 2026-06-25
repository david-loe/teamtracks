<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError } from "@/api/client";
import { useOrganizationsStore } from "@/stores/organizations";

const props = defineProps<{ organizationId: string }>();

const route = useRoute();
const router = useRouter();
const organizationsStore = useOrganizationsStore();
const password = ref("");
const submitting = ref(false);
const error = ref<string | null>(null);

async function submit(): Promise<void> {
  submitting.value = true;
  error.value = null;
  try {
    const organizationId = Number(props.organizationId);
    await organizationsStore.loginAdmin(organizationId, password.value);
    const redirect = typeof route.query.redirect === "string"
      ? route.query.redirect
      : `/org/${organizationId}/admin/songs`;
    await router.replace(redirect);
  } catch (err) {
    error.value = err instanceof ApiError && err.status === 401
      ? "Das Admin-Passwort ist falsch."
      : err instanceof Error ? err.message : "Die Anmeldung ist fehlgeschlagen.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <section class="auth-panel panel">
    <p class="eyebrow">Admin</p><h1>Anmelden</h1>
    <p class="muted">Der Organisations-Adminbereich ist separat passwortgeschützt.</p>
    <form class="stack-form section-block" @submit.prevent="submit">
      <label for="admin-password">Passwort</label>
      <input id="admin-password" v-model="password" name="password" type="password" autocomplete="current-password" required autofocus />
      <p v-if="error" class="error-text">{{ error }}</p>
      <button class="button button-primary" :disabled="submitting">{{ submitting ? "Anmeldung..." : "Anmelden" }}</button>
    </form>
  </section>
</template>
