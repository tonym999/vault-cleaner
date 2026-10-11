<script lang="ts">
  import { FACETS, facetOptions, hasBothKinds, ofKind, type KindFilter } from '../lib/filters';
  import type { ReviewSession } from '../lib/session.svelte';
  import Button from './ui/button.svelte';

  let { session }: { session: ReviewSession } = $props();

  const uid = $props.id();
  const KINDS: { value: KindFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'exact', label: 'Exact' },
    { value: 'same_stat', label: 'Same stats' },
  ];
</script>

<section class="filters" aria-labelledby="{uid}-title">
  <h2 id="{uid}-title" class="sr-only">Filters</h2>
  {#if hasBothKinds(session.groups)}
    <div class="filter">
      <p class="filter-label" id="{uid}-kind">Show</p>
      <div class="segments" role="group" aria-labelledby="{uid}-kind">
        {#each KINDS as kind (kind.value)}
          {@const total = ofKind(session.groups, kind.value).length}
          <Button
            variant="ghost"
            size="sm"
            class="segment rounded-none transition-none"
            aria-pressed={session.filters.kind === kind.value}
            data-kind-filter={kind.value}
            onclick={() => session.setKind(kind.value)}
          >
            {kind.label} ({total})
          </Button>
        {/each}
      </div>
    </div>
  {/if}
  {#each FACETS as facet (facet.key)}
    <label class="filter">
      <span class="filter-label">{facet.label}</span>
      <select
        class="select"
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
  <Button variant="ghost" size="sm" onclick={() => session.resetFilters()}>Reset filters</Button>
</section>
