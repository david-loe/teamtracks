<script setup lang="ts">
import { ref } from "vue";

import type { StemRole } from "@/api/stems";
import { STEM_ROLES } from "@/api/stems";
import { SONG_KEYS } from "@/types/keys";

defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{
  submit: [payload: { sourcePath: string; name: string; role: StemRole; key: number | null }];
}>();

const sourcePath = ref("");
const name = ref("");
const role = ref<StemRole>("other");
const key = ref<number | null>(null);

function submit(): void {
  if (sourcePath.value.trim() === "" || name.value.trim() === "") {
    return;
  }

  emit("submit", {
    sourcePath: sourcePath.value.trim(),
    name: name.value.trim(),
    role: role.value,
    key: key.value,
  });

  sourcePath.value = "";
  name.value = "";
  role.value = "other";
  key.value = null;
}
</script>

<template>
  <form class="stack-form" autocomplete="off" @submit.prevent="submit">
    <label>
      Importpfad
      <input id="stem-import-source-path" v-model="sourcePath" name="sourcePath" type="text" autocomplete="off" required :disabled="disabled" placeholder="drums.wav" />
    </label>
    <label>
      Name
      <input id="stem-import-name" v-model="name" name="name" type="text" maxlength="200" autocomplete="off" required :disabled="disabled" />
    </label>
    <label>
      Rolle
      <select id="stem-import-role" v-model="role" name="role" :disabled="disabled">
        <option v-for="stemRole in STEM_ROLES" :key="stemRole" :value="stemRole">{{ stemRole }}</option>
      </select>
    </label>
    <label>
      Tonart
      <select id="stem-import-key" v-model="key" name="key" :disabled="disabled">
        <option :value="null">tonartunabhaengig</option>
        <option v-for="songKey in SONG_KEYS" :key="songKey.value" :value="songKey.value">{{ songKey.label }}</option>
      </select>
    </label>
    <button class="button button-primary" type="submit" :disabled="disabled || sourcePath.trim() === '' || name.trim() === ''">
      Importieren
    </button>
  </form>
</template>
