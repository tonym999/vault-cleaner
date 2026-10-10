// Presentation of the Armor duplicates surface, as pure functions of the
// adopted envelope.
//
// Nothing here decides grouping, member order, the survivor, a disposition
// or which members carry a proposal.  Those are read: groups and members in
// the order the server sent them, `disposition` and `proposal_action` from
// each member, and the proposal itself by looking the member's id up in its
// section's `decisions`.  What this module adds is wording and layout data.

import type {
  Decision,
  Envelope,
  ExactGroup,
  ExactMember,
  MemberBase,
  SameStatGroup,
  SameStatMember,
} from './envelope';

export type GroupKind = 'exact' | 'same_stat';
export type Verdict = '' | 'approved' | 'vetoed';

/** A value to print.  `unknown` marks an absent value so it never looks real. */
export interface Cell {
  text: string;
  unknown: boolean;
}

export interface Fact {
  key: string;
  label: string;
  cell: Cell;
}

export interface StatView {
  name: string;
  value: number;
  /** Tier-5 role, or '' when the piece has no 30/25/20 spike. */
  role: '' | 'primary' | 'secondary' | 'tertiary';
}

export interface MemberView {
  id: string;
  location: Cell;
  /** Exact group: the server's disposition.  Same-stat: proposal or not. */
  status: string;
  /** The member's value for every comparison field of its group. */
  cells: Record<string, Cell>;
  proposal: { action: string; reason: Cell } | null;
  hasControls: boolean;
  verdict: Verdict;
  persistedVeto: boolean;
}

export interface GroupView {
  key: string;
  kind: GroupKind;
  id: string;
  hash: string;
  name: Cell;
  facts: Fact[];
  stats: StatView[];
  /** Fields with one value across every member, and group-level values. */
  shared: Fact[];
  /** Fields whose values differ between members: shown on every member. */
  differing: { key: string; label: string }[];
  members: MemberView[];
  /** The raw values the filter facets match on. */
  guardianClass: string;
}

interface Field<M> {
  key: string;
  label: string;
  cell: (member: M) => Cell;
}

const real = (text: string): Cell => ({ text, unknown: false });
const absent = (text: string): Cell => ({ text, unknown: true });

export const categorical = (value: string): Cell => (value === '' ? absent('none') : real(value));
/** The server writes this sentinel when a piece has no known Tuning Mod Slot. */
const TUNING_MOD_SLOT_UNKNOWN = 'none/unknown';
const tuningSlot = (value: string): Cell =>
  value === TUNING_MOD_SLOT_UNKNOWN ? absent(value) : categorical(value);
const yesNo = (value: boolean): Cell => real(value ? 'Yes' : 'No');
const count = (value: number | null): Cell =>
  value === null ? absent('unknown') : real(String(value));

function protection(member: MemberBase): Cell {
  if (member.protection_level === null || member.protection_level === '') return absent('none');
  return real(
    member.protection_reason
      ? `${member.protection_level} — ${member.protection_reason}`
      : member.protection_level,
  );
}

const COMMON_FIELDS: Field<MemberBase>[] = [
  { key: 'protection', label: 'Protection', cell: protection },
  { key: 'in_loadout', label: 'In loadout', cell: (m) => yesNo(m.in_loadout) },
  { key: 'equipped', label: 'Equipped', cell: (m) => yesNo(m.equipped) },
  { key: 'locked', label: 'Locked', cell: (m) => yesNo(m.locked) },
  { key: 'masterwork_tier', label: 'Masterwork tier', cell: (m) => count(m.masterwork_tier) },
  { key: 'power', label: 'Power', cell: (m) => count(m.power) },
];

const SAME_STAT_FIELDS: Field<SameStatMember>[] = [
  { key: 'tuning_mod_slot', label: 'Tuning Mod Slot', cell: (m) => tuningSlot(m.tuning_mod_slot) },
  { key: 'tuning_stat', label: 'Tuning Stat', cell: (m) => categorical(m.tuning_stat) },
  { key: 'seasonal_mod', label: 'Seasonal Mod', cell: (m) => categorical(m.seasonal_mod) },
  { key: 'holofoil', label: 'Holofoil', cell: (m) => categorical(m.holofoil) },
  ...COMMON_FIELDS,
];

const DISPOSITIONS: Record<string, string> = {
  preferred_survivor: 'Preferred survivor',
  retained_protected: 'Retained, protected',
  proposed_junk: 'Proposed junk',
  proposed_review: 'Proposed review',
};

/** The disposition that goes with each proposal action, as the server pairs them. */
const PROPOSAL_DISPOSITIONS: Record<string, string> = {
  proposed_junk: 'junk',
  proposed_review: 'review',
};
const VERDICT_ACTIONS = new Set(['junk', 'review']);

