<script setup lang="ts">
import { onMounted, ref } from "vue";

import {
  DEFAULT_USER_PLAYER_SETTINGS,
  getUserPlayerSettings,
  saveUserPlayerSettings,
  type UserPlayerSettings,
} from "@/storage/userPlayerSettings";

const MIN_GAIN_DB = -60;
const MAX_GAIN_DB = 12;

const settings = ref<UserPlayerSettings>({ ...DEFAULT_USER_PLAYER_SETTINGS });
const loading = ref(true);
const saving = ref(false);
const saved = ref(false);
const error = ref<string | null>(null);
let saveId = 0;
let saveQueue = Promise.resolve();

onMounted(() => void load());

async function load(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    const storedSettings = (await getUserPlayerSettings()) ?? DEFAULT_USER_PLAYER_SETTINGS;
    settings.value = {
      focusedGainDb: clampGain(storedSettings.focusedGainDb),
      backgroundGainDb: clampGain(storedSettings.backgroundGainDb),
    };
  } catch (err) {
    error.value = getErrorMessage(err, "Einstellungen konnten nicht geladen werden.");
  } finally {
    loading.value = false;
  }
}

async function save(): Promise<void> {
  const requestId = ++saveId;
  saving.value = true;
  saved.value = false;
  error.value = null;
  try {
    const nextSettings = { ...settings.value };
    saveQueue = saveQueue.catch(() => undefined).then(() => saveUserPlayerSettings(nextSettings));
    await saveQueue;
    if (requestId === saveId) {
      saved.value = true;
    }
  } catch (err) {
    if (requestId === saveId) {
      error.value = getErrorMessage(err, "Einstellungen konnten nicht gespeichert werden.");
    }
  } finally {
    if (requestId === saveId) {
      saving.value = false;
    }
  }
}

function getErrorMessage(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

function clampGain(value: number): number {
  return Math.min(Math.max(value, MIN_GAIN_DB), MAX_GAIN_DB);
}
</script>

<template>
  <section>
    <div class="page-header compact-page-header">
      <div>
        <p class="eyebrow">Benutzer</p>
        <h1>Einstellungen</h1>
        <p class="muted">Diese Werte gelten in diesem Browser für alle Songs.</p>
      </div>
    </div>

    <p v-if="loading" class="muted">Einstellungen werden geladen...</p>
    <section v-else class="panel user-settings-panel">
      <label class="settings-range">
        <span>Fokus-Gain <strong>{{ settings.focusedGainDb }} dB</strong></span>
        <input
          id="user-focus-gain"
          v-model.number="settings.focusedGainDb"
          type="range"
          :min="MIN_GAIN_DB"
          :max="MAX_GAIN_DB"
          step="1"
          @input="save"
        />
      </label>

      <label class="settings-range">
        <span>Hintergrund-Gain <strong>{{ settings.backgroundGainDb }} dB</strong></span>
        <input
          id="user-background-gain"
          v-model.number="settings.backgroundGainDb"
          type="range"
          :min="MIN_GAIN_DB"
          :max="MAX_GAIN_DB"
          step="1"
          @input="save"
        />
      </label>

      <p class="settings-save-status" aria-live="polite">
        <span v-if="saving" class="muted">Wird gespeichert...</span>
        <span v-else-if="error" class="error-text">{{ error }}</span>
        <span v-else-if="saved" class="success-text">Gespeichert.</span>
      </p>
    </section>
  </section>
</template>
