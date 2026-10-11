// Filtering of the groups the server sent.  It runs entirely in the browser,
// so it keeps working when the server has stopped.  A filter hides groups;
// it never changes what a group contains.

import { categorical, pieces, type GroupKind, type GroupView } from './view';

export type KindFilter = 'all' | GroupKind;

export interface Facet {
  key: string;
  label: string;
  anyLabel: string;
  /** The word the scope sentence uses for this facet. */
  scopeWord: string;
  value: (group: GroupView) => string;
}

export const FACETS: Facet[] = [
  {
    key: 'guardian_class',
    label: 'Class',
    anyLabel: 'any class',
    scopeWord: 'class',
    value: (group) => categorical(group.guardianClass).text,
  },
];

export interface Filters {
  kind: KindFilter;
  /** Facet key to selected value; '' means any. */
  facets: Record<string, string>;
}

export const NO_FILTERS: Filters = { kind: 'all', facets: {} };

export const ofKind = (groups: GroupView[], kind: KindFilter): GroupView[] =>
  kind === 'all' ? groups : groups.filter((group) => group.kind === kind);

export function applyFilters(groups: GroupView[], filters: Filters): GroupView[] {
  return ofKind(groups, filters.kind).filter((group) =>
    FACETS.every((facet) => {
      const wanted = filters.facets[facet.key] ?? '';
      return wanted === '' || facet.value(group) === wanted;
    }),
  );
}

export interface FacetOption {
  value: string;
  label: string;
}

/** A facet's options, counted over the groups of the selected kind. */
export function facetOptions(groups: GroupView[], kind: KindFilter, facet: Facet): FacetOption[] {
  const counts = new Map<string, number>();
  for (const group of ofKind(groups, kind)) {
    counts.set(facet.value(group), (counts.get(facet.value(group)) ?? 0) + 1);
  }
  return [...counts]
    .sort(([left], [right]) => left.localeCompare(right, 'en', { sensitivity: 'base' }))
    .map(([value, total]) => ({
      value,
      label: `${value} (${total} ${total === 1 ? 'group' : 'groups'})`,
    }));
}

export const hasBothKinds = (groups: GroupView[]): boolean =>
  groups.some((group) => group.kind === 'exact') &&
  groups.some((group) => group.kind === 'same_stat');

/**
 * Drop any selection the current groups can no longer satisfy, and say what
 * was dropped.  Called when the kind changes and when a report is adopted.
 */
export function reconcile(
  groups: GroupView[],
  filters: Filters,
): { filters: Filters; dropped: string[] } {
  const dropped: string[] = [];
  let kind = filters.kind;
  if (kind !== 'all' && !hasBothKinds(groups)) {
    dropped.push(kind === 'exact' ? 'exact duplicates only' : 'same-stat groups only');
    kind = 'all';
  }
  const facets: Record<string, string> = {};
  for (const facet of FACETS) {
    const selected = filters.facets[facet.key] ?? '';
    if (selected === '') continue;
    if (facetOptions(groups, kind, facet).some((option) => option.value === selected)) {
      facets[facet.key] = selected;
    } else {
      dropped.push(`${facet.scopeWord} ${selected}`);
    }
  }
  return { filters: { kind, facets }, dropped };
}

const plural = (total: number, word: string) => (total === 1 ? word : `${word}s`);

/** "2 groups · 4 pieces", or "1 of 2 groups · 2 of 4 pieces — filtered to …". */
export function scopeText(groups: GroupView[], shown: GroupView[], filters: Filters): string {
  const parts: string[] = [];
  if (filters.kind === 'exact') parts.push('exact duplicates');
  if (filters.kind === 'same_stat') parts.push('same-stat groups');
  for (const facet of FACETS) {
    const selected = filters.facets[facet.key] ?? '';
    if (selected !== '') parts.push(`${facet.scopeWord} ${selected}`);
  }
  const groupWord = plural(groups.length, 'group');
  const pieceWord = plural(pieces(groups), 'piece');
  if (!parts.length) return `${groups.length} ${groupWord} · ${pieces(groups)} ${pieceWord}`;
  return (
    `${shown.length} of ${groups.length} ${groupWord} · ` +
    `${pieces(shown)} of ${pieces(groups)} ${pieceWord} — filtered to ${parts.join(', ')}`
  );
}
