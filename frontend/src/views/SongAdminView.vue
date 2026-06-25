<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import ConversionStatus from "@/components/ConversionStatus.vue";
import StemUpload from "@/components/StemUpload.vue";
import type { StemKeyAssetVariant } from "@/api/transposition";
import { useAdminStemsStore } from "@/stores/adminStems";
import { useSongsStore } from "@/stores/songs";
import { formatBytes, formatDuration } from "@/types/format";
import { formatSongKey, SONG_KEYS } from "@/types/keys";

const props = defineProps<{
  organizationId: string;
  id: string;
}>();

const organizationId = computed(() => Number(props.organizationId));
const songId = computed(() => Number(props.id));
const songsStore = useSongsStore();
const stemsStore = useAdminStemsStore();
const targetKeys = ref<number[]>([]);
const editForm = reactive({ title: "", artist: "", originalKey: 0 });
const keyAssetsByStemId = computed(() =>
  new Map(stemsStore.keyAssets.map((item) => [item.stemId, item.variants])),
);

onMounted(() => {
  void loadPage();
});

onUnmounted(() => {
  stemsStore.reset();
});

watch(songId, () => {
  void loadPage();
});

watch(
  () => songsStore.currentSong,
  (song) => {
    editForm.title = song?.title ?? "";
    editForm.artist = song?.artist ?? "";
    editForm.originalKey = song?.originalKey ?? 0;
  },
  { immediate: true },
);

async function loadPage(): Promise<void> {
  if (!Number.isFinite(songId.value)) {
    return;
  }

  await Promise.all([
    songsStore.fetchSong(organizationId.value, songId.value),
    stemsStore.load(organizationId.value, songId.value),
    stemsStore.loadJobs(organizationId.value, songId.value),
    stemsStore.loadKeyAssets(organizationId.value, songId.value),
  ]);
}

async function uploadStems(payload: Parameters<typeof stemsStore.uploadMany>[2]) {
  return stemsStore.uploadMany(organizationId.value, songId.value, payload);
}

async function deleteStem(stemId: number): Promise<void> {
  if (!window.confirm("Stem inklusive Quelldatei und konvertierter Datei löschen?")) {
    return;
  }

  await stemsStore.removeStem(organizationId.value, stemId);
}

async function transposeSong(): Promise<void> {
  if (targetKeys.value.length === 0) {
    return;
  }
  const ok = await stemsStore.transpose(organizationId.value, songId.value, targetKeys.value);
  if (ok) {
    targetKeys.value = [];
    await songsStore.fetchSong(organizationId.value, songId.value);
  }
}

async function saveSongDetails(): Promise<void> {
  if (!songsStore.currentSong) {
    return;
  }
  await songsStore.updateSong(organizationId.value, songId.value, {
    title: editForm.title.trim(),
    artist: editForm.artist.trim(),
    originalKey: editForm.originalKey,
  });
  await stemsStore.loadKeyAssets(organizationId.value, songId.value);
}

function variantsForStem(stemId: number): StemKeyAssetVariant[] {
  return keyAssetsByStemId.value.get(stemId) ?? [];
}
</script>

