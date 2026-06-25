<script setup lang="ts">
import { onMounted, ref } from "vue";
import type { AppSettings } from "@/api/settings";
import { getSettings, updateSettings } from "@/api/settings";

const props = defineProps<{ organizationId: string }>();
const organizationId = Number(props.organizationId);
const settings = ref<AppSettings | null>(null);
const loading = ref(false);
const saving = ref(false);
const error = ref<string | null>(null);
const saved = ref(false);

onMounted(() => void load());
async function load(): Promise<void> {
  loading.value = true; error.value = null;
  try { settings.value = await getSettings(organizationId); }
  catch (err) { error.value = err instanceof Error ? err.message : "Einstellungen konnten nicht geladen werden."; }
  finally { loading.value = false; }
}
async function save(): Promise<void> {
  if (!settings.value) return;
  saving.value = true; error.value = null; saved.value = false;
  try { settings.value = await updateSettings(organizationId, settings.value); saved.value = true; }
  catch (err) { error.value = err instanceof Error ? err.message : "Einstellungen konnten nicht gespeichert werden."; }
  finally { saving.value = false; }
}
</script>

<template>
  <section>
    <div class="page-header"><div><p class="eyebrow">Admin</p><h1>Einstellungen</h1><p class="muted">Werte dieser Organisation für neue Conversion-Jobs und den Player.</p></div></div>
    <p v-if="loading" class="muted">Einstellungen werden geladen...</p>
    <form v-else-if="settings" class="settings-form" @submit.prevent="save">
      <section class="panel"><h2>Conversion</h2><div class="settings-grid">
        <label>Mono-Bitrate (kbit/s)<input v-model.number="settings.monoBitrateKbps" type="number" min="32" max="512" /></label>
        <label>Stereo-Bitrate (kbit/s)<input v-model.number="settings.stereoBitrateKbps" type="number" min="32" max="512" /></label>
        <label>Ziel-Samplerate<select v-model.number="settings.targetSampleRate"><option :value="44100">44100 Hz</option><option :value="48000">48000 Hz</option></select></label>
        <label>Dauer-Toleranz (ms)<input v-model.number="settings.durationToleranceMs" type="number" min="0" max="10000" /></label>
      </div></section>
      <section class="panel"><h2>Player</h2><div class="settings-grid">
        <label>Stem Standard (dB)<input v-model.number="settings.stemGainDefaultDb" type="number" /></label>
        <label>Stem Minimum (dB)<input v-model.number="settings.stemGainMinDb" type="number" /></label>
        <label>Stem Maximum (dB)<input v-model.number="settings.stemGainMaxDb" type="number" /></label>
        <label>Stem Schrittweite (dB)<input v-model.number="settings.stemGainStepDb" type="number" min="1" /></label>
        <label>Fokus Standard (dB)<input v-model.number="settings.focusGainDefaultDb" type="number" /></label>
        <label>Fokus Minimum (dB)<input v-model.number="settings.focusGainMinDb" type="number" /></label>
        <label>Fokus Maximum (dB)<input v-model.number="settings.focusGainMaxDb" type="number" /></label>
        <label>Hintergrund Standard (dB)<input v-model.number="settings.backgroundGainDefaultDb" type="number" /></label>
        <label>Hintergrund Minimum (dB)<input v-model.number="settings.backgroundGainMinDb" type="number" /></label>
        <label>Hintergrund Maximum (dB)<input v-model.number="settings.backgroundGainMaxDb" type="number" /></label>
      </div></section>
      <p v-if="error" class="error-text">{{ error }}</p><p v-if="saved" class="success-text">Einstellungen gespeichert.</p>
      <button class="button button-primary" :disabled="saving">{{ saving ? "Speichern..." : "Einstellungen speichern" }}</button>
    </form>
  </section>
</template>
