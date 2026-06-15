<script setup lang="ts">
import { ref } from "vue";

import type { StemRole } from "@/api/stems";
import { STEM_ROLES } from "@/api/stems";

defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{
  submit: [payload: { name: string; role: StemRole; file: File }];
}>();

const name = ref("");
const role = ref<StemRole>("other");
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
    file: file.value,
  });

  name.value = "";
  role.value = "other";
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
      WAV-Datei
      <input id="stem-upload-file" name="file" type="file" accept=".wav,audio/wav,audio/x-wav" required :disabled="disabled" @change="onFileChange" />
    </label>
    <button class="button button-primary" type="submit" :disabled="disabled || !file || name.trim() === ''">
      Hochladen
    </button>
  </form>
</template>
