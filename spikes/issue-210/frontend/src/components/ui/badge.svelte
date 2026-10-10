<script lang="ts" module>
  // From shadcn-svelte 1.7.0's generated badge. The variant table is as
  // generated, less the icon rules; the `ref` binding and link form are
  // removed, and the fixed height and nowrap are overridden where it is
  // used, because a status must wrap at 390 px and never be clipped.
  import { type VariantProps, tv } from 'tailwind-variants';

  export const badgeVariants = tv({
    base: 'h-5 gap-1 rounded-4xl border border-transparent px-2 py-0.5 text-xs font-medium transition-all group/badge inline-flex w-fit shrink-0 items-center justify-center overflow-hidden whitespace-nowrap',
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground',
        secondary: 'bg-secondary text-secondary-foreground',
        outline: 'border-border text-foreground',
      },
    },
    defaultVariants: { variant: 'default' },
  });

  export type BadgeVariant = VariantProps<typeof badgeVariants>['variant'];
</script>

<script lang="ts">
  import type { HTMLAttributes } from 'svelte/elements';
  import { cn } from './cn';

  let {
    class: className,
    variant = 'default',
    children,
    ...rest
  }: HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant } = $props();
</script>

<span
  data-slot="badge"
  class={cn(badgeVariants({ variant }), 'h-auto shrink whitespace-normal transition-none', className)}
  {...rest}
>
  {@render children?.()}
</span>