<template>
  <section>
    <div class="page-header">
      <div>
        <p class="eyebrow">Song {{ id }}</p>
        <h1>{{ songsStore.currentSong?.title ?? "Stem-Verwaltung" }}</h1>
        <p class="muted">
          {{ songsStore.currentSong?.artist || "Unbekannter Künstler" }} ·
          WAV-Stems hochladen und Conversion-Jobs starten.
          Originaltonart: {{ formatSongKey(songsStore.currentSong?.originalKey) }}
        </p>
      </div>
      <div class="header-actions">
        <RouterLink class="button button-secondary" :to="`/org/${organizationId}/admin/songs`">Zur Liste</RouterLink>
        <RouterLink v-if="songsStore.currentSong?.status === 'ready'" class="button button-secondary" :to="`/org/${organizationId}/songs/${id}`">Player</RouterLink>
      </div>
    </div>

    <div class="layout-grid">
      <section class="panel">
        <h2>Songdaten</h2>
        <form class="stack-form" autocomplete="off" @submit.prevent="saveSongDetails">
          <label for="edit-song-title">Titel</label>
          <input id="edit-song-title" v-model="editForm.title" name="title" maxlength="200" required />

          <label for="edit-song-artist">Künstler</label>
          <input id="edit-song-artist" v-model="editForm.artist" name="artist" maxlength="200" />

          <label for="edit-song-original-key">Originaltonart</label>
          <select id="edit-song-original-key" v-model="editForm.originalKey" name="originalKey">
            <option v-for="songKey in SONG_KEYS" :key="songKey.value" :value="songKey.value">{{ songKey.label }}</option>
          </select>

          <button class="button button-primary" type="submit" :disabled="songsStore.saving || !songsStore.currentSong">
            {{ songsStore.saving ? "Wird gespeichert..." : "Songdaten speichern" }}
          </button>
        </form>
      </section>

      <section class="panel">
        <h2>Upload</h2>
        <StemUpload
          v-if="songsStore.currentSong"
          :disabled="stemsStore.uploading"
          :original-key="songsStore.currentSong.originalKey"
          :upload="uploadStems"
        />
        <p v-else class="muted">Songdaten werden geladen...</p>
      </section>
    </div>

    <p v-if="songsStore.error" class="error-text">{{ songsStore.error }}</p>
    <p v-if="stemsStore.error" class="error-text">{{ stemsStore.error }}</p>

    <section class="panel section-block">
      <div class="section-heading">
        <h2>Stems</h2>
        <button class="button button-secondary" type="button" :disabled="stemsStore.loading" @click="stemsStore.load(organizationId, songId)">
          Aktualisieren
        </button>
      </div>

      <p v-if="stemsStore.loading" class="muted">Stems werden geladen...</p>
      <p v-else-if="stemsStore.stems.length === 0" class="muted">Noch keine Stems vorhanden.</p>
      <div v-else class="table-shell">
        <table class="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Rolle</th>
              <th>Status</th>
              <th>Tonart</th>
              <th>Vorhandene Tonarten</th>
              <th>Metadaten</th>
              <th class="actions-cell">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="stem in stemsStore.stems" :key="stem.id">
              <td>
                <strong>{{ stem.name }}</strong>
                <span class="table-subtext">{{ stem.sourceFilename ?? "keine Quelldatei" }}</span>
                <p v-if="stem.errorMessage" class="error-text">{{ stem.errorMessage }}</p>
              </td>
              <td>{{ stem.role }}</td>
              <td><span class="status-pill" :class="`status-${stem.status}`">{{ stem.status }}</span></td>
              <td>{{ formatSongKey(stem.key) }}</td>
              <td>
                <template v-if="stem.key !== null">
                  <span v-if="variantsForStem(stem.id).length === 0" class="table-subtext">keine</span>
                  <span v-else class="badge-row">
                    <span
                      v-for="variant in variantsForStem(stem.id)"
                      :key="`${stem.id}-${variant.songKeyId}`"
                      class="status-pill key-badge"
                      :class="`status-${variant.status}`"
                      :title="variant.errorMessage ?? undefined"
                    >
                      {{ formatSongKey(variant.targetKey) }}
                    </span>
                  </span>
                </template>
              </td>
              <td>
                <span class="table-subtext">
                  {{ formatDuration(stem.durationMs) }} · {{ stem.sampleRate ?? "n/a" }} Hz ·
                  {{ stem.channels ?? "n/a" }} ch · {{ formatBytes(stem.fileSizeBytes) }}
                </span>
              </td>
              <td class="actions-cell">
                <button
                  class="button button-danger"
                  type="button"
                  :disabled="stemsStore.deletingId === stem.id"
                  @click="deleteStem(stem.id)"
                >
                  Löschen
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel section-block">
      <div class="section-heading">
        <div>
          <h2>Conversion</h2>
          <p class="muted">{{ stemsStore.convertibleStems.length }} Stem(s) bereit für Conversion.</p>
        </div>
        <button
          class="button button-primary"
          type="button"
          :disabled="stemsStore.startingConversion || stemsStore.convertibleStems.length === 0"
          @click="stemsStore.startConversion(organizationId, songId)"
        >
          {{ stemsStore.startingConversion ? "Wird gestartet..." : "Conversion starten" }}
        </button>
        <button
          class="button button-secondary"
          type="button"
          :disabled="stemsStore.startingConversion || stemsStore.stems.length === 0"
          @click="stemsStore.reconvert(organizationId, songId)"
        >
          Neu konvertieren
        </button>
      </div>
      <p v-if="stemsStore.jobError" class="error-text">{{ stemsStore.jobError }}</p>
      <p v-if="stemsStore.hasActiveJobs" class="muted">Aktive Jobs werden automatisch aktualisiert.</p>
      <ConversionStatus :jobs="stemsStore.jobs" :loading="stemsStore.loadingJobs" />
    </section>

    <section class="panel section-block">
      <div class="section-heading">
        <div>
          <h2>Tonarten</h2>
          <p class="muted">Bereite Songs in weitere Tonarten transponieren.</p>
        </div>
        <button
          class="button button-primary"
          type="button"
          :disabled="stemsStore.transposing || songsStore.currentSong?.status !== 'ready' || targetKeys.length === 0"
          @click="transposeSong"
        >
          {{ stemsStore.transposing ? "Jobs werden angelegt..." : "Transponieren" }}
        </button>
      </div>
      <label>
        Zieltonarten
        <select id="transpose-target-keys" v-model="targetKeys" name="targetKeys" multiple :disabled="stemsStore.transposing || songsStore.currentSong?.status !== 'ready'">
          <option
            v-for="songKey in SONG_KEYS"
            :key="songKey.value"
            :value="songKey.value"
          >
            {{ songKey.label }}
          </option>
        </select>
      </label>
      <p class="muted">Mehrere Tonarten mit Shift/Ctrl auswählen. Die Originaltonart kann ebenfalls ausgewählt werden, um sie neu zu erzeugen.</p>
      <p v-if="stemsStore.transposeError" class="error-text">{{ stemsStore.transposeError }}</p>
    </section>
  </section>
</template>
