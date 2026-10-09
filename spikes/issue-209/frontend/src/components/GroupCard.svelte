<script lang="ts">
  import type { ReviewSession } from '../lib/session.svelte';
  import type { GroupView } from '../lib/view';
  import MemberRow from './MemberRow.svelte';
  import StatList from './StatList.svelte';
  import Value from './Value.svelte';

  let { group, session }: { group: GroupView; session: ReviewSession } = $props();

  const uid = $props.id();
  const total = $derived(group.members.length);
</script>

<article
  class="card card-border bg-base-100 shadow-sm"
  aria-labelledby="{uid}-name"
  data-group={group.key}
  data-kind={group.kind}
>
  <div class="card-body gap-4 p-4 sm:p-6">
    <header class="flex flex-wrap items-start justify-between gap-2">
      <h4 id="{uid}-name" class="card-title" data-field="name">
        <Value cell={group.name} />
      </h4>
      <p class="flex flex-wrap items-center gap-2">
        <span class="badge {group.kind === 'exact' ? 'badge-primary' : 'badge-warning'}" data-field="kind">
          {group.kind === 'exact' ? 'Exact duplicates' : 'Same stats · review only'}
        </span>
        <span class="font-semibold" data-field="piece_count">{total} {total === 1 ? 'piece' : 'pieces'}</span>
      </p>
    </header>

    <dl class="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-5">
      {#each group.facts as fact (fact.key)}
        <div class="min-w-0">
          <dt class="eyebrow">{fact.label}</dt>
          <dd class={fact.key === 'hash' ? 'font-mono text-sm' : ''} data-field={fact.key}>
            <Value cell={fact.cell} />
          </dd>
        </div>
      {/each}
    </dl>

    <StatList stats={group.stats} />

    {#if group.kind === 'same_stat'}
      <p class="alert alert-warning" data-field="review_only">
        These pieces have the same base stats but different tuning, so no survivor is chosen. A piece
        has verdict buttons only if the report already proposes something for it.
      </p>
    {/if}

    <div>
      <h5 class="eyebrow mb-2">
        {total === 1 ? 'This piece' : `The same for all ${total} pieces`}
      </h5>
      <dl class="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-[repeat(auto-fill,minmax(9rem,1fr))]">
        {#each group.shared as fact (fact.key)}
          <div class="min-w-0">
            <dt class="eyebrow">{fact.label}</dt>
            <dd data-shared={fact.key}><Value cell={fact.cell} /></dd>
          </div>
        {/each}
      </dl>
    </div>

    <div>
      <h5 class="eyebrow mb-2">
        {group.differing.length ? 'Piece by piece: what differs' : 'Piece by piece'}
      </h5>
      <ol class="grid gap-2">
        {#each group.members as member, index (member.id)}
          <MemberRow {group} {member} position={index + 1} {session} />
        {/each}
      </ol>
    </div>
  </div>
</article>
