<script lang="ts">
  import type { StatView } from '../lib/view';

  let { stats }: { stats: StatView[] } = $props();

  const top = $derived(Math.max(1, ...stats.map((stat) => stat.value)));
</script>

<ul class="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3" aria-label="Base stats">
  {#each stats as stat (stat.name)}
    <li data-stat={stat.name}>
      <div class="flex items-baseline justify-between gap-2">
        <span class="capitalize">{stat.name}</span>
        <span>
          <span class="font-semibold tabular-nums" data-field="stat_value">{stat.value}</span>
          {#if stat.role}
            <span class="badge badge-sm badge-primary badge-outline" data-field="stat_role">{stat.role}</span>
          {/if}
        </span>
      </div>
      <!-- Decoration: the number beside it is the value. -->
      <progress class="progress progress-primary h-1.5 w-full" value={stat.value} max={top} aria-hidden="true"
      ></progress>
    </li>
  {/each}
</ul>
