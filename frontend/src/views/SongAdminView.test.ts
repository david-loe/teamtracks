import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SongAdminView from "@/views/SongAdminView.vue";

const storeMocks = vi.hoisted(() => ({
  songs: {
    currentSong: {
      id: 10,
      title: "Test Song",
      artist: "Test Artist",
      slug: "test-song",
      description: null,
      status: "ready",
      originalKey: 0,
      targetSampleRate: 48000,
      targetDurationMs: 120000,
      createdAt: "2026-01-01T00:00:00Z",
      updatedAt: "2026-01-01T00:00:00Z",
    },
    saving: false,
    error: null,
    fetchSong: vi.fn().mockResolvedValue(undefined),
    updateSong: vi.fn().mockResolvedValue(undefined),
  },
  stems: {
    stems: [
      {
        id: 1,
        songId: 10,
        name: "Drums",
        role: "drums",
        key: null,
        status: "ready",
        sourceFilename: "drums.wav",
        durationMs: 120000,
        sampleRate: 48000,
        channels: 2,
        fileSizeBytes: 1000,
        errorMessage: null,
      },
      {
        id: 2,
        songId: 10,
        name: "Bass",
        role: "bass",
        key: 0,
        status: "ready",
        sourceFilename: "bass.wav",
        durationMs: 120000,
        sampleRate: 48000,
        channels: 1,
        fileSizeBytes: 1000,
        errorMessage: null,
      },
    ],
    keyAssets: [
      {
        stemId: 1,
        stemName: "Drums",
        stemRole: "drums",
        variants: [{ songKeyId: 100, semitoneOffset: 0, targetKey: 0, status: "ready", errorMessage: null }],
      },
      {
        stemId: 2,
        stemName: "Bass",
        stemRole: "bass",
        variants: [{ songKeyId: 101, semitoneOffset: 2, targetKey: 2, status: "ready", errorMessage: null }],
      },
    ],
    loading: false,
    uploading: false,
    error: null,
    deletingId: null,
    convertibleStems: [],
    startingConversion: false,
    jobError: null,
    hasActiveJobs: false,
    jobs: [],
    loadingJobs: false,
    transposing: false,
    transposeError: null,
    reset: vi.fn(),
    load: vi.fn().mockResolvedValue(undefined),
    loadJobs: vi.fn().mockResolvedValue(undefined),
    loadKeyAssets: vi.fn().mockResolvedValue(undefined),
    uploadMany: vi.fn().mockResolvedValue(undefined),
    removeStem: vi.fn().mockResolvedValue(undefined),
    transpose: vi.fn().mockResolvedValue(true),
    startConversion: vi.fn().mockResolvedValue(undefined),
    reconvert: vi.fn().mockResolvedValue(undefined),
  },
}));

vi.mock("@/stores/songs", () => ({ useSongsStore: () => storeMocks.songs }));
vi.mock("@/stores/adminStems", () => ({ useAdminStemsStore: () => storeMocks.stems }));

describe("SongAdminView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("leaves available keys empty for key-independent stems", async () => {
    const wrapper = mount(SongAdminView, {
      props: { organizationId: "7", id: "10" },
      global: {
        stubs: {
          RouterLink: { template: "<a><slot /></a>" },
          StemUpload: true,
          ConversionStatus: true,
        },
      },
    });
    await flushPromises();

    const rows = wrapper.findAll("tbody tr");
    expect(rows[0].findAll("td")[4].text()).toBe("");
    expect(rows[1].findAll("td")[4].text()).toBe("D");
  });
});
