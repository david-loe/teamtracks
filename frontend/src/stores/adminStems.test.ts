import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as conversionApi from "@/api/conversion";
import type { ConversionJob } from "@/api/conversion";
import type { Stem } from "@/api/stems";
import * as stemsApi from "@/api/stems";
import * as transpositionApi from "@/api/transposition";
import { useAdminStemsStore } from "@/stores/adminStems";

vi.mock("@/api/stems", () => ({
  listStems: vi.fn(),
  uploadStem: vi.fn(),
  deleteStem: vi.fn(),
}));

vi.mock("@/api/conversion", () => ({
  createConversionJobs: vi.fn(),
  getConversionJob: vi.fn(),
  listConversionJobs: vi.fn(),
}));

vi.mock("@/api/transposition", () => ({
  transposeSong: vi.fn(),
  listKeyAssets: vi.fn(),
}));

const uploadedStem: Stem = {
  id: 1,
  songId: 10,
  name: "Drums",
  role: "drums",
  key: null,
  status: "uploaded",
  sourceFilename: "drums.wav",
  sourceFormat: "wav",
  codec: null,
  sampleRate: null,
  channels: null,
  durationMs: null,
  fileSizeBytes: 1024,
  bitrateKbps: null,
  errorMessage: null,
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
};

const readyStem: Stem = {
  ...uploadedStem,
  id: 2,
  name: "Bass",
  role: "bass",
  key: 0,
  status: "ready",
  codec: "aac",
  sampleRate: 48000,
  channels: 1,
  durationMs: 100000,
  bitrateKbps: 96,
};

const runningJob: ConversionJob = {
  id: 99,
  songId: 10,
  stemId: 1,
  songKeyId: null,
  jobType: "stem_conversion",
  targetKey: null,
  semitoneOffset: null,
  status: "running",
  requestedBy: "admin-ui",
  monoBitrateKbps: 96,
  stereoBitrateKbps: 160,
  targetSampleRate: 48000,
  durationToleranceMs: 100,
  startedAt: "2026-01-01T00:00:00Z",
  finishedAt: null,
  errorMessage: null,
  createdAt: "2026-01-01T00:00:00Z",
  updatedAt: "2026-01-01T00:00:00Z",
};

