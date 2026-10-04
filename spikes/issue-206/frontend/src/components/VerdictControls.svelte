<script lang="ts">
  import type { ReviewSession } from '../lib/session.svelte';
  import type { MemberView } from '../lib/view';

  // The buttons are switched off with aria-disabled, not `disabled`: Chromium
  // drops focus to <body> when the focused button becomes `disabled`, and a
  // verdict must never move focus (experiment S5).  The session ignores an
  // action it cannot take, so an aria-disabled button does nothing.
  let { member, session }: { member: MemberView; session: ReviewSession } = $props();

  const BUTTONS = [
    { label: 'Approve', shows: 'approved', sends: 'approved', pressed: 'btn-success' },
    { label: 'Veto', shows: 'vetoed', sends: 'vetoed', pressed: 'btn-error' },
    { label: 'Unset', shows: '', sends: null, pressed: 'btn-neutral' },
  ] as const;
</script>

<div class="join" role="group" aria-label="Verdict for item {member.id}">
  {#each BUTTONS as button (button.label)}
    {@const pressed = member.verdict === button.shows}
    <button
      type="button"
      class="btn btn-sm join-item {pressed ? `${button.pressed} font-bold underline` : 'font-normal'}"
      class:btn-disabled={!session.canMutate}
      aria-pressed={pressed}
      aria-label="{button.label} item {member.id}"
      aria-disabled={!session.canMutate}
      onclick={() => session.setVerdict(member.id, button.sends)}
    >
      {button.label}
    </button>
  {/each}
</div>
