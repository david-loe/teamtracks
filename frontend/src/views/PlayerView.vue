<script setup lang="ts">
import { computed, onUnmounted, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import type { LocationQueryValue } from "vue-router";

import LoadingProgress from "@/components/LoadingProgress.vue";
import StemMixer from "@/components/StemMixer.vue";
import { useOrganizationsStore } from "@/stores/organizations";
import { usePlayerStore } from "@/stores/player";
import { formatDuration } from "@/types/format";
import { formatSongKey } from "@/types/keys";

const props = defineProps<{
  organizationId: string;
  id: string;
}>();

const organizationId = computed(() => Number(props.organizationId));
const songId = computed(() => Number(props.id));
const playerStore = usePlayerStore();
const organizationsStore = useOrganizationsStore();
const route = useRoute();
const router = useRouter();
let handlingAccessError = false;

const seekValue = computed(() => playerStore.currentTimeSeconds);

onUnmounted(() => {
  playerStore.reset();
});

watch(
  [organizationId, songId, () => route.query.key],
  ([nextOrganizationId, nextSongId, rawKey]) => {
    void loadPage(nextOrganizationId, nextSongId, rawKey);
  },
  { immediate: true },
);

watch(
  () => playerStore.accessErrorStatus,
  (status) => {
    if ((status === 401 || status === 403) && !handlingAccessError) {
      void handleAccessError();
    }
  },
);

watch(
  () => playerStore.manifest,
  (nextManifest) => {
    const parsedKey = parseRouteKey(route.query.key);
    if (nextManifest && parsedKey.valid && parsedKey.key === nextManifest.song.originalKey) {
      void replaceKeyQuery(null);
    }
  },
);

async function loadPage(
  nextOrganizationId: number,
  nextSongId: number,
  rawKey: LocationQueryValue | LocationQueryValue[] | undefined,
): Promise<void> {
  if (!Number.isFinite(nextOrganizationId) || !Number.isFinite(nextSongId)) {
    return;
  }

  const parsedKey = parseRouteKey(rawKey);
  if (!parsedKey.valid) {
    await replaceKeyQuery(null);
    return;
  }

  await playerStore.load(nextOrganizationId, nextSongId, parsedKey.key);
}

async function handleAccessError(): Promise<void> {
  handlingAccessError = true;
  const deniedOrganizationId = organizationId.value;
  const redirect = route.fullPath;
  playerStore.reset();
  try {
    await organizationsStore.refreshSession();
  } catch {
    // Die Auswahlseite kann auch ohne wiederherstellbare Browser-Session laden.
  }
  await router.replace({
    name: "organizations",
    query: { organizationId: String(deniedOrganizationId), redirect },
  });
}

function seek(event: Event): void {
  playerStore.seek(Number((event.target as HTMLInputElement).value));
}

function selectKey(event: Event): void {
  const key = Number((event.target as HTMLSelectElement).value);
  const originalKey = playerStore.manifest?.song.originalKey;
  void router.push({
    query: queryWithKey(key === originalKey ? null : key),
  });
}

function selectFocus(event: Event): void {
  const value = (event.target as HTMLSelectElement).value;
  playerStore.setFocusStem(value ? Number(value) : null);
}

function togglePlayback(): void {
  if (playerStore.playbackState === "playing") {
    playerStore.pause();
    return;
  }
  void playerStore.play();
}

function keyForVariant(semitoneOffset: number): number {
  const originalKey = playerStore.manifest?.song.originalKey ?? 0;
  return (originalKey + semitoneOffset) % 12;
}

function parseRouteKey(rawKey: LocationQueryValue | LocationQueryValue[] | undefined):
  | { valid: true; key: number | null }
  | { valid: false } {
  if (rawKey === undefined) {
    return { valid: true, key: null };
  }
  if (typeof rawKey !== "string" || !/^(?:0|[1-9]|1[01])$/.test(rawKey)) {
    return { valid: false };
  }
  return { valid: true, key: Number(rawKey) };
}

function queryWithKey(key: number | null) {
  const query = { ...route.query };
  if (key === null) {
    delete query.key;
  } else {
    query.key = String(key);
  }
  return query;
}

async function replaceKeyQuery(key: number | null): Promise<void> {
  await router.replace({ query: queryWithKey(key) });
}
</script>

<template>
  <section>
    <div class="page-header">
      <div>
        <p class="eyebrow">Song {{ id }}</p>
        <h1>{{ playerStore.manifest?.song.title ?? "Player" }}</h1>
        <p class="muted">
          {{ playerStore.manifest?.song.artist || "Unbekannter Künstler" }} ·
          {{ formatDuration(playerStore.durationMs) }} · {{ playerStore.playableStems.length }} Stem(s)
        </p>
      </div>
      <div class="header-actions">
        <RouterLink class="button button-secondary" :to="`/org/${organizationId}/songs`">Zur Liste</RouterLink>
      </div>
    </div>

    <p v-if="playerStore.error" class="error-text">{{ playerStore.error }}</p>
    <div v-if="playerStore.loadError" class="activation-row">
      <p class="error-text">{{ playerStore.loadError }}</p>
      <button class="button button-secondary" type="button" :disabled="playerStore.loadingAudio" @click="playerStore.retryAudioLoad">
        Stems erneut laden
      </button>
    </div>
    <p v-if="playerStore.playbackError" class="error-text">{{ playerStore.playbackError }}</p>

    <section class="panel player-panel">
      <p v-if="playerStore.loadingManifest" class="muted">Manifest wird geladen...</p>

      <template v-else-if="playerStore.manifest">
        <div v-if="!playerStore.manifest.playable" class="empty-state">
          <h2>Nicht abspielbereit</h2>
          <p class="muted">Für die gewählte Tonart ist noch kein Stem abspielbereit.</p>
          <div class="status-list">
            <span
              v-for="stem in playerStore.manifest.stems"
              :key="stem.id"
              class="status-pill"
              :class="`status-${stem.status}`"
            >
              {{ stem.name }}: {{ stem.status }}
            </span>
          </div>
        </div>

        <template v-else>
          <div class="player-options">
            <label v-if="playerStore.keyVariants.length > 0">
              Tonart
              <select
                id="player-key"
                name="playerKey"
                :value="playerStore.selectedKey ?? ''"
                @change="selectKey"
              >
                <option
                  v-for="keyVariant in playerStore.keyVariants"
                  :key="keyVariant.id"
                  :value="keyForVariant(keyVariant.semitoneOffset)"
                  :disabled="!keyVariant.playable"
                >
                  {{ formatSongKey(keyForVariant(keyVariant.semitoneOffset)) }}{{ keyVariant.isOriginal ? " (Original)" : "" }}
                </option>
              </select>
            </label>

            <label>
              Fokus
              <select
                id="focus-stem"
                name="focusStem"
                :value="playerStore.focusedStemId ?? ''"
                :disabled="!playerStore.controlsEnabled"
                @change="selectFocus"
              >
                <option value="">Aus</option>
                <option v-for="stem in playerStore.focusableStems" :key="stem.id" :value="stem.id">{{ stem.name }}</option>
              </select>
            </label>
          </div>

          <div v-if="playerStore.unavailableStems.length > 0" class="partial-stems-notice">
            <p class="muted">In dieser Tonart nicht verfügbare Stems:</p>
            <div class="status-list">
              <span
                v-for="stem in playerStore.unavailableStems"
                :key="stem.id"
                class="status-pill"
              >
                {{ stem.name }}
              </span>
            </div>
          </div>

          <LoadingProgress
            v-if="playerStore.audioLoadPhase"
            :stems="playerStore.playableStems"
            :progress="playerStore.loadProgress"
            :percent="playerStore.loadProgressPercent"
            :phase="playerStore.audioLoadPhase"
          />

          <div class="transport">
            <div class="transport-buttons">
              <button
                class="button button-primary"
                type="button"
                :disabled="!playerStore.controlsEnabled || playerStore.startingPlayback"
                @click="togglePlayback"
              >
                {{ playerStore.startingPlayback ? "Audio wird gestartet..." : playerStore.playbackState === "playing" ? "Pause" : "Play" }}
              </button>
              <button
                class="button button-secondary stop-button"
                type="button"
                :disabled="!playerStore.controlsEnabled"
                @click="playerStore.stop"
              >
                Stop
              </button>
            </div>

            <label class="seek-control">
              <span>{{ formatDuration(playerStore.currentTimeSeconds * 1000) }}</span>
              <input
                type="range"
                min="0"
                :max="playerStore.durationSeconds"
                step="0.1"
                :value="seekValue"
                :disabled="!playerStore.controlsEnabled"
                @input="seek"
              />
              <span>{{ formatDuration(playerStore.durationMs) }}</span>
            </label>
          </div>
        </template>
      </template>

      <p v-else class="muted">Noch kein Manifest geladen.</p>
    </section>

    <section v-if="playerStore.manifest?.playable" class="panel mixer-panel section-block">
      <h2>Mixer</h2>
      <StemMixer
        :stems="playerStore.playableStems"
        :muted="playerStore.mutedStems"
        :gains="playerStore.stemGains"
        :disabled="!playerStore.controlsEnabled"
        :min-gain-db="playerStore.playerSettings.stemGainMinDb"
        :max-gain-db="playerStore.playerSettings.stemGainMaxDb"
        :step-gain-db="playerStore.playerSettings.stemGainStepDb"
        @set-muted="playerStore.setStemMuted"
        @set-gain="playerStore.setStemGain"
      />
    </section>
  </section>
</template>
