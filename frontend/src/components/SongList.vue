<script setup lang="ts">
import { RouterLink } from "vue-router";

import type { SongListItem } from "@/api/songs";
import { formatDuration } from "@/types/format";

defineProps<{
  songs: SongListItem[];
  deletingId: number | null;
}>();

defineEmits<{
  delete: [songId: number];
}>();
</script>

<template>
  <div class="table-shell">
    <table class="data-table">
      <thead>
        <tr>
          <th>Song</th>
          <th>Status</th>
          <th>Stems</th>
          <th>Dauer</th>
          <th class="actions-cell">Aktionen</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="song in songs" :key="song.id">
          <td>
            <strong>{{ song.title }}</strong>
            <span class="table-subtext">{{ song.slug }}</span>
          </td>
          <td><span class="status-pill" :class="`status-${song.status}`">{{ song.status }}</span></td>
          <td>{{ song.readyStemCount }} / {{ song.stemCount }} ready</td>
          <td>{{ formatDuration(song.durationMs) }}</td>
          <td class="actions-cell">
            <RouterLink class="button button-secondary" :to="`/admin/songs/${song.id}`">Verwalten</RouterLink>
            <RouterLink v-if="song.status === 'ready'" class="button button-secondary" :to="`/songs/${song.id}`">Player</RouterLink>
            <button
              class="button button-danger"
              type="button"
              :disabled="deletingId === song.id"
              @click="$emit('delete', song.id)"
            >
              Löschen
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
