<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { logout } from "@/api/auth";

const route = useRoute();
const router = useRouter();
const adminArea = computed(() => Boolean(route.meta.admin || route.meta.adminLogin));
async function signOut(): Promise<void> { await logout(); await router.push("/songs"); }
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink class="brand" :to="adminArea ? '/admin/songs' : '/songs'">TeamTracks</RouterLink>
      <nav v-if="adminArea && route.meta.admin" class="nav"><RouterLink to="/admin/songs">Songs</RouterLink><RouterLink to="/admin/settings">Einstellungen</RouterLink><button class="nav-button" @click="signOut">Logout</button></nav>
      <nav v-else class="nav"><RouterLink to="/songs">Songs</RouterLink><RouterLink to="/settings">Einstellungen</RouterLink><RouterLink to="/admin/login">Admin</RouterLink></nav>
    </header>

    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>
