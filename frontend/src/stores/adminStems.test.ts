import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as conversionApi from "@/api/conversion";
import type { ConversionJob } from "@/api/conversion";
import type { Stem } from "@/api/stems";
import * as stemsApi from "@/api/stems";
import { useAdminStemsStore } from "@/stores/adminStems";

vi.mock("@/api/stems", () => ({
  listStems: vi.fn(),
  uploadStem: vi.fn(),
  importStem: vi.fn(),
  deleteStem: vi.fn(),
}));

vi.mock("@/api/conversion", () => ({
  createConversionJobs: vi.fn(),
  getConversionJob: vi.fn(),
  listConversionJobs: vi.fn(),
}));

const uploadedStem: Stem = {
  id: 1,
  songId: 10,
  name: "Drums",
  role: "drums",
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
    const ok = await store.upload(10, { name: "Drums", role: "drums", file });

    expect(ok).toBe(true);
    expect(store.stems).toEqual([readyStem, uploadedStem]);
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
});
