<script setup lang="ts">
import type { StemLoadProgress } from "@/audio/AudioEngine";
import type { AudioLoadPhase } from "@/stores/player";
import type { PlayableStemManifestItem } from "@/types/manifest";

defineProps<{
  stems: PlayableStemManifestItem[];
  progress: Record<number, StemLoadProgress>;
  percent: number;
  phase: AudioLoadPhase;
}>();
</script>

<template>
  <div class="loading-progress">
    <div class="progress-header">
      <strong v-if="phase === 'downloading'">Stems laden</strong>
      <strong v-else>Stems werden dekodiert…</strong>
      <span v-if="phase === 'downloading'">{{ percent }}%</span>
    </div>
    <div v-if="phase === 'downloading'" class="progress-bar" aria-hidden="true">
      <span :style="{ width: `${percent}%` }"></span>
    </div>
    <div v-if="phase === 'downloading'" class="progress-list">
      <div v-for="stem in stems" :key="stem.id" class="progress-row">
        <span>{{ stem.name }}</span>
        <span>{{ Math.round((progress[stem.id]?.ratio ?? 0) * 100) }}%</span>
      </div>
    </div>
  </div>
</template>
