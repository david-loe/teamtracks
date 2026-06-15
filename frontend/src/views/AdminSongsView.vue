<script setup lang="ts">
import { onMounted, reactive } from "vue";
import { useRouter } from "vue-router";

import SongList from "@/components/SongList.vue";
import { useSongsStore } from "@/stores/songs";
import { SONG_KEYS } from "@/types/keys";

const router = useRouter();
const songsStore = useSongsStore();
const form = reactive({ title: "", artist: "", slug: "", description: "", originalKey: 0 });

onMounted(() => void songsStore.fetchSongs());

async function createSong(): Promise<void> {
  const song = await songsStore.createSong({
    title: form.title.trim(),
    artist: form.artist.trim(),
    slug: form.slug.trim(),
    description: form.description.trim() || null,
    originalKey: form.originalKey,
  });
  if (song) {
    form.title = "";
    form.artist = "";
    form.slug = "";
    form.description = "";
    form.originalKey = 0;
    await router.push(`/admin/songs/${song.id}`);
  }
}

function slugFromTitle(): void {
  if (form.slug.trim()) return;
  form.slug = form.title.toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

async function deleteSong(songId: number): Promise<void> {
  if (window.confirm("Song inklusive Stems und Dateien löschen?")) await songsStore.deleteSong(songId);
}
</script>

<template>
  <section>
    <div class="page-header"><div><p class="eyebrow">Admin</p><h1>Songs verwalten</h1><p class="muted">Songs anlegen, bearbeiten und konvertieren.</p></div></div>
    <div class="layout-grid">
      <section class="panel">
        <h2>Neuer Song</h2>
        <form class="stack-form" autocomplete="off" @submit.prevent="createSong">
          <label for="song-title">Titel</label><input id="song-title" v-model="form.title" name="title" maxlength="200" required @blur="slugFromTitle" />
          <label for="song-artist">Künstler</label><input id="song-artist" v-model="form.artist" name="artist" maxlength="200" />
          <label for="song-slug">Slug</label><input id="song-slug" v-model="form.slug" name="slug" pattern="[a-z0-9]+(?:-[a-z0-9]+)*" maxlength="200" required />
          <label for="song-original-key">Originaltonart</label>
          <select id="song-original-key" v-model="form.originalKey" name="originalKey">
            <option v-for="songKey in SONG_KEYS" :key="songKey.value" :value="songKey.value">{{ songKey.label }}</option>
          </select>
          <label for="song-description">Beschreibung</label><textarea id="song-description" v-model="form.description" name="description" rows="4" />
          <button class="button button-primary" :disabled="songsStore.saving">{{ songsStore.saving ? "Wird angelegt..." : "Song anlegen" }}</button>
        </form>
      </section>
      <section class="panel">
        <div class="section-heading"><h2>Songliste</h2><button class="button button-secondary" :disabled="songsStore.loading" @click="songsStore.fetchSongs">Aktualisieren</button></div>
        <p v-if="songsStore.error" class="error-text">{{ songsStore.error }}</p>
        <p v-if="songsStore.loading" class="muted">Songs werden geladen...</p>
        <p v-else-if="!songsStore.hasSongs" class="muted">Noch keine Songs vorhanden.</p>
        <SongList v-else :songs="songsStore.songs" :deleting-id="songsStore.deletingId" @delete="deleteSong" />
      </section>
    </div>
  </section>
</template>
