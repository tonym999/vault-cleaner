<script lang="ts" module>
  import { buttonVariants } from './ui/button.svelte';
  import { cn } from './ui/cn';

  // shadcn's ghost button, joined into one control. `transition-none`
  // matters: every request switches all of these at once, and a transition
  // on each made that the slice's largest cost (#209). No rule may select on
  // aria-disabled either, so the switch restyles nothing.
  const BASE = cn(
    buttonVariants({ variant: 'ghost', size: 'sm' }),
    'verdict-button rounded-none transition-none aria-pressed:font-bold aria-pressed:underline aria-pressed:underline-offset-4',
  );
  const BUTTONS = [
    {
      label: 'Approve',
      shows: 'approved',
      sends: 'approved',
      class: cn(BASE, 'aria-pressed:bg-ok/25 aria-pressed:text-ok'),
    },
    {
      label: 'Veto',
      shows: 'vetoed',
      sends: 'vetoed',
      class: cn(BASE, 'aria-pressed:bg-no/25 aria-pressed:text-no'),
    },
    { label: 'Unset', shows: '', sends: null, class: BASE },
  ] as const;
</script>

<script lang="ts">
  import type { ReviewSession } from '../lib/session.svelte';
  import type { MemberView } from '../lib/view';

  // The buttons are switched off with aria-disabled, not `disabled`: Chromium
  // drops focus to <body> when the focused button becomes `disabled`, and a
  // verdict must never move focus (experiment S5).  The session ignores an
  // action it cannot take, so an aria-disabled button does nothing.
  let { member, session }: { member: MemberView; session: ReviewSession } = $props();
</script>

<div class="verdict" role="group" aria-label="Verdict for item {member.id}">
  {#each BUTTONS as button (button.label)}
    <button
      type="button"
      class={button.class}
      aria-pressed={member.verdict === button.shows}
      aria-label="{button.label} item {member.id}"
      aria-disabled={!session.canMutate}
      onclick={() => session.setVerdict(member.id, button.sends)}
    >
      {button.label}
    </button>
  {/each}
</div>
