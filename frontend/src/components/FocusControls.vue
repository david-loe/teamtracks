<script setup lang="ts">
import type { PlayableStemManifestItem } from "@/types/manifest";
import type { PlayerSettings } from "@/types/manifest";

const props = defineProps<{
  stems: PlayableStemManifestItem[];
  selectedStemId: number | null;
  focusedGainDb: number;
  backgroundGainDb: number;
  disabled: boolean;
  settings: PlayerSettings;
}>();

const emit = defineEmits<{
  setFocusStem: [stemId: number | null];
  setFocusGains: [focusedGainDb: number, backgroundGainDb: number];
}>();

function updateFocusedGain(value: string): void {
  emit("setFocusGains", Number(value), props.backgroundGainDb);
}

function updateBackgroundGain(value: string): void {
  emit("setFocusGains", props.focusedGainDb, Number(value));
}
</script>

<template>
  <div class="focus-controls">
    <label>
      Fokus
      <select
        id="focus-stem"
        name="focusStem"
        :value="selectedStemId ?? ''"
        :disabled="disabled"
        @change="$emit('setFocusStem', ($event.target as HTMLSelectElement).value ? Number(($event.target as HTMLSelectElement).value) : null)"
      >
        <option value="">Aus</option>
        <option v-for="stem in stems" :key="stem.id" :value="stem.id">{{ stem.name }}</option>
      </select>
    </label>

    <label>
      Fokus-Gain {{ focusedGainDb }} dB
      <input
        id="focus-gain"
        name="focusGainDb"
        type="range"
        :min="settings.focusGainMinDb"
        :max="settings.focusGainMaxDb"
        step="1"
        :value="focusedGainDb"
        :disabled="disabled"
        @input="updateFocusedGain(($event.target as HTMLInputElement).value)"
      />
    </label>

    <label>
      Hintergrund {{ backgroundGainDb }} dB
      <input
        id="background-gain"
        name="backgroundGainDb"
        type="range"
        :min="settings.backgroundGainMinDb"
        :max="settings.backgroundGainMaxDb"
        step="1"
        :value="backgroundGainDb"
        :disabled="disabled"
        @input="updateBackgroundGain(($event.target as HTMLInputElement).value)"
      />
    </label>
  </div>
</template>
