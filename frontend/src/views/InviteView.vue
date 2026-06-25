<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { useOrganizationsStore } from "@/stores/organizations";

const props = defineProps<{ token: string }>();
const router = useRouter();
const store = useOrganizationsStore();
const error = ref<string | null>(null);

onMounted(async () => {
  try {
    const organizationId = await store.acceptInvitation(props.token);
    await router.replace({ name: "songs", params: { organizationId } });
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "Einladung ist ungültig.";
  }
});
</script>

<template>
  <section class="auth-panel panel">
    <p class="eyebrow">Einladung</p>
    <h1>{{ error ? "Einladung ungültig" : "Einladung wird angenommen..." }}</h1>
    <p v-if="error" class="error-text">{{ error }}</p>
  </section>
</template>
