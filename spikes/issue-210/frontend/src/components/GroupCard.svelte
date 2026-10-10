<script lang="ts">
  import type { ReviewSession } from '../lib/session.svelte';
  import { tunedStatMerged, type GroupView } from '../lib/view';
  import Badge from './ui/badge.svelte';
  import PieceColumn from './PieceColumn.svelte';
  import StatStrip from './StatStrip.svelte';
  import Value from './Value.svelte';

  let { group, session }: { group: GroupView; session: ReviewSession } = $props();

  const uid = $props.id();
  const total = $derived(group.members.length);
  // One "Tuned stat" value stands for Tuning Mod Slot and Tuning Stat when
  // they agree on every piece; otherwise both fields are shown.
  const merged = $derived(tunedStatMerged(group));
  const hidden = (key: string) => merged && key === 'tuning_stat';
  const rows = $derived(group.differing.filter((field) => !hidden(field.key)));
  const shared = $derived(group.shared.filter((fact) => !hidden(fact.key)));
  // Facts whose value says what it is; the rest need their label shown.
  const SELF_EVIDENT = new Set(['item_archetype', 'type', 'guardian_class']);
</script>

<article
  class="group"
  aria-labelledby="{uid}-name"
  data-group={group.key}
  data-kind={group.kind}
>
  <div class="group-head">
    <header class="group-title">
      <h4 id="{uid}-name" data-field="name"><Value cell={group.name} /></h4>
      <p class="group-chips">
        <Badge variant="outline" class={group.kind === 'exact' ? 'border-primary/60 text-primary' : 'border-warn/60 text-warn'} data-field="kind">
          {group.kind === 'exact' ? 'Exact duplicates' : 'Same stats · review only'}
        </Badge>
        <span class="count" data-field="piece_count">{total} {total === 1 ? 'piece' : 'pieces'}</span>
      </p>
      <dl class="group-facts">
        {#each group.facts as fact (fact.key)}
          <div class:lead={fact.key === 'item_archetype'}>
            <dt class:sr-only={SELF_EVIDENT.has(fact.key) && !fact.cell.unknown}>{fact.label}</dt>
            <dd class:mono={fact.key === 'hash'} data-field={fact.key}><Value cell={fact.cell} /></dd>
          </div>
        {/each}
      </dl>
      {#if group.kind === 'same_stat'}
        <p class="sr-only" data-field="review_only">
          Review only: these pieces have the same base stats but different tuning, so no survivor is chosen.
        </p>
      {/if}
    </header>
    <StatStrip stats={group.stats} />
  </div>

  <ol class="matrix n{Math.min(total, 7)} r{rows.length + 3}">
    <li class="labels" aria-hidden="true">
      <div class="cell piece-head"></div>
      {#each rows as field (field.key)}
        <div class="cell" class:tuned={field.key === 'tuning_mod_slot'}>
          {merged && field.key === 'tuning_mod_slot' ? 'Tuned stat' : field.label}
        </div>
      {/each}
      <div class="cell">Proposal</div>
      <div class="cell verdict-cell">Verdict</div>
    </li>
    {#each group.members as member, index (member.id)}
      <PieceColumn {group} {member} position={index + 1} fields={rows} {merged} {session} />
    {/each}
  </ol>

  {#if shared.length}
    <dl class="shared">
      <dt class="shared-lead">{total === 2 ? 'Same on both' : `Same on all ${total}`}</dt>
      {#each shared as fact (fact.key)}
        <dd><span class="quiet">{fact.label}</span> <span data-shared={fact.key}><Value cell={fact.cell} /></span></dd>
      {/each}
    </dl>
  {/if}
</article>
