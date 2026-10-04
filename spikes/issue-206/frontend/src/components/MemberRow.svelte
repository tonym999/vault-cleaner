<script lang="ts">
  import type { ReviewSession } from '../lib/session.svelte';
  import { PERSISTED_VETO_NOTE, VERDICT_LABELS, type GroupView, type MemberView } from '../lib/view';
  import Value from './Value.svelte';
  import VerdictControls from './VerdictControls.svelte';

  let {
    group,
    member,
    position,
    session,
  }: { group: GroupView; member: MemberView; position: number; session: ReviewSession } = $props();
</script>

<li class="rounded-box border border-base-300 p-3" data-member={member.id} data-verdict={member.verdict}>
  <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
    <span class="eyebrow">Piece {position}</span>
    <code class="font-mono text-sm" data-field="id">{member.id}</code>
    <span data-field="location"><Value cell={member.location} /></span>
    <span class="badge badge-outline" data-field="status">{member.status}</span>
  </div>

  {#if group.differing.length}
    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-[repeat(auto-fill,minmax(9rem,1fr))]">
      {#each group.differing as field (field.key)}
        <div class="min-w-0">
          <dt class="eyebrow">{field.label}</dt>
          <dd data-field={field.key}><Value cell={member.cells[field.key]!} /></dd>
        </div>
      {/each}
    </dl>
  {/if}

  {#if member.proposal}
    <div class="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-base-300 pt-3">
      <div class="min-w-0">
        <p>
          <span class="eyebrow">Proposed</span>
          <span class="font-semibold" data-field="proposal_action">{member.proposal.action}</span>
          <span class="eyebrow ml-2">Reason</span>
          <span data-field="proposal_reason"><Value cell={member.proposal.reason} /></span>
        </p>
        <p>
          <span class="eyebrow">Verdict</span>
          <span class="font-semibold" data-field="verdict">{VERDICT_LABELS[member.verdict]}</span>
        </p>
        {#if member.persistedVeto}
          <p class="mt-1 font-semibold" data-field="persisted_veto">{PERSISTED_VETO_NOTE}</p>
        {/if}
      </div>
      {#if member.hasControls}
        <VerdictControls {member} {session} />
      {:else}
        <p class="text-sm" data-field="read_only">Read-only here. Its proposal is decided on the Proposals page.</p>
      {/if}
    </div>
  {/if}
</li>
