import { defineStore } from "pinia";
import { computed, ref } from "vue";

import type { ConversionJob } from "@/api/conversion";
import * as conversionApi from "@/api/conversion";
import type { Stem, StemUploadInput, StemUploadResult } from "@/api/stems";
import * as stemsApi from "@/api/stems";
import type { StemKeyAssetInventoryItem } from "@/api/transposition";
import * as transpositionApi from "@/api/transposition";

const ACTIVE_JOB_STATUSES = new Set(["queued", "running"]);
const POLL_INTERVAL_MS = 2500;

export const useAdminStemsStore = defineStore("adminStems", () => {
  const stems = ref<Stem[]>([]);
  const jobs = ref<ConversionJob[]>([]);
  const keyAssets = ref<StemKeyAssetInventoryItem[]>([]);
  const loading = ref(false);
  const loadingJobs = ref(false);
  const loadingKeyAssets = ref(false);
  const uploading = ref(false);
  const deletingId = ref<number | null>(null);
  const startingConversion = ref(false);
  const transposing = ref(false);
  const error = ref<string | null>(null);
  const jobError = ref<string | null>(null);
  const transposeError = ref<string | null>(null);
  const pollingSongId = ref<number | null>(null);
  const pollingOrganizationId = ref<number | null>(null);
  let pollTimer: number | null = null;

  const activeJobs = computed(() => jobs.value.filter((job) => ACTIVE_JOB_STATUSES.has(job.status)));
  const hasActiveJobs = computed(() => activeJobs.value.length > 0);
  const hasActiveTranspositionJobs = computed(() =>
    activeJobs.value.some((job) => job.jobType === "song_transposition"),
  );
  const convertibleStems = computed(() =>
    stems.value.filter((stem) => stem.status === "uploaded" || stem.status === "error"),
  );

  async function load(organizationId: number, songId: number): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      stems.value = await stemsApi.listStems(organizationId, songId);
    } catch (err) {
      error.value = getErrorMessage(err);
    } finally {
      loading.value = false;
    }
  }

  async function loadJobs(organizationId: number, songId: number): Promise<void> {
    loadingJobs.value = true;
    jobError.value = null;
    try {
      jobs.value = await conversionApi.listConversionJobs(organizationId, songId);
      if (hasActiveJobs.value) {
        startPolling(organizationId, songId);
      } else {
        stopPolling();
      }
    } catch (err) {
      jobError.value = getErrorMessage(err);
    } finally {
      loadingJobs.value = false;
    }
  }

  async function loadKeyAssets(organizationId: number, songId: number): Promise<void> {
    loadingKeyAssets.value = true;
    try {
      keyAssets.value = await transpositionApi.listKeyAssets(organizationId, songId);
    } catch (err) {
      transposeError.value = getErrorMessage(err);
    } finally {
      loadingKeyAssets.value = false;
    }
  }

  async function upload(organizationId: number, songId: number, input: StemUploadInput): Promise<boolean> {
    uploading.value = true;
    error.value = null;
    try {
      const stem = await stemsApi.uploadStem(organizationId, songId, input);
      stems.value = [...stems.value, stem];
      return true;
    } catch (err) {
      error.value = getErrorMessage(err);
      return false;
    } finally {
      uploading.value = false;
    }
  }

  async function uploadMany(organizationId: number, songId: number, inputs: StemUploadInput[]): Promise<StemUploadResult[]> {
    uploading.value = true;
    error.value = null;
    const results: StemUploadResult[] = [];
    try {
      for (const input of inputs) {
        try {
          const stem = await stemsApi.uploadStem(organizationId, songId, input);
          stems.value = [...stems.value, stem];
          results.push({ input, stem, error: null });
        } catch (err) {
          results.push({ input, stem: null, error: getErrorMessage(err) });
        }
      }
      return results;
    } finally {
      uploading.value = false;
    }
  }

  async function removeStem(organizationId: number, stemId: number): Promise<boolean> {
    deletingId.value = stemId;
    error.value = null;
    try {
      await stemsApi.deleteStem(organizationId, stemId);
      stems.value = stems.value.filter((stem) => stem.id !== stemId);
      jobs.value = jobs.value.filter((job) => job.stemId !== stemId);
      return true;
    } catch (err) {
      error.value = getErrorMessage(err);
      return false;
    } finally {
      deletingId.value = null;
    }
  }

  async function startConversion(organizationId: number, songId: number): Promise<boolean> {
    startingConversion.value = true;
    jobError.value = null;
    try {
      await conversionApi.createConversionJobs(organizationId, songId, { requestedBy: "admin-ui" });
      await Promise.all([
        load(organizationId, songId),
        loadJobs(organizationId, songId),
        loadKeyAssets(organizationId, songId),
      ]);
      startPolling(organizationId, songId);
      return true;
    } catch (err) {
      jobError.value = getErrorMessage(err);
      return false;
    } finally {
      startingConversion.value = false;
    }
  }

  async function reconvert(organizationId: number, songId: number): Promise<boolean> {
    const stemIds = stems.value.filter((stem) => stem.sourceFilename !== null).map((stem) => stem.id);
    if (stemIds.length === 0) return false;
    startingConversion.value = true;
    jobError.value = null;
    try {
      await conversionApi.createConversionJobs(organizationId, songId, {
        stemIds,
        requestedBy: "admin-ui-reconvert",
      });
      await Promise.all([loadJobs(organizationId, songId), loadKeyAssets(organizationId, songId)]);
      startPolling(organizationId, songId);
      return true;
    } catch (err) {
      jobError.value = getErrorMessage(err);
      return false;
    } finally {
      startingConversion.value = false;
    }
  }

  async function transpose(organizationId: number, songId: number, targetKeys: number[]): Promise<boolean> {
    transposing.value = true;
    transposeError.value = null;
    try {
      await transpositionApi.transposeSong(organizationId, songId, { targetKeys });
      await Promise.all([loadJobs(organizationId, songId), loadKeyAssets(organizationId, songId)]);
      startPolling(organizationId, songId);
      return true;
    } catch (err) {
      transposeError.value = getErrorMessage(err);
      return false;
    } finally {
      transposing.value = false;
    }
  }

  function startPolling(organizationId: number, songId: number): void {
    if (pollingOrganizationId.value === organizationId && pollingSongId.value === songId && pollTimer !== null) {
      return;
    }

    stopPolling();
    pollingSongId.value = songId;
    pollingOrganizationId.value = organizationId;
    pollTimer = window.setInterval(() => {
      void refreshDuringPolling(organizationId, songId);
    }, POLL_INTERVAL_MS);
  }

  function stopPolling(): void {
    if (pollTimer !== null) {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
    pollingSongId.value = null;
    pollingOrganizationId.value = null;
  }

  async function refreshDuringPolling(organizationId: number, songId: number): Promise<void> {
    try {
      const hadActiveJobs = hasActiveJobs.value;
      const [nextStems, nextJobs] = await Promise.all([
        stemsApi.listStems(organizationId, songId),
        conversionApi.listConversionJobs(organizationId, songId),
      ]);
      stems.value = nextStems;
      jobs.value = nextJobs;
      if (hadActiveJobs || nextJobs.some((job) => ACTIVE_JOB_STATUSES.has(job.status))) {
        keyAssets.value = await transpositionApi.listKeyAssets(organizationId, songId);
      }
      jobError.value = null;
      if (!hasActiveJobs.value) {
        stopPolling();
      }
    } catch (err) {
      jobError.value = getErrorMessage(err);
    }
  }

  function clearError(): void {
    error.value = null;
    jobError.value = null;
    transposeError.value = null;
  }

  function reset(): void {
    stopPolling();
    stems.value = [];
    jobs.value = [];
    keyAssets.value = [];
    error.value = null;
    jobError.value = null;
    transposeError.value = null;
  }

  return {
    stems,
    jobs,
    keyAssets,
    loading,
    loadingJobs,
    loadingKeyAssets,
    uploading,
    deletingId,
    startingConversion,
    transposing,
    error,
    jobError,
    transposeError,
    activeJobs,
    hasActiveJobs,
    hasActiveTranspositionJobs,
    convertibleStems,
    load,
    loadJobs,
    loadKeyAssets,
    upload,
    uploadMany,
    removeStem,
    startConversion,
    reconvert,
    transpose,
    startPolling,
    stopPolling,
    clearError,
    reset,
  };
});

function getErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : "Unbekannter Fehler";
}