export const VERDICT_LABELS: Record<Verdict, string> = {
  '': 'Unreviewed',
  approved: 'Approved',
  vetoed: 'Vetoed',
};

export const PERSISTED_VETO_NOTE =
  'A veto saved from an earlier review still suppresses this item.';

const SPIKE_ROLES = [
  [30, 'primary'],
  [25, 'secondary'],
  [20, 'tertiary'],
] as const;

/** Tier-5 pieces carry a fixed 30/25/20 spike; the envelope has no role field. */
export function statViews(stats: Record<string, number>, tier: number | null): StatView[] {
  const entries = Object.entries(stats);
  const values = entries.map(([, value]) => value);
  const times = (wanted: number) => values.filter((value) => value === wanted).length;
  const spike =
    tier === 5 &&
    entries.length === 6 &&
    SPIKE_ROLES.every(([value]) => times(value) === 1) &&
    times(0) === 3;
  if (!spike) return entries.map(([name, value]) => ({ name, value, role: '' }));
  const spiked = SPIKE_ROLES.map(([value, role]) => {
    const [name] = entries.find(([, candidate]) => candidate === value)!;
    return { name, value, role };
  });
  const rest = entries
    .filter(([, value]) => value === 0)
    .map(([name, value]) => ({ name, value, role: '' as const }));
  return [...spiked, ...rest];
}

interface Lookups {
  proposals: Map<string, Decision>;
  verdicts: Map<string, string>;
  persistedVetoes: Set<string>;
}

function memberView<M extends MemberBase>(
  member: M,
  fields: Field<M>[],
  status: string,
  canVerdict: (decision: Decision) => boolean,
  lookups: Lookups,
): MemberView {
  const decision = lookups.proposals.get(member.id);
  const verdict = lookups.verdicts.get(member.id);
  return {
    id: member.id,
    location: member.location === '' ? absent('unknown') : real(member.location),
    status,
    cells: Object.fromEntries(fields.map((field) => [field.key, field.cell(member)])),
    proposal: decision
      ? { action: decision.action, reason: categorical(decision.reason) }
      : null,
    hasControls: decision !== undefined && canVerdict(decision),
    verdict: verdict === 'approved' || verdict === 'vetoed' ? verdict : '',
    persistedVeto: lookups.persistedVetoes.has(member.id),
  };
}

function split<M>(fields: Field<M>[], members: MemberView[]) {
  const shared: Fact[] = [];
  const differing: { key: string; label: string }[] = [];
  for (const { key, label } of fields) {
    const texts = new Set(members.map((member) => member.cells[key]!.text));
    if (texts.size > 1) differing.push({ key, label });
    else shared.push({ key, label, cell: members[0]!.cells[key]! });
  }
  return { shared, differing };
}

function groupFacts(group: ExactGroup | SameStatGroup): Fact[] {
  return [
    { key: 'item_archetype', label: 'Archetype', cell: categorical(group.item_archetype) },
    { key: 'type', label: 'Type / slot', cell: categorical(group.type) },
    { key: 'guardian_class', label: 'Class', cell: categorical(group.guardian_class) },
    { key: 'tier', label: 'Tier', cell: count(group.tier) },
    { key: 'hash', label: 'Hash', cell: real(group.hash) },
  ];
}

function extras(group: ExactGroup | SameStatGroup): Fact[] {
  return group.spirit_signature.length
    ? [{ key: 'spirit_signature', label: 'Spirit signature', cell: real(group.spirit_signature.join(' · ')) }]
    : [];
}

/** What both kinds of group show the same way. */
function commonView(group: ExactGroup | SameStatGroup) {
  return {
    id: group.group_id,
    hash: group.hash,
    name: group.name === '' ? absent('Unnamed armor') : real(group.name),
    facts: groupFacts(group),
    stats: statViews(group.stats, group.tier),
    guardianClass: group.guardian_class,
  };
}

function exactView(group: ExactGroup, lookups: Lookups): GroupView {
  const members = group.members.map((member: ExactMember) =>
    memberView(
      member,
      COMMON_FIELDS,
      DISPOSITIONS[member.disposition] ?? member.disposition,
      // Production's rule (review_ui.js, isProposalMember): the disposition and
      // the member's own proposal action agree.  The section's proposal must
      // carry the same action.
      (decision) =>
        PROPOSAL_DISPOSITIONS[member.disposition] === decision.action &&
        member.proposal_action === decision.action,
      lookups,
    ),
  );
  const { shared, differing } = split(COMMON_FIELDS, members);
  const groupLevel: Fact[] = [
    { key: 'tuning_mod_slot', label: 'Tuning Mod Slot', cell: tuningSlot(group.tuning_mod_slot) },
  ];
  if (group.seasonal_mod !== '') {
    groupLevel.push({ key: 'seasonal_mod', label: 'Seasonal Mod', cell: real(group.seasonal_mod) });
  }
  if (group.holofoil !== '' && group.holofoil.toLowerCase() !== 'false') {
    groupLevel.push({ key: 'holofoil', label: 'Holofoil', cell: real(group.holofoil) });
  }
  return {
    ...commonView(group),
    key: `exact:${group.group_id}`,
    kind: 'exact',
    shared: [...groupLevel, ...extras(group), ...shared],
    differing,
    members,
  };
}

