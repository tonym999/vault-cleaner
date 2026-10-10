<script lang="ts">
  import Filters from './components/Filters.svelte';
  import GroupCard from './components/GroupCard.svelte';
  import SessionPanel from './components/SessionPanel.svelte';
  import Button, { buttonVariants } from './components/ui/button.svelte';
  import type { ReviewSession } from './lib/session.svelte';
  import { SECTION_COPY, type GroupKind } from './lib/view';

  let { session }: { session: ReviewSession } = $props();

  const KINDS: GroupKind[] = ['exact', 'same_stat'];

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

<a class="{buttonVariants()} skip" href="#vc-title">Skip to review content</a>

<main class="page">
  <header class="page-head">
    <h1 id="vc-title" tabindex="-1">Armor duplicates</h1>
    <p class="quiet">vault-cleaner review · redesigned Svelte slice (#210)</p>
  </header>

  <p
    id="vc-status"
    role="status"
    aria-live="polite"
    class="notice"
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
    class={session.reconciliation ? 'notice' : 'sr-only'}
    data-tone="warn"
  >
    {session.reconciliation}
  </p>

  <!-- `frozen` is the long-lived case (finalised, closed, disconnected). A
       request in flight changes nothing visible on the controls. -->
  <section
    class="list"
    class:frozen={!session.canMutate && !session.busy}
    aria-labelledby="vc-list-title"
    bind:this={list}
  >
    <div class="list-head">
      <h2 id="vc-list-title" tabindex="-1" bind:this={listHeading}>Duplicate groups</h2>
      <p id="vc-scope" role="status" aria-live="polite">{session.scope}</p>
    </div>

    {#if session.envelope === null}
      <p class="notice" data-empty="waiting">Waiting for the review server.</p>
    {:else if session.envelope.snapshot === null}
      <p class="notice" data-empty="no-report">
        Nothing to show because no report is loaded. Upload a DIM armor export on the
        <a class="link" href="/">main review page</a>, then use Reload report.
      </p>
    {:else if session.groups.length === 0}
      <p class="notice" data-empty="no-groups">
        The loaded report has no armor duplicate groups, so there is nothing to compare.
      </p>
    {:else if session.shown.length === 0}
      <p class="notice" data-empty="filtered">
        No group matches the filters.
        <Button variant="outline" size="sm" onclick={() => session.resetFilters()}>Reset filters</Button>
      </p>
    {/if}

    {#each sections as section (section.kind)}
      <section class="kind kind-{section.kind}" aria-labelledby="vc-kind-{section.kind}">
        <div class="kind-head">
          <h3 id="vc-kind-{section.kind}" data-section={section.kind}>{SECTION_COPY[section.kind].heading}</h3>
          <p class="kind-rule">{SECTION_COPY[section.kind].rule}</p>
          <p class="count">{section.groups.length} {section.groups.length === 1 ? 'group' : 'groups'}</p>
        </div>
        <div class="groups">
          {#each section.groups as group (group.key)}
            <GroupCard {group} {session} />
          {/each}
        </div>
      </section>
    {/each}
  </section>
</main>
