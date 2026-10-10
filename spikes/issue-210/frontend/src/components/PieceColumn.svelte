<script lang="ts">
  import type { ReviewSession } from '../lib/session.svelte';
  import { PERSISTED_VETO_NOTE, VERDICT_LABELS, isKept, type GroupView, type MemberView } from '../lib/view';
  import Badge from './ui/badge.svelte';
  import TunedStat from './TunedStat.svelte';
  import Value from './Value.svelte';
  import VerdictControls from './VerdictControls.svelte';

  let {
    group,
    member,
    position,
    fields,
    merged,
    session,
  }: {
    group: GroupView;
    member: MemberView;
    position: number;
    fields: { key: string; label: string }[];
    merged: boolean;
    session: ReviewSession;
  } = $props();

  const kept = $derived(isKept(group, member));
</script>

<li class="piece" class:kept data-member={member.id} data-verdict={member.verdict}>
  <div class="cell piece-head">
    <span class="piece-number">Piece {position}</span>
    <Badge
      variant={kept ? 'default' : 'outline'}
      class={kept ? '' : member.proposal ? 'border-dashed' : 'text-muted-foreground'}
      data-field="status">{member.status}</Badge
    >
    <span class="piece-where">
      <code data-field="id">{member.id}</code>
      <span data-field="location"><Value cell={member.location} /></span>
    </span>
  </div>

  <dl class="piece-fields">
    {#each fields as field (field.key)}
      {#if field.key === 'tuning_mod_slot'}
        <div class="cell tuned">
          <dt class="cell-label">{merged ? 'Tuned stat' : field.label}</dt>
          <dd class="tuned-value"><TunedStat cell={member.cells[field.key]!} {merged} /></dd>
        </div>
      {:else}
        <div class="cell">
          <dt class="cell-label">{field.label}</dt>
          <dd data-field={field.key}><Value cell={member.cells[field.key]!} /></dd>
        </div>
      {/if}
    {/each}
    <div class="cell proposal-cell">
      <dt class="cell-label">Proposal</dt>
      {#if member.proposal}
        <dd class="proposal">
          <span class="quiet">Proposed</span>
          <strong data-field="proposal_action">{member.proposal.action}</strong>
          <span class="quiet">because</span>
          <span data-field="proposal_reason"><Value cell={member.proposal.reason} /></span>
        </dd>
      {:else}
        <dd class="absent">none</dd>
      {/if}
    </div>
  </dl>

  <div class="cell verdict-cell">
    <span class="cell-label">Verdict</span>
    {#if member.proposal}
      {#if member.hasControls}
        <VerdictControls {member} {session} />
      {/if}
      <p class="verdict-state" data-state={member.verdict || 'none'}>
        <span data-field="verdict">{VERDICT_LABELS[member.verdict]}</span>
      </p>
      {#if member.persistedVeto}
        <p class="note" data-field="persisted_veto">{PERSISTED_VETO_NOTE}</p>
      {/if}
      {#if !member.hasControls}
        <p class="note" data-field="read_only">Read-only here. Its proposal is decided on the Proposals page.</p>
      {/if}
    {:else}
      <p class="note">No proposal, so there is nothing to decide.</p>
    {/if}
  </div>
</li>
