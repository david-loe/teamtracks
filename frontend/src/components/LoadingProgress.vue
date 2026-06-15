<script setup lang="ts">
import type { StemLoadProgress } from "@/audio/AudioEngine";
import type { PlayableStemManifestItem } from "@/types/manifest";

defineProps<{
  stems: PlayableStemManifestItem[];
  progress: Record<number, StemLoadProgress>;
  percent: number;
}>();
</script>

<template>
  <div class="loading-progress">
    <div class="progress-header">
      <strong>Stems laden</strong>
      <span>{{ percent }}%</span>
    </div>
    <div class="progress-bar" aria-hidden="true">
      <span :style="{ width: `${percent}%` }"></span>
    </div>
    <div class="progress-list">
      <div v-for="stem in stems" :key="stem.id" class="progress-row">
        <span>{{ stem.name }}</span>
        <span>{{ Math.round((progress[stem.id]?.ratio ?? 0) * 100) }}%</span>
      </div>
    </div>
  </div>
</template>
