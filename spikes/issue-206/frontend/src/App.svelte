<script lang="ts">
  import Filters from './components/Filters.svelte';
  import GroupCard from './components/GroupCard.svelte';
  import SessionPanel from './components/SessionPanel.svelte';
  import type { ReviewSession } from './lib/session.svelte';
  import { SECTION_COPY, type GroupKind } from './lib/view';

  let { session }: { session: ReviewSession } = $props();

  const KINDS: GroupKind[] = ['exact', 'same_stat'];
  const TONES = { info: 'alert-info', ok: 'alert-success', error: 'alert-error' } as const;

  const sections = $derived(
    KINDS.map((kind) => ({ kind, groups: session.shown.filter((group) => group.kind === kind) })).filter(
      (section) => section.groups.length,
    ),
  );

  // Focus policy on a report change.  Groups and members are keyed by id, so
  // a control whose member is still in the new report is the same node and
  // keeps focus.  If the focused control's member is gone, focus would fall
  // to <body>; it is moved to the list heading instead.  These two effects
  // are the slice's only direct DOM access: one notes, before the DOM
  // changes, whether focus is in the list; the other runs after the change.
  let list: HTMLElement;
  let listHeading: HTMLElement;
  let focusWasInList = false;
  $effect.pre(() => {
    void session.reportKey;
    focusWasInList = list?.contains(document.activeElement) ?? false;
  });
  $effect(() => {
    void session.reportKey;
    if (focusWasInList && document.activeElement === document.body) listHeading.focus();
  });
</script>

<a class="btn btn-primary sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-10" href="#vc-title">
  Skip to review content
</a>

<main class="mx-auto flex max-w-6xl flex-col gap-4 p-4 sm:p-6">
  <header>
    <h1 id="vc-title" tabindex="-1" class="text-2xl font-bold">Armor duplicates</h1>
    <p class="text-sm">vault-cleaner review · Svelte frontend spike (#206)</p>
  </header>

  <p
    id="vc-status"
    role="status"
    aria-live="polite"
    class="alert {TONES[session.status.tone]}"
    data-connection={session.connection}
    data-busy={session.busy ?? ''}
    data-tone={session.status.tone}
  >
    {session.status.text}
  </p>

  <SessionPanel {session} />

  {#if session.groups.length}
    <Filters {session} />
  {/if}

  <p
    id="vc-reconciliation"
    role="status"
    aria-live="polite"
    class={session.reconciliation ? 'alert alert-warning' : 'sr-only'}
  >
    {session.reconciliation}
  </p>

  <section
    class="flex flex-col gap-4"
    aria-labelledby="vc-list-title"
    bind:this={list}
  >
    <div class="flex flex-wrap items-baseline justify-between gap-2">
      <h2 id="vc-list-title" tabindex="-1" class="text-xl font-semibold" bind:this={listHeading}>
        Duplicate groups
      </h2>
      <p id="vc-scope" role="status" aria-live="polite" class="font-semibold">{session.scope}</p>
    </div>

    {#if session.envelope === null}
      <p class="alert" data-empty="waiting">Waiting for the review server.</p>
    {:else if session.envelope.snapshot === null}
      <p class="alert" data-empty="no-report">
        Nothing to show because no report is loaded. Upload a DIM armor export on the
        <a class="link" href="/">main review page</a>, then use Reload report.
      </p>
    {:else if session.groups.length === 0}
      <p class="alert" data-empty="no-groups">
        The loaded report has no armor duplicate groups, so there is nothing to compare.
      </p>
    {:else if session.shown.length === 0}
      <p class="alert" data-empty="filtered">
        No group matches the filters.
        <button type="button" class="btn btn-sm" onclick={() => session.resetFilters()}>Reset filters</button>
      </p>
    {/if}

    {#each sections as section (section.kind)}
      <div>
        <h3 class="text-lg font-semibold" data-section={section.kind}>{SECTION_COPY[section.kind].heading}</h3>
        <p class="text-sm">{SECTION_COPY[section.kind].rule}</p>
      </div>
      {#each section.groups as group (group.key)}
        <GroupCard {group} {session} />
      {/each}
    {/each}
  </section>
</main>
