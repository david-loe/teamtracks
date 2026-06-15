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
      <div>
        <strong>{{ stem.name }}</strong>
        <span class="table-subtext">{{ stem.role }} · {{ stem.channels ?? "n/a" }} ch</span>
      </div>
      <label class="inline-control">
        <input
          :id="`stem-${stem.id}-muted`"
          :name="`stem-${stem.id}-muted`"
          type="checkbox"
          :checked="muted[stem.id] ?? false"
          :disabled="disabled"
          @change="$emit('setMuted', stem.id, ($event.target as HTMLInputElement).checked)"
        />
        Mute
      </label>
      <label class="gain-control">
        <span>{{ gains[stem.id] ?? 0 }} dB</span>
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
