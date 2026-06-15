<script setup lang="ts">
import type { ConversionJob } from "@/api/conversion";
import { formatDateTime } from "@/types/format";
import { formatSongKey } from "@/types/keys";

defineProps<{
  jobs: ConversionJob[];
  loading?: boolean;
}>();

function jobSubject(job: ConversionJob): string {
  if (job.jobType === "song_transposition") {
    return `Tonart ${formatSongKey(job.targetKey)}`;
  }
  return `Stem ${job.stemId ?? "n/a"}`;
}
</script>

<template>
  <div>
    <p v-if="loading" class="muted">Jobs werden geladen...</p>
    <p v-else-if="jobs.length === 0" class="muted">Noch keine Conversion-Jobs.</p>
    <div v-else class="job-list">
      <article v-for="job in jobs.slice(0, 8)" :key="job.id" class="job-row">
        <div>
          <strong>Job #{{ job.id }}</strong>
          <span class="table-subtext">{{ jobSubject(job) }} · {{ formatDateTime(job.createdAt) }}</span>
          <p v-if="job.errorMessage" class="error-text">{{ job.errorMessage }}</p>
        </div>
        <span class="status-pill" :class="`status-${job.status}`">{{ job.status }}</span>
      </article>
    </div>
  </div>
</template>
