<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from "vue";
import { RouterLink } from "vue-router";

import FocusControls from "@/components/FocusControls.vue";
import LoadingProgress from "@/components/LoadingProgress.vue";
import StemMixer from "@/components/StemMixer.vue";
import { usePlayerStore } from "@/stores/player";
import { formatDuration } from "@/types/format";

const props = defineProps<{
  id: string;
}>();

const songId = computed(() => Number(props.id));
const playerStore = usePlayerStore();

const seekValue = computed(() => playerStore.currentTimeSeconds);

onMounted(() => {
  void loadPage();
});

onUnmounted(() => {
  playerStore.reset();
});

watch(songId, () => {
  void loadPage();
});

async function loadPage(): Promise<void> {
  if (!Number.isFinite(songId.value)) {
    return;
  }
  await playerStore.load(songId.value);
}

function seek(event: Event): void {
  playerStore.seek(Number((event.target as HTMLInputElement).value));
}
</script>

<template>
  <section>
    <div class="page-header">
      <div>
        <p class="eyebrow">Song {{ id }}</p>
        <h1>{{ playerStore.manifest?.song.title ?? "Player" }}</h1>
        <p class="muted">{{ formatDuration(playerStore.durationMs) }} · {{ playerStore.playableStems.length }} Stem(s)</p>
      </div>
      <div class="header-actions">
        <RouterLink class="button button-secondary" to="/songs">Zur Liste</RouterLink>
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
          <p class="muted">Der Song braucht ein vollständiges Manifest mit ausschließlich bereiten Stems.</p>
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
          <LoadingProgress
            v-if="playerStore.loadingAudio || playerStore.loadProgressPercent > 0"
            :stems="playerStore.playableStems"
            :progress="playerStore.loadProgress"
            :percent="playerStore.loadProgressPercent"
          />

          <div class="transport">
            <div class="transport-buttons">
              <button
                class="button button-primary"
                type="button"
                :disabled="!playerStore.controlsEnabled || playerStore.startingPlayback || playerStore.playbackState === 'playing'"
                @click="playerStore.play"
              >
                {{ playerStore.startingPlayback ? "Audio wird gestartet..." : "Play" }}
              </button>
              <button
                class="button button-secondary"
                type="button"
                :disabled="!playerStore.controlsEnabled || playerStore.playbackState !== 'playing'"
                @click="playerStore.pause"
              >
                Pause
              </button>
              <button
                class="button button-secondary"
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

    <div v-if="playerStore.manifest?.playable" class="layout-grid section-block">
      <section class="panel">
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

      <section class="panel">
        <h2>Fokus</h2>
        <FocusControls
          :stems="playerStore.playableStems"
          :selected-stem-id="playerStore.focusedStemId"
          :focused-gain-db="playerStore.focusedGainDb"
          :background-gain-db="playerStore.backgroundGainDb"
          :disabled="!playerStore.controlsEnabled"
          :settings="playerStore.playerSettings"
          @set-focus-stem="playerStore.setFocusStem"
          @set-focus-gains="playerStore.setFocusGains"
        />
      </section>
    </div>
  </section>
</template>
