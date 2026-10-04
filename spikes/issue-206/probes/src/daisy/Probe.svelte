<script lang="ts">
  // daisyUI 5.7.47: CSS classes on native elements; no JavaScript of its own.
  let pressed = $state(false);
  let choice = $state('a');
  let dialog: HTMLDialogElement;
</script>

<h1 class="text-xl">daisyUI</h1>
<button type="button" class="btn btn-primary" data-probe="button">Button</button>
<button
  type="button"
  class="btn"
  class:btn-active={pressed}
  data-probe="toggle"
  aria-pressed={pressed}
  onclick={() => (pressed = !pressed)}
>
  Toggle
</button>
<select class="select w-40" data-probe="select" bind:value={choice}>
  <option value="a">A</option>
  <option value="b">B</option>
</select>
<button type="button" class="btn" data-probe="overlay-open" onclick={() => dialog.showModal()}>
  Open dialog
</button>
<dialog class="modal" bind:this={dialog} data-probe="overlay">
  <div class="modal-box"><p>A native dialog with daisyUI classes.</p></div>
</dialog>
