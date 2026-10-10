<script lang="ts">
  import type { ReviewSession } from '../lib/session.svelte';

  let { session }: { session: ReviewSession } = $props();

  const NOTES: Record<string, string> = {
    idle: 'No report is loaded. Upload a DIM armor export on the main review page, then reload here.',
    finalized: 'Finalised. The reviewed CSV has been produced and this review is frozen.',
    closed: 'This review session is closed. It accepts no more verdicts.',
  };
  const note = $derived(
    NOTES[session.serverState] ??
      'Verdicts are held by the server for this session. Nothing is saved until you finalise.',
  );
  const hasReport = $derived(session.envelope?.snapshot != null);
</script>

<section class="card card-border bg-base-100" aria-label="Review session">
  <div class="card-body flex-row flex-wrap items-center justify-between gap-3 p-4">
    <p class="min-w-0 flex-1 basis-64" data-field="session_note" data-state={session.serverState}>{note}</p>
    <div class="flex flex-wrap gap-2" role="group" aria-label="Review session actions">
      <button
        type="button"
        class="btn btn-sm"
        class:btn-disabled={!session.canRequest}
        aria-disabled={!session.canRequest}
        onclick={() => session.load()}
      >
        Reload report
      </button>
      {#if session.serverState === 'finalized'}
        <a class="btn btn-sm btn-primary" href="/api/finalized.csv" download="dim-import.csv">Download reviewed CSV</a>
      {:else}
        <button
          type="button"
          class="btn btn-sm btn-primary"
          class:btn-disabled={!session.canMutate || !hasReport}
          aria-disabled={!session.canMutate || !hasReport}
          onclick={() => session.finalize()}
        >
          Finalise review
        </button>
      {/if}
      <button
        type="button"
        class="btn btn-sm btn-outline"
        class:btn-disabled={!session.canReset}
        aria-disabled={!session.canReset}
        onclick={() => session.reset()}
      >
        Reset session
      </button>
    </div>
  </div>
</section>
