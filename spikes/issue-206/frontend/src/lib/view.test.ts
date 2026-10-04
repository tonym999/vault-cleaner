import { describe, expect, it } from 'vitest';
import { samples } from '../contract/samples';
import type { Envelope } from './envelope';
import { duplicateGroups, statViews } from './view';

const groups = duplicateGroups(samples.reviewing);
const [exact, sameStat] = groups;

describe('duplicateGroups', () => {
  it('lists exact groups first, then same-stat, in server order', () => {
    expect(groups.map((group) => group.key)).toEqual(['exact:6031', 'same_stat:6081']);
  });

  it('is empty without a report', () => {
    expect(duplicateGroups(null)).toEqual([]);
    expect(duplicateGroups({ ...samples.reviewing, snapshot: null })).toEqual([]);
  });

  it('takes the disposition and proposal from the server', () => {
    const [survivor, junk] = exact!.members;
    expect(survivor).toMatchObject({ status: 'Preferred survivor', proposal: null, hasControls: false });
    expect(junk).toMatchObject({
      status: 'Proposed junk',
      proposal: { action: 'junk', reason: { text: 'armor-exact-dupe' } },
      hasControls: true,
      verdict: 'vetoed',
    });
  });

  it('gives an exact member controls only when the member itself is the proposal', () => {
    // A survivor that a later pass also proposed: shown, but read-only here.
    const envelope: Envelope = structuredClone(samples.reviewing);
    const section = envelope.snapshot!.sections[0]!;
    section.decisions.push({ id: '6031', hash: '940', action: 'review', reason: 'armor-similar to' });
    const survivor = duplicateGroups(envelope)[0]!.members[0]!;
    expect(survivor.proposal).toEqual({ action: 'review', reason: { text: 'armor-similar to', unknown: false } });
    expect(survivor.hasControls).toBe(false);
  });

  it('gives a same-stat member controls only when the section has a proposal for it', () => {
    expect(sameStat!.members.map((member) => member.hasControls)).toEqual([true, true]);
    const envelope: Envelope = structuredClone(samples.reviewing);
    const section = envelope.snapshot!.sections[0]!;
    section.decisions = section.decisions.filter((decision) => decision.id !== '6082');
    const members = duplicateGroups(envelope)[1]!.members;
    expect(members.map((member) => member.hasControls)).toEqual([true, false]);
    expect(members[1]!.status).toBe('Comparison only');
  });

  it('splits fields into shared and differing, losing none', () => {
    expect(exact!.differing.map((field) => field.key)).toEqual(['masterwork_tier']);
    expect(exact!.shared.map((fact) => fact.key)).toEqual([
      'tuning_mod_slot', 'protection', 'in_loadout', 'equipped', 'locked', 'power',
    ]);
    expect(sameStat!.differing.map((field) => field.key)).toEqual(['tuning_mod_slot', 'tuning_stat']);
    for (const group of groups) {
      for (const member of group.members) {
        for (const field of group.differing) expect(member.cells[field.key]).toBeDefined();
      }
    }
  });

  it('marks absent values so they never look real', () => {
    expect(exact!.facts.find((fact) => fact.key === 'item_archetype')!.cell).toEqual({ text: 'none', unknown: true });
    expect(exact!.shared.find((fact) => fact.key === 'protection')!.cell.unknown).toBe(true);
    const envelope: Envelope = structuredClone(samples.reviewing);
    envelope.snapshot!.sections[0]!.armor!.exact_duplicate_groups[0]!.members[0]!.power = null;
    const cell = duplicateGroups(envelope)[0]!.members[0]!.cells.power;
    expect(cell).toEqual({ text: 'unknown', unknown: true });
  });

  it('reads verdicts and active persisted vetoes from the adopted envelope only', () => {
    expect(exact!.members[1]!.persistedVeto).toBe(false);
    const after = duplicateGroups(samples.finalized);
    expect(after[0]!.members[1]).toMatchObject({ verdict: 'vetoed', persistedVeto: true });
    expect(after[1]!.members[0]).toMatchObject({ verdict: 'approved', persistedVeto: false });
  });

  it('keeps ids and hashes as the strings they arrived as', () => {
    const envelope: Envelope = structuredClone(samples.reviewing);
    const group = envelope.snapshot!.sections[0]!.armor!.exact_duplicate_groups[0]!;
    group.hash = '007';
    group.members[0]!.id = '18446744073709551615';
    const view = duplicateGroups(envelope)[0]!;
    expect(view.hash).toBe('007');
    expect(view.facts.find((fact) => fact.key === 'hash')!.cell.text).toBe('007');
    expect(view.members[0]!.id).toBe('18446744073709551615');
  });
});

describe('statViews', () => {
  it('names the three roles of a tier-5 spike and puts them first', () => {
    const stats = { class: 0, grenade: 25, health: 0, melee: 30, super: 20, weapons: 0 };
    expect(statViews(stats, 5).map((stat) => `${stat.name}:${stat.role}`)).toEqual([
      'melee:primary', 'grenade:secondary', 'super:tertiary', 'class:', 'health:', 'weapons:',
    ]);
  });

  it('assigns no role without the exact spike, or below tier 5', () => {
    const stats = { class: 0, grenade: 25, health: 0, melee: 30, super: 20, weapons: 0 };
    expect(statViews(stats, 4).every((stat) => stat.role === '')).toBe(true);
    expect(statViews({ ...stats, class: 5 }, 5).every((stat) => stat.role === '')).toBe(true);
  });
});
