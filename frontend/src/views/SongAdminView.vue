<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from "vue";
import { RouterLink } from "vue-router";

import ConversionStatus from "@/components/ConversionStatus.vue";
import StemImport from "@/components/StemImport.vue";
import StemUpload from "@/components/StemUpload.vue";
import { useAdminStemsStore } from "@/stores/adminStems";
import { useSongsStore } from "@/stores/songs";
import { formatBytes, formatDuration } from "@/types/format";

const props = defineProps<{
  id: string;
}>();

const songId = computed(() => Number(props.id));
const songsStore = useSongsStore();
const stemsStore = useAdminStemsStore();

onMounted(() => {
  void loadPage();
});

onUnmounted(() => {
  stemsStore.reset();
});

watch(songId, () => {
  void loadPage();
});

async function loadPage(): Promise<void> {
  if (!Number.isFinite(songId.value)) {
    return;
  }

  await Promise.all([
    songsStore.fetchSong(songId.value),
    stemsStore.load(songId.value),
    stemsStore.loadJobs(songId.value),
  ]);
}

async function uploadStem(payload: Parameters<typeof stemsStore.upload>[1]): Promise<void> {
  await stemsStore.upload(songId.value, payload);
}

async function importStem(payload: Parameters<typeof stemsStore.importFromSource>[1]): Promise<void> {
  await stemsStore.importFromSource(songId.value, payload);
}

async function deleteStem(stemId: number): Promise<void> {
  if (!window.confirm("Stem inklusive Quelldatei und konvertierter Datei löschen?")) {
    return;
  }

  await stemsStore.removeStem(stemId);
}
</script>

<template>
  <section>
    <div class="page-header">
      <div>
        <p class="eyebrow">Song {{ id }}</p>
        <h1>{{ songsStore.currentSong?.title ?? "Stem-Verwaltung" }}</h1>
        <p class="muted">WAV-Stems hochladen oder importieren und Conversion-Jobs starten.</p>
      </div>
      <div class="header-actions">
        <RouterLink class="button button-secondary" to="/admin/songs">Zur Liste</RouterLink>
        <RouterLink v-if="songsStore.currentSong?.status === 'ready'" class="button button-secondary" :to="`/songs/${id}`">Player</RouterLink>
      </div>
    </div>

    <div class="layout-grid">
      <section class="panel">
        <h2>Upload</h2>
        <StemUpload :disabled="stemsStore.uploading" @submit="uploadStem" />
      </section>

      <section class="panel">
        <h2>Import aus SOURCE_ROOT</h2>
        <StemImport :disabled="stemsStore.importing" @submit="importStem" />
      </section>
    </div>

    <p v-if="songsStore.error" class="error-text">{{ songsStore.error }}</p>
    <p v-if="stemsStore.error" class="error-text">{{ stemsStore.error }}</p>

    <section class="panel section-block">
      <div class="section-heading">
        <h2>Stems</h2>
        <button class="button button-secondary" type="button" :disabled="stemsStore.loading" @click="stemsStore.load(songId)">
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
          @click="stemsStore.startConversion(songId)"
        >
          {{ stemsStore.startingConversion ? "Wird gestartet..." : "Conversion starten" }}
        </button>
        <button
          class="button button-secondary"
          type="button"
          :disabled="stemsStore.startingConversion || stemsStore.stems.length === 0"
          @click="stemsStore.reconvert(songId)"
        >
          Neu konvertieren
        </button>
      </div>
      <p v-if="stemsStore.jobError" class="error-text">{{ stemsStore.jobError }}</p>
      <p v-if="stemsStore.hasActiveJobs" class="muted">Aktive Jobs werden automatisch aktualisiert.</p>
      <ConversionStatus :jobs="stemsStore.jobs" :loading="stemsStore.loadingJobs" />
    </section>
  </section>
</template>
