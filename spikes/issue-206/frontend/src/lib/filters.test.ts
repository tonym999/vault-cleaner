import { describe, expect, it } from 'vitest';
import { samples } from '../contract/samples';
import type { Envelope } from './envelope';
import { applyFilters, FACETS, facetOptions, NO_FILTERS, reconcile, scopeText } from './filters';
import { duplicateGroups } from './view';

// The exact group is Titan; make the same-stat group Hunter.
const envelope: Envelope = structuredClone(samples.reviewing);
envelope.snapshot!.sections[0]!.armor!.same_stat_groups[0]!.guardian_class = 'Hunter';
const groups = duplicateGroups(envelope);
const classFacet = FACETS[0]!;

describe('filters', () => {
  it('shows everything and counts it when nothing is selected', () => {
    expect(applyFilters(groups, NO_FILTERS)).toHaveLength(2);
    expect(scopeText(groups, groups, NO_FILTERS)).toBe('2 groups · 4 pieces');
  });

  it('filters by kind and by facet, and says so in the scope', () => {
    const filters = { kind: 'exact' as const, facets: { guardian_class: 'Titan' } };
    const shown = applyFilters(groups, filters);
    expect(shown.map((group) => group.key)).toEqual(['exact:6031']);
    expect(scopeText(groups, shown, filters)).toBe(
      '1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates, class Titan',
    );
  });

  it('recounts a facet for the selected kind', () => {
    expect(facetOptions(groups, 'all', classFacet).map((option) => option.label)).toEqual([
      'Hunter (1 group)', 'Titan (1 group)',
    ]);
    expect(facetOptions(groups, 'exact', classFacet).map((option) => option.label)).toEqual(['Titan (1 group)']);
  });

  it('drops a facet value the selected kind lacks, and reports it', () => {
    const result = reconcile(groups, { kind: 'exact', facets: { guardian_class: 'Hunter' } });
    expect(result.filters).toEqual({ kind: 'exact', facets: {} });
    expect(result.dropped).toEqual(['class Hunter']);
  });

  it('keeps a selection that still applies', () => {
    const filters = { kind: 'same_stat' as const, facets: { guardian_class: 'Hunter' } };
    expect(reconcile(groups, filters)).toEqual({ filters, dropped: [] });
  });

  it('drops a kind selection when the report no longer has both kinds', () => {
    const onlyExact = groups.filter((group) => group.kind === 'exact');
    expect(reconcile(onlyExact, { kind: 'same_stat', facets: {} })).toEqual({
      filters: NO_FILTERS,
      dropped: ['same-stat groups only'],
    });
  });
});
