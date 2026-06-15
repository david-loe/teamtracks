import { defineStore } from "pinia";
import { computed, ref } from "vue";

import type { Song, SongCreateInput, SongListItem } from "@/api/songs";
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

  async function fetchSongs(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      songs.value = await songsApi.listSongs();
    } catch (err) {
      error.value = getErrorMessage(err);
    } finally {
      loading.value = false;
    }
  }

  async function fetchSong(songId: number): Promise<void> {
    loadingCurrent.value = true;
    error.value = null;
    try {
      currentSong.value = await songsApi.getSong(songId);
    } catch (err) {
      currentSong.value = null;
      error.value = getErrorMessage(err);
    } finally {
      loadingCurrent.value = false;
    }
  }

  async function createSong(input: SongCreateInput): Promise<Song | null> {
    saving.value = true;
    error.value = null;
    try {
      const song = await songsApi.createSong(input);
      await fetchSongs();
      return song;
    } catch (err) {
      error.value = getErrorMessage(err);
      return null;
    } finally {
      saving.value = false;
    }
  }

  async function deleteSong(songId: number): Promise<boolean> {
    deletingId.value = songId;
    error.value = null;
    try {
      await songsApi.deleteSong(songId);
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
    deleteSong,
    clearError,
  };
});

function getErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "Unbekannter Fehler";
}
