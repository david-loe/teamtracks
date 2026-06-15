<script setup lang="ts">
import { computed, ref } from "vue";

import type { StemRole, StemUploadInput, StemUploadResult } from "@/api/stems";
import { STEM_ROLES } from "@/api/stems";
import { SONG_KEYS } from "@/types/keys";

const props = defineProps<{
  disabled?: boolean;
  originalKey: number;
  upload: (inputs: StemUploadInput[]) => Promise<StemUploadResult[]>;
}>();

interface UploadRow {
  id: number;
  file: File;
  name: string;
  role: StemRole;
  key: number | null;
  status: "pending" | "uploading" | "error";
  error: string | null;
}

const rows = ref<UploadRow[]>([]);
const submitting = ref(false);
let nextRowId = 1;

const controlsDisabled = computed(() => Boolean(props.disabled) || submitting.value);
const canSubmit = computed(
  () => rows.value.length > 0 && rows.value.every((row) => row.name.trim() !== ""),
);

function onFileChange(event: Event): void {
  const input = event.target as HTMLInputElement;
  const newRows = Array.from(input.files ?? []).map((file) => ({
    id: nextRowId++,
    file,
    name: file.name.replace(/\.[^.]+$/, ""),
    role: "other" as StemRole,
    key: props.originalKey,
    status: "pending" as const,
    error: null,
  }));
  rows.value = [...rows.value, ...newRows];
  input.value = "";
}

function onRoleChange(row: UploadRow): void {
  if (row.role === "drums" || row.role === "click_cue") {
    row.key = null;
  } else if (row.key === null) {
    row.key = props.originalKey;
  }
  resetRowError(row);
}

function resetRowError(row: UploadRow): void {
  if (row.status === "error") {
    row.status = "pending";
    row.error = null;
  }
}

function removeRow(rowId: number): void {
  rows.value = rows.value.filter((row) => row.id !== rowId);
}

async function submit(): Promise<void> {
  if (!canSubmit.value || controlsDisabled.value) {
    return;
  }

  const submittedRows = [...rows.value];
  const inputs = submittedRows.map((row) => ({
    name: row.name.trim(),
    role: row.role,
    key: row.key,
    file: row.file,
  }));

  submitting.value = true;
  for (const row of submittedRows) {
    row.status = "uploading";
    row.error = null;
  }

  try {
    const results = await props.upload(inputs);
    const successfulIds = new Set<number>();

    submittedRows.forEach((row, index) => {
      const result = results[index];
      if (result?.stem) {
        successfulIds.add(row.id);
        return;
      }

      row.status = "error";
      row.error = result?.error ?? "Upload fehlgeschlagen";
    });

    rows.value = rows.value.filter((row) => !successfulIds.has(row.id));
  } catch (err) {
    const message = err instanceof Error ? err.message : "Upload fehlgeschlagen";
    for (const row of submittedRows) {
      row.status = "error";
      row.error = message;
    }
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <form class="stack-form" autocomplete="off" @submit.prevent="submit">
    <label>
      WAV-Dateien
      <input
        id="stem-upload-files"
        name="files"
        type="file"
        accept=".wav,audio/wav,audio/x-wav"
        multiple
        :disabled="controlsDisabled"
        @change="onFileChange"
      />
    </label>

    <div v-if="rows.length" class="upload-queue">
      <article v-for="row in rows" :key="row.id" class="upload-row">
        <label :for="`stem-upload-name-${row.id}`">
          Name
          <input
            :id="`stem-upload-name-${row.id}`"
            v-model="row.name"
            type="text"
            maxlength="200"
            required
            :disabled="controlsDisabled"
            @input="resetRowError(row)"
          />
        </label>
        <label :for="`stem-upload-role-${row.id}`">
          Rolle
          <select
            :id="`stem-upload-role-${row.id}`"
            v-model="row.role"
            :disabled="controlsDisabled"
            @change="onRoleChange(row)"
          >
            <option v-for="stemRole in STEM_ROLES" :key="stemRole" :value="stemRole">{{ stemRole }}</option>
          </select>
        </label>
        <label :for="`stem-upload-key-${row.id}`">
          Tonart
          <select
            :id="`stem-upload-key-${row.id}`"
            v-model="row.key"
            :disabled="controlsDisabled"
            @change="resetRowError(row)"
          >
            <option :value="null">tonartunabhaengig</option>
            <option v-for="songKey in SONG_KEYS" :key="songKey.value" :value="songKey.value">{{ songKey.label }}</option>
          </select>
        </label>
        <div class="upload-row-actions">
          <span class="table-subtext">{{ row.file.name }}</span>
          <button class="button button-secondary" type="button" :disabled="controlsDisabled" @click="removeRow(row.id)">
            Entfernen
          </button>
        </div>
        <p v-if="row.status === 'uploading'" class="muted upload-row-message">Wird hochgeladen...</p>
        <p v-else-if="row.error" class="error-text upload-row-message">{{ row.error }}</p>
      </article>
    </div>

    <button class="button button-primary" type="submit" :disabled="controlsDisabled || !canSubmit">
      {{ submitting ? "Wird hochgeladen..." : `${rows.length} Stem(s) hochladen` }}
    </button>
  </form>
</template>