describe("useAdminStemsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useRealTimers();
    vi.resetAllMocks();
    vi.mocked(transpositionApi.listKeyAssets).mockResolvedValue([]);
  });

  it("loads stems and exposes only uploaded/error stems as convertible", async () => {
    vi.mocked(stemsApi.listStems).mockResolvedValue([uploadedStem, readyStem]);

    const store = useAdminStemsStore();
    await store.load(10);

    expect(store.stems).toEqual([uploadedStem, readyStem]);
    expect(store.convertibleStems).toEqual([uploadedStem]);
    expect(store.error).toBeNull();
  });

  it("appends uploaded stems", async () => {
    vi.mocked(stemsApi.listStems).mockResolvedValue([readyStem]);
    vi.mocked(stemsApi.uploadStem).mockResolvedValue(uploadedStem);

    const file = new File(["wav"], "drums.wav", { type: "audio/wav" });
    const store = useAdminStemsStore();
    await store.load(10);
    const ok = await store.upload(10, { name: "Drums", role: "drums", key: null, file });

    expect(ok).toBe(true);
    expect(store.stems).toEqual([readyStem, uploadedStem]);
  });

  it("uploads batches sequentially and continues after a failure", async () => {
    let resolveFirst: ((stem: Stem) => void) | undefined;
    const firstUpload = new Promise<Stem>((resolve) => {
      resolveFirst = resolve;
    });
    vi.mocked(stemsApi.uploadStem)
      .mockReturnValueOnce(firstUpload)
      .mockRejectedValueOnce(new Error("Second upload failed"))
      .mockResolvedValueOnce(readyStem);

    const inputs = [
      { name: "Drums", role: "drums" as const, key: null, file: new File(["one"], "drums.wav") },
      { name: "Vocals", role: "vocals" as const, key: 0, file: new File(["two"], "vocals.wav") },
      { name: "Bass", role: "bass" as const, key: 0, file: new File(["three"], "bass.wav") },
    ];
    const store = useAdminStemsStore();
    const resultPromise = store.uploadMany(10, inputs);

    expect(store.uploading).toBe(true);
    expect(stemsApi.uploadStem).toHaveBeenCalledTimes(1);

    resolveFirst?.(uploadedStem);
    const results = await resultPromise;

    expect(stemsApi.uploadStem).toHaveBeenCalledTimes(3);
    expect(vi.mocked(stemsApi.uploadStem).mock.calls.map((call) => call[1])).toEqual(inputs);
    expect(results).toEqual([
      { input: inputs[0], stem: uploadedStem, error: null },
      { input: inputs[1], stem: null, error: "Second upload failed" },
      { input: inputs[2], stem: readyStem, error: null },
    ]);
    expect(store.stems).toEqual([uploadedStem, readyStem]);
    expect(store.uploading).toBe(false);
  });

  it("starts conversion and reloads stems and jobs", async () => {
    vi.mocked(conversionApi.createConversionJobs).mockResolvedValue({ jobIds: [99], status: "queued" });
    vi.mocked(stemsApi.listStems).mockResolvedValue([uploadedStem]);
    vi.mocked(conversionApi.listConversionJobs).mockResolvedValue([runningJob]);

    const store = useAdminStemsStore();
    const ok = await store.startConversion(10);

    expect(ok).toBe(true);
    expect(conversionApi.createConversionJobs).toHaveBeenCalledWith(10, { requestedBy: "admin-ui" });
    expect(store.stems).toEqual([uploadedStem]);
    expect(store.jobs).toEqual([runningJob]);
    store.reset();
  });

  it("removes a stem and its jobs after delete succeeds", async () => {
    vi.mocked(stemsApi.listStems).mockResolvedValue([uploadedStem]);
    vi.mocked(conversionApi.listConversionJobs).mockResolvedValue([runningJob]);
    vi.mocked(stemsApi.deleteStem).mockResolvedValue(undefined);

    const store = useAdminStemsStore();
    await store.load(10);
    await store.loadJobs(10);
    const ok = await store.removeStem(1);

    expect(ok).toBe(true);
    expect(store.stems).toEqual([]);
    expect(store.jobs).toEqual([]);
  });

  it("queues all source stems for explicit reconversion", async () => {
    vi.mocked(stemsApi.listStems).mockResolvedValue([uploadedStem, readyStem]);
    vi.mocked(conversionApi.createConversionJobs).mockResolvedValue({ jobIds: [1, 2], status: "queued" });
    vi.mocked(conversionApi.listConversionJobs).mockResolvedValue([]);

    const store = useAdminStemsStore();
    await store.load(10);
    const ok = await store.reconvert(10);

    expect(ok).toBe(true);
    expect(conversionApi.createConversionJobs).toHaveBeenCalledWith(10, {
      stemIds: [1, 2],
      requestedBy: "admin-ui-reconvert",
    });
  });

  it("transposes ready songs into selected keys", async () => {
    vi.mocked(transpositionApi.transposeSong).mockResolvedValue({ jobIds: [100], status: "queued" });
    vi.mocked(conversionApi.listConversionJobs).mockResolvedValue([
      {
        ...runningJob,
        id: 100,
        stemId: null,
        jobType: "song_transposition",
        targetKey: 2,
        semitoneOffset: 2,
      },
    ]);

    const store = useAdminStemsStore();
    const ok = await store.transpose(10, [2]);

    expect(ok).toBe(true);
    expect(transpositionApi.transposeSong).toHaveBeenCalledWith(10, { targetKeys: [2] });
    expect(conversionApi.listConversionJobs).toHaveBeenCalledWith(10);
    expect(transpositionApi.listKeyAssets).toHaveBeenCalledWith(10);
    expect(store.transposeError).toBeNull();
    store.reset();
  });
});
