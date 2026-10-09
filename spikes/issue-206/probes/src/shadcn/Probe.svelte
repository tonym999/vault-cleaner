<script lang="ts">
  // shadcn-svelte 1.7.0 as its CLI generated it (Bits UI underneath).
  import { Button } from '$lib/components/ui/button';
  import * as Dialog from '$lib/components/ui/dialog';
  import * as Select from '$lib/components/ui/select';
  import { Toggle } from '$lib/components/ui/toggle';

  let pressed = $state(false);
  let choice = $state('a');
</script>

<h1 class="text-xl">shadcn-svelte</h1>
<Button data-probe="button">Button</Button>
<Toggle data-probe="toggle" bind:pressed>Toggle</Toggle>
<Select.Root type="single" bind:value={choice}>
  <Select.Trigger data-probe="select" class="w-40">{choice}</Select.Trigger>
  <Select.Content>
    <Select.Item value="a" label="A" />
    <Select.Item value="b" label="B" data-probe="select-option" />
  </Select.Content>
</Select.Root>
<Dialog.Root>
  <Dialog.Trigger data-probe="overlay-open">Open dialog</Dialog.Trigger>
  <Dialog.Content data-probe="overlay">
    <Dialog.Header>
      <Dialog.Title>Dialog</Dialog.Title>
      <Dialog.Description>A Bits UI dialog.</Dialog.Description>
    </Dialog.Header>
  </Dialog.Content>
</Dialog.Root>
