<script lang="ts">
  import { FACETS, facetOptions, hasBothKinds, ofKind, type KindFilter } from '../lib/filters';
  import type { ReviewSession } from '../lib/session.svelte';

  let { session }: { session: ReviewSession } = $props();

  const uid = $props.id();
  const KINDS: { value: KindFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'exact', label: 'Exact' },
    { value: 'same_stat', label: 'Same stats' },
  ];
</script>

<section class="card card-border bg-base-100" aria-labelledby="{uid}-title">
  <div class="card-body flex-row flex-wrap items-end gap-4 p-4">
    <h2 id="{uid}-title" class="sr-only">Filters</h2>
    {#if hasBothKinds(session.groups)}
      <div>
        <p class="eyebrow mb-1" id="{uid}-kind">Show</p>
        <div class="join" role="group" aria-labelledby="{uid}-kind">
          {#each KINDS as kind (kind.value)}
            {@const total = ofKind(session.groups, kind.value).length}
            {@const pressed = session.filters.kind === kind.value}
            <button
              type="button"
              class="btn btn-sm join-item {pressed ? 'btn-primary font-bold underline' : 'font-normal'}"
              aria-pressed={pressed}
              data-kind-filter={kind.value}
              onclick={() => session.setKind(kind.value)}
            >
              {kind.label} ({total})
            </button>
          {/each}
        </div>
      </div>
    {/if}
    {#each FACETS as facet (facet.key)}
      <label class="flex flex-col gap-1">
        <span class="eyebrow">{facet.label}</span>
        <select
          class="select select-sm w-56 max-w-full"
          data-facet={facet.key}
          value={session.filters.facets[facet.key] ?? ''}
          onchange={(event) => session.setFacet(facet.key, event.currentTarget.value)}
        >
          <option value="">{facet.anyLabel}</option>
          {#each facetOptions(session.groups, session.filters.kind, facet) as option (option.value)}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </label>
    {/each}
    <button type="button" class="btn btn-sm btn-ghost" onclick={() => session.resetFilters()}>
      Reset filters
    </button>
  </div>
</section>
