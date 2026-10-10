<script lang="ts" module>
  // One fixed order for every group, so a stat is found by its position.
  export const STAT_ORDER = ['health', 'melee', 'grenade', 'super', 'class', 'weapons'];

  export const inStatOrder = <T extends { name: string }>(stats: T[]): T[] => {
    const rank = (name: string) => {
      const index = STAT_ORDER.indexOf(name);
      return index < 0 ? STAT_ORDER.length : index;
    };
    return [...stats].sort((a, b) => rank(a.name) - rank(b.name));
  };
</script>

<script lang="ts">
  import type { StatView } from '../lib/view';

  let { stats }: { stats: StatView[] } = $props();

  const ordered = $derived(inStatOrder(stats));
</script>

<ul class="strip" aria-label="Base stats">
  {#each ordered as stat (stat.name)}
    <li class="stat" class:zero={stat.value === 0} data-stat={stat.name} data-role={stat.role || undefined}>
      <span class="stat-name">{stat.name}</span>
      <span class="stat-value" data-field="stat_value">{stat.value}</span>
      {#if stat.role}
        <span class="stat-role" data-field="stat_role">{stat.role}</span>
      {/if}
    </li>
  {/each}
</ul>
