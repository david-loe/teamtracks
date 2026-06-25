import { defineStore } from "pinia";
import { computed, ref } from "vue";

import type { Song, SongCreateInput, SongListItem, SongUpdateInput } from "@/api/songs";
import * as songsApi from "@/api/songs";

export const useSongsStore = defineStore("songs", () => {
  const songs = ref<SongListItem[]>([]);
  const currentSong = ref<Song | null>(null);
  const loading = ref(false);
  const loadingCurrent = ref(false);
  const saving = ref(false);
  const deletingId = ref<number | null>(null);
  const error = ref<string | null>(null);

  const hasSongs = computed(() => songs.value.length > 0);

  async function fetchSongs(organizationId: number): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      songs.value = await songsApi.listSongs(organizationId);
    } catch (err) {
      error.value = getErrorMessage(err);
    } finally {
      loading.value = false;
    }
  }

  async function fetchSong(organizationId: number, songId: number): Promise<void> {
    loadingCurrent.value = true;
    error.value = null;
    try {
      currentSong.value = await songsApi.getSong(organizationId, songId);
    } catch (err) {
      currentSong.value = null;
      error.value = getErrorMessage(err);
    } finally {
      loadingCurrent.value = false;
    }
  }

  async function createSong(organizationId: number, input: SongCreateInput): Promise<Song | null> {
    saving.value = true;
    error.value = null;
    try {
      const song = await songsApi.createSong(organizationId, input);
      await fetchSongs(organizationId);
      return song;
    } catch (err) {
      error.value = getErrorMessage(err);
      return null;
    } finally {
      saving.value = false;
    }
  }

  async function updateSong(organizationId: number, songId: number, input: SongUpdateInput): Promise<Song | null> {
    saving.value = true;
    error.value = null;
    try {
      const song = await songsApi.updateSong(organizationId, songId, input);
      currentSong.value = song;
      await fetchSongs(organizationId);
      return song;
    } catch (err) {
      error.value = getErrorMessage(err);
      return null;
    } finally {
      saving.value = false;
    }
  }

  async function deleteSong(organizationId: number, songId: number): Promise<boolean> {
    deletingId.value = songId;
    error.value = null;
    try {
      await songsApi.deleteSong(organizationId, songId);
      songs.value = songs.value.filter((song) => song.id !== songId);
      if (currentSong.value?.id === songId) {
        currentSong.value = null;
      }
      return true;
    } catch (err) {
      error.value = getErrorMessage(err);
      return false;
    } finally {
      deletingId.value = null;
    }
  }

  function clearError(): void {
    error.value = null;
  }

  function reset(): void {
    songs.value = [];
    currentSong.value = null;
    error.value = null;
  }

  return {
    songs,
    currentSong,
    loading,
    loadingCurrent,
    saving,
    deletingId,
    error,
    hasSongs,
    fetchSongs,
    fetchSong,
    createSong,
    updateSong,
    deleteSong,
    clearError,
    reset,
  };
});

function getErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "Unbekannter Fehler";
}
