<script lang="ts">
  // Plain Svelte 5: a scoped style, a style: directive, a style attribute,
  // a spread style, a transition and a native dialog.
  import { fade, slide } from 'svelte/transition';

  let pressed = $state(false);
  let choice = $state('a');
  let open = $state(false);
  let dialog: HTMLDialogElement;
  const spread = { style: 'outline: 1px dotted' };
</script>

<h1>Plain Svelte 5</h1>
<button type="button" data-probe="button" onclick={() => (open = !open)}>Button</button>
<button type="button" data-probe="toggle" aria-pressed={pressed} onclick={() => (pressed = !pressed)}>
  Toggle
</button>
<select data-probe="select" bind:value={choice}>
  <option value="a">A</option>
  <option value="b">B</option>
</select>
<div class="bar" data-probe="style-directive" style:width={pressed ? '75%' : '25%'}></div>
<div class="bar" data-probe="style-attribute" style="width: {pressed ? 60 : 40}%"></div>
<div data-probe="style-spread" {...spread}>spread</div>
{#if open}
  <p data-probe="transition" transition:fade={{ duration: 50 }}>fade</p>
  <p data-probe="transition-slide" transition:slide={{ duration: 50 }}>slide</p>
{/if}
<button type="button" data-probe="overlay-open" onclick={() => dialog.showModal()}>Open dialog</button>
<dialog bind:this={dialog} data-probe="overlay"><p>Native dialog</p></dialog>

<style>
  h1 { font-size: 1.25rem; }
</style>
