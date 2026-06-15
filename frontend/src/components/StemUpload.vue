<script setup lang="ts">
import { ref } from "vue";

import type { StemRole } from "@/api/stems";
import { STEM_ROLES } from "@/api/stems";
import { SONG_KEYS } from "@/types/keys";

defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{
  submit: [payload: { name: string; role: StemRole; key: number | null; file: File }];
}>();

const name = ref("");
const role = ref<StemRole>("other");
const key = ref<number | null>(null);
const file = ref<File | null>(null);

function onFileChange(event: Event): void {
  const input = event.target as HTMLInputElement;
  file.value = input.files?.[0] ?? null;
  if (file.value && name.value.trim() === "") {
    name.value = file.value.name.replace(/\.[^.]+$/, "");
  }
}

function submit(): void {
  if (!file.value || name.value.trim() === "") {
    return;
  }

  emit("submit", {
    name: name.value.trim(),
    role: role.value,
    key: key.value,
    file: file.value,
  });

  name.value = "";
  role.value = "other";
  key.value = null;
  file.value = null;
}
</script>

<template>
  <form class="stack-form" autocomplete="off" @submit.prevent="submit">
    <label>
      Name
      <input id="stem-upload-name" v-model="name" name="name" type="text" maxlength="200" autocomplete="off" required :disabled="disabled" />
    </label>
    <label>
      Rolle
      <select id="stem-upload-role" v-model="role" name="role" :disabled="disabled">
        <option v-for="stemRole in STEM_ROLES" :key="stemRole" :value="stemRole">{{ stemRole }}</option>
      </select>
    </label>
    <label>
      Tonart
      <select id="stem-upload-key" v-model="key" name="key" :disabled="disabled">
        <option :value="null">tonartunabhaengig</option>
        <option v-for="songKey in SONG_KEYS" :key="songKey.value" :value="songKey.value">{{ songKey.label }}</option>
      </select>
    </label>
    <label>
      WAV-Datei
      <input id="stem-upload-file" name="file" type="file" accept=".wav,audio/wav,audio/x-wav" required :disabled="disabled" @change="onFileChange" />
    </label>
    <button class="button button-primary" type="submit" :disabled="disabled || !file || name.trim() === ''">
      Hochladen
    </button>
  </form>
</template>
