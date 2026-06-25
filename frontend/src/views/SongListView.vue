<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import type { SongListItem } from "@/api/songs";
import { listPublicSongs } from "@/api/songs";
import { formatDuration } from "@/types/format";

const props = defineProps<{ organizationId: string }>();
const organizationId = Number(props.organizationId);
const songs = ref<SongListItem[]>([]);
const query = ref("");
const loading = ref(false);
const error = ref<string | null>(null);

onMounted(() => void search());
async function search(): Promise<void> {
  loading.value = true;
  error.value = null;
  try { songs.value = await listPublicSongs(organizationId, query.value); }
  catch (err) { error.value = err instanceof Error ? err.message : "Songs konnten nicht geladen werden."; }
  finally { loading.value = false; }
}
</script>

<template>
  <section>
    <div class="page-header"><div><p class="eyebrow">TeamTracks</p><h1>Songs</h1><p class="muted">Abspielbereite Songs suchen und öffnen.</p></div></div>
    <section class="panel">
      <form class="search-form" @submit.prevent="search"><input v-model="query" type="search" placeholder="Titel, Künstler, Slug oder Beschreibung" /><button class="button button-primary" :disabled="loading">Suchen</button></form>
      <p v-if="error" class="error-text">{{ error }}</p>
      <p v-if="loading" class="muted">Songs werden geladen...</p>
      <p v-else-if="songs.length === 0" class="muted">Keine abspielbereiten Songs gefunden.</p>
      <div v-else class="public-song-list section-block">
        <RouterLink v-for="song in songs" :key="song.id" class="song-card" :to="`/org/${organizationId}/songs/${song.id}`">
          <div><strong>{{ song.title }}</strong><span class="table-subtext">{{ song.artist || "Unbekannter Künstler" }} · {{ song.slug }}</span></div>
          <span>{{ formatDuration(song.durationMs) }}</span>
        </RouterLink>
      </div>
    </section>
  </section>
</template>
