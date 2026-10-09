<script lang="ts">
  // One printed value.  An absent value is italic and marked, so it never
  // looks like a real one.
  import type { Cell } from '../lib/view';

  let { cell }: { cell: Cell } = $props();
</script>

<span class:italic={cell.unknown} data-unknown={cell.unknown ? '' : undefined}>
  {cell.text}
</span>
