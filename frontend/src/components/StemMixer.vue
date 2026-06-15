<script setup lang="ts">
import type { PlayableStemManifestItem } from "@/types/manifest";

defineProps<{
  stems: PlayableStemManifestItem[];
  muted: Record<number, boolean>;
  gains: Record<number, number>;
  disabled: boolean;
  minGainDb: number;
  maxGainDb: number;
  stepGainDb: number;
}>();

defineEmits<{
  setMuted: [stemId: number, muted: boolean];
  setGain: [stemId: number, gainDb: number];
}>();
</script>

<template>
  <div class="mixer-list">
    <div v-for="stem in stems" :key="stem.id" class="mixer-row">
      <div class="stem-summary">
        <strong>{{ stem.name }}</strong>
        <span class="table-subtext">{{ stem.role }}</span>
      </div>
      <button
        :id="`stem-${stem.id}-muted`"
        class="mute-button"
        :class="{ 'is-muted': muted[stem.id] ?? false }"
        type="button"
        :aria-pressed="muted[stem.id] ?? false"
        :disabled="disabled"
        @click="$emit('setMuted', stem.id, !(muted[stem.id] ?? false))"
      >
        Mute
      </button>
      <label class="gain-control">
        <span>Gain <strong>{{ gains[stem.id] ?? 0 }} dB</strong></span>
        <input
          :id="`stem-${stem.id}-gain`"
          :name="`stem-${stem.id}-gain`"
          type="range"
          :min="minGainDb"
          :max="maxGainDb"
          :step="stepGainDb"
          :value="gains[stem.id] ?? 0"
          :disabled="disabled"
          @input="$emit('setGain', stem.id, Number(($event.target as HTMLInputElement).value))"
        />
      </label>
    </div>
  </div>
</template>
