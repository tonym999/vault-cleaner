<script lang="ts">
  // The piece's tuned stat, marked at that stat's place in the group's stat
  // order. The boxes are decoration; the name beside them is the value.
  import type { Cell } from '../lib/view';
  import { STAT_ORDER } from './StatStrip.svelte';
  import Value from './Value.svelte';

  let { cell, merged }: { cell: Cell; merged: boolean } = $props();

  const tuned = $derived(cell.unknown ? '' : cell.text.toLowerCase());
</script>

<span class="tuned-boxes" aria-hidden="true">
  {#each STAT_ORDER as name (name)}
    <span class="tuned-box" class:on={name === tuned}>{name.charAt(0)}</span>
  {/each}
</span>
<span class="tuned-name" data-field="tuning_mod_slot" data-merged={merged ? 'tuning_stat' : undefined}>
  <Value {cell} />
</span>
