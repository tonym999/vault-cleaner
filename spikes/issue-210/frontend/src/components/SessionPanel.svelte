<script lang="ts">
  import type { ReviewSession } from '../lib/session.svelte';
  import Button, { buttonVariants } from './ui/button.svelte';

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

<section class="session" aria-label="Review session">
  <p class="session-note" data-field="session_note" data-state={session.serverState}>{note}</p>
  <div class="session-actions" role="group" aria-label="Review session actions">
    <Button
      variant="outline"
      size="sm"
      class={session.canRequest ? '' : 'is-off'}
      aria-disabled={!session.canRequest}
      onclick={() => session.load()}
    >
      Reload report
    </Button>
    {#if session.serverState === 'finalized'}
      <a class={buttonVariants({ size: 'sm' })} href="/api/finalized.csv" download="dim-import.csv">
        Download reviewed CSV
      </a>
    {:else}
      <Button
        size="sm"
        class={session.canMutate && hasReport ? '' : 'is-off'}
        aria-disabled={!session.canMutate || !hasReport}
        onclick={() => session.finalize()}
      >
        Finalise review
      </Button>
    {/if}
    <Button
      variant="outline"
      size="sm"
      class={session.canReset ? '' : 'is-off'}
      aria-disabled={!session.canReset}
      onclick={() => session.reset()}
    >
      Reset session
    </Button>
  </div>
</section>