function sameStatView(group: SameStatGroup, lookups: Lookups): GroupView {
  const members = group.members.map((member) =>
    memberView(
      member,
      SAME_STAT_FIELDS,
      lookups.proposals.has(member.id)
        ? `Existing proposal: ${lookups.proposals.get(member.id)!.action}`
        : 'Comparison only',
      // Production's rule (armorMemberCanVerdict): the section's proposal for
      // this member is exactly junk or review.
      (decision) => VERDICT_ACTIONS.has(decision.action),
      lookups,
    ),
  );
  const { shared, differing } = split(SAME_STAT_FIELDS, members);
  return {
    ...commonView(group),
    key: `same_stat:${group.group_id}`,
    kind: 'same_stat',
    shared: [...extras(group), ...shared],
    differing,
    members,
  };
}

/** Every duplicate group: exact first, then same-stat, each in server order. */
export function duplicateGroups(envelope: Envelope | null, previous: GroupView[] = []): GroupView[] {
  if (!envelope?.snapshot) return [];
  const verdicts = new Map(envelope.verdicts.map((entry) => [entry.id, entry.verdict]));
  const persistedVetoes = new Set(
    envelope.override_status.filter((entry) => entry.status === 'active').map((entry) => entry.id),
  );
  const exact: GroupView[] = [];
  const sameStat: GroupView[] = [];
  for (const section of envelope.snapshot.sections) {
    if (!section.armor) continue;
    const lookups: Lookups = {
      proposals: new Map(section.decisions.map((decision) => [decision.id, decision])),
      verdicts,
      persistedVetoes,
    };
    for (const group of section.armor.exact_duplicate_groups) exact.push(exactView(group, lookups));
    for (const group of section.armor.same_stat_groups) sameStat.push(sameStatView(group, lookups));
  }
  const oldGroups = new Map(previous.map((group) => [group.key, group]));
  return [...exact, ...sameStat].map((group) => {
    const old = oldGroups.get(group.key);
    if (!old) return group;
    const members = new Map(old.members.map((member) => [member.id, member]));
    group.members = group.members.map((member) => retain(members.get(member.id), member));
    group.name = retain(old.name, group.name);
    group.facts = retain(old.facts, group.facts);
    group.stats = retain(old.stats, group.stats);
    group.shared = retain(old.shared, group.shared);
    group.differing = retain(old.differing, group.differing);
    group.members = retain(old.members, group.members);
    return retain(old, group);
  });
}

export const SECTION_COPY: Record<GroupKind, { heading: string; rule: string }> = {
  exact: {
    heading: 'Exact duplicates',
    rule: 'Same item, same stats, same tuning. One copy survives.',
  },
  same_stat: {
    heading: 'Same stats, different tuning',
    rule: 'Review only. No survivor is chosen, because the tuning is yours to pick.',
  },
};

export const pieces = (groups: GroupView[]): number =>
  groups.reduce((sum, group) => sum + group.members.length, 0);

/** Complete presented-value equality, independent of every revision or fingerprint. */
export function sameView(left: unknown, right: unknown): boolean {
  if (left === right) return true;
  if (left === null || right === null || typeof left !== 'object' || typeof right !== 'object') return false;
  if (Array.isArray(left) !== Array.isArray(right)) return false;
  const a = Object.keys(left);
  const b = Object.keys(right);
  const l = left as Record<string, unknown>;
  const r = right as Record<string, unknown>;
  return a.length === b.length && a.every((key) => Object.hasOwn(r, key) && sameView(l[key], r[key]));
}

function retain<T>(previous: T | undefined, next: T): T {
  return previous !== undefined && sameView(previous, next) ? previous : next;
}

/** The exact group's survivor, which the page marks as the piece that is kept. */
export const isKept = (group: GroupView, member: MemberView): boolean =>
  group.kind === 'exact' && member.status === DISPOSITIONS.preferred_survivor;

/**
 * Whether one "Tuned stat" value can stand for both Tuning Mod Slot and
 * Tuning Stat: true when every piece's two values agree, ignoring case.
 * When any piece disagrees the page shows both fields for the whole group.
 */
export function tunedStatMerged(group: GroupView): boolean {
  if (group.kind !== 'same_stat') return false;
  return group.members.every((member) => {
    const slot = member.cells.tuning_mod_slot;
    const stat = member.cells.tuning_stat;
    return slot !== undefined && stat !== undefined && slot.text.toLowerCase() === stat.text.toLowerCase();
  });
}
