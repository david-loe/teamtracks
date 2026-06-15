import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Song, SongListItem } from "@/api/songs";
import * as songsApi from "@/api/songs";
import { useSongsStore } from "@/stores/songs";

vi.mock("@/api/songs", () => ({
  listSongs: vi.fn(),
  createSong: vi.fn(),
  getSong: vi.fn(),
  updateSong: vi.fn(),
  deleteSong: vi.fn(),
}));

const songList: SongListItem[] = [
  {
    id: 1,
    title: "First Song",
    artist: "First Artist",
    slug: "first-song",
    status: "ready",
    originalKey: 0,
    stemCount: 2,
    readyStemCount: 2,
    durationMs: 120000,
  },
];

const song: Song = {
  id: 1,
  title: "First Song",
  artist: "First Artist",
  slug: "first-song",
  description: null,
  status: "ready",
  originalKey: 0,
  targetSampleRate: 48000,
  targetDurationMs: 120000,
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
};

describe("useSongsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
  });

  it("loads songs and exposes hasSongs", async () => {
    vi.mocked(songsApi.listSongs).mockResolvedValue(songList);

    const store = useSongsStore();
    await store.fetchSongs();

    expect(store.songs).toEqual(songList);
    expect(store.hasSongs).toBe(true);
    expect(store.error).toBeNull();
  });

  it("stores API errors when loading the current song fails", async () => {
    vi.mocked(songsApi.getSong).mockRejectedValue(new Error("not found"));

    const store = useSongsStore();
    await store.fetchSong(404);

    expect(store.currentSong).toBeNull();
    expect(store.error).toBe("not found");
  });

  it("creates a song and refreshes the list", async () => {
    vi.mocked(songsApi.createSong).mockResolvedValue(song);
    vi.mocked(songsApi.listSongs).mockResolvedValue(songList);

    const store = useSongsStore();
    const created = await store.createSong({ title: "First Song", artist: "First Artist", slug: "first-song", originalKey: 0 });

    expect(created).toEqual(song);
    expect(songsApi.listSongs).toHaveBeenCalledTimes(1);
    expect(store.songs).toEqual(songList);
  });

  it("updates a song and refreshes the list", async () => {
    const updatedSong = { ...song, title: "Updated Song", artist: "Updated Artist", originalKey: 5 };
    vi.mocked(songsApi.updateSong).mockResolvedValue(updatedSong);
    vi.mocked(songsApi.listSongs).mockResolvedValue([
      { ...songList[0], title: "Updated Song", artist: "Updated Artist", originalKey: 5 },
    ]);

    const store = useSongsStore();
    const updated = await store.updateSong(1, {
      title: "Updated Song",
      artist: "Updated Artist",
      originalKey: 5,
    });

    expect(updated).toEqual(updatedSong);
    expect(store.currentSong).toEqual(updatedSong);
    expect(songsApi.listSongs).toHaveBeenCalledTimes(1);
    expect(store.songs[0].artist).toBe("Updated Artist");
  });

  it("deletes a song locally after the API succeeds", async () => {
    vi.mocked(songsApi.listSongs).mockResolvedValue(songList);
    vi.mocked(songsApi.deleteSong).mockResolvedValue(undefined);

    const store = useSongsStore();
    await store.fetchSongs();
    const deleted = await store.deleteSong(1);

    expect(deleted).toBe(true);
    expect(store.songs).toEqual([]);
  });
});
