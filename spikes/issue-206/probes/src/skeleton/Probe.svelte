<script lang="ts">
  // Skeleton 5.0.1: buttons and selects are CSS classes; the interactive
  // components are Zag.js machines.
  import { Dialog, Portal, ToggleGroup } from '@skeletonlabs/skeleton-svelte';

  let value = $state<string[]>([]);
  let choice = $state('a');
</script>

<h1 class="h3">Skeleton</h1>
<button type="button" class="btn preset-filled" data-probe="button">Button</button>
<ToggleGroup {value} onValueChange={(details) => (value = details.value)}>
  <ToggleGroup.Item value="on" data-probe="toggle">Toggle</ToggleGroup.Item>
</ToggleGroup>
<select class="select w-40" data-probe="select" bind:value={choice}>
  <option value="a">A</option>
  <option value="b">B</option>
</select>
<Dialog>
  <Dialog.Trigger class="btn preset-tonal" data-probe="overlay-open">Open dialog</Dialog.Trigger>
  <Portal>
    <Dialog.Backdrop class="fixed inset-0 bg-surface-50-950/50" />
    <Dialog.Positioner class="fixed inset-0 flex items-center justify-center">
      <Dialog.Content class="card bg-surface-100-900 p-4" data-probe="overlay">
        <Dialog.Title>Dialog</Dialog.Title>
        <Dialog.Description>A Zag.js dialog.</Dialog.Description>
      </Dialog.Content>
    </Dialog.Positioner>
  </Portal>
</Dialog>
