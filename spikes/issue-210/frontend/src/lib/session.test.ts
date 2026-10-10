import { describe, expect, it } from 'vitest';
import { samples } from '../contract/samples';
import type { Api, Failure, Result, VerdictRequest } from './api';
import type { Envelope } from './envelope';
import { ReviewSession } from './session.svelte';

const ok = <T>(value: T): Result<T> => ({ ok: true, value });
const refuse = (failure: Failure): Result<never> => ({ ok: false, failure });
const http = (status: number, code: string, message = ''): Failure => ({ kind: 'http', status, code, message });

const unreviewed: Envelope = { ...samples.reviewing, verdicts: [], verdict_revision: 0 };

/** A scripted server: each call takes the next queued answer. */
function fakeApi(script: {
  report?: Result<Envelope>[];
  verdicts?: Result<Envelope>[];
  finalize?: Result<null>[];
  reset?: Result<Envelope>[];
}) {
  const calls: { name: string; body?: unknown }[] = [];
  const next = <T>(name: string, queue: Result<T>[] | undefined, body?: unknown): Promise<Result<T>> => {
    calls.push({ name, body });
    const answer = queue?.shift();
    if (!answer) throw new Error(`unexpected ${name} request`);
    return Promise.resolve(answer);
  };
  const api: Api = {
    report: () => next('report', script.report),
    verdicts: (body) => next('verdicts', script.verdicts, body),
    finalize: (body) => next('finalize', script.finalize, body),
    reset: (body) => next('reset', script.reset, body),
  };
  return { api, calls };
}

async function loaded(script: Parameters<typeof fakeApi>[0], first: Envelope = unreviewed) {
  const fake = fakeApi({ ...script, report: [ok(first), ...(script.report ?? [])] });
  const session = new ReviewSession(fake.api);
  await session.load();
  return { session, calls: fake.calls };
}

const verdictOf = (session: ReviewSession, id: string) =>
  session.groups.flatMap((group) => group.members).find((member) => member.id === id)!.verdict;

describe('ReviewSession', () => {
  it('adopts the report and connects', async () => {
    const { session } = await loaded({});
    expect(session.connection).toBe('connected');
    expect(session.groups).toHaveLength(2);
    expect(session.scope).toBe('2 groups · 4 pieces');
    expect(session.canMutate).toBe(true);
  });

  it('sends the adopted revisions and the id unchanged, and shows nothing until the answer', async () => {
    let release!: (value: Result<Envelope>) => void;
    const held = new Promise<Result<Envelope>>((resolve) => (release = resolve));
    const fake = fakeApi({ report: [ok(unreviewed)] });
    const sent: VerdictRequest[] = [];
    fake.api.verdicts = (body) => {
      sent.push(body);
      return held;
    };
    const session = new ReviewSession(fake.api);
    await session.load();

    const pending = session.setVerdict('6032', 'vetoed');
    expect(sent).toEqual([
      { report_revision: 1, verdict_revision: 0, fingerprint: unreviewed.fingerprint, decisions: [{ id: '6032', verdict: 'vetoed' }] },
    ]);
    expect(verdictOf(session, '6032')).toBe('');
    expect(session.canMutate).toBe(false);

    release(ok(samples.reviewing));
    await pending;
    expect(verdictOf(session, '6032')).toBe('vetoed');
    expect(session.canMutate).toBe(true);
    expect(session.status).toEqual({ tone: 'ok', text: 'The server recorded your veto for item 6032.' });
  });

  it('ignores a second action while one is in flight', async () => {
    const { session, calls } = await loaded({ verdicts: [ok(samples.reviewing)] });
    const first = session.setVerdict('6032', 'vetoed');
    await session.setVerdict('6081', 'approved');
    await first;
    expect(calls.filter((call) => call.name === 'verdicts')).toHaveLength(1);
  });

  it.each(['stale_verdicts', 'stale_report'])('reconciles %s and does not replay', async (code) => {
    const { session, calls } = await loaded({
      verdicts: [refuse(http(409, code))],
      report: [ok(samples.reviewing)],
    });
    await session.setVerdict('6081', null);
    expect(calls.map((call) => call.name)).toEqual(['report', 'verdicts', 'report']);
    expect(session.envelope).toBe(samples.reviewing);
    expect(session.status.tone).toBe('error');
    expect(session.status.text).toContain('was not applied because the review changed');
    expect(session.canMutate).toBe(true);
  });

  it('reaches the frozen state when another tab finalised, without replaying', async () => {
    const { session, calls } = await loaded({
      verdicts: [refuse(http(409, 'illegal_state'))],
      report: [ok(samples.finalized)],
    });
    await session.setVerdict('6032', 'approved');
    expect(calls.map((call) => call.name)).toEqual(['report', 'verdicts', 'report']);
    expect(session.frozen).toBe(true);
    expect(session.canMutate).toBe(false);
    expect(session.status.text).toBe('Your approval was not applied: this review is finalised.');
  });

  it('shows the finalised state although neither revision moved', async () => {
    const { session, calls } = await loaded({ finalize: [ok(null)], report: [ok(samples.finalized)] }, samples.reviewing);
    const before = session.reportKey;
    await session.finalize();
    expect(calls.map((call) => call.name)).toEqual(['report', 'finalize', 'report']);
    expect(session.reportKey).toBe(before);
    expect(session.envelope!.verdict_revision).toBe(samples.reviewing.verdict_revision);
    expect(session.serverState).toBe('finalized');
    expect(session.frozen).toBe(true);
    const vetoed = session.groups[0]!.members[1]!;
    expect(vetoed.persistedVeto).toBe(true);
  });

  it('adopts the idle envelope after a reset', async () => {
    const idle: Envelope = { ...unreviewed, state: 'idle', snapshot: null, fingerprint: null, report_revision: 2 };
    const { session, calls } = await loaded({ reset: [ok(idle)] });
    await session.reset();
    expect(calls.at(-1)).toEqual({ name: 'reset', body: { report_revision: 1, verdict_revision: 0 } });
    expect(session.groups).toEqual([]);
    expect(session.serverState).toBe('idle');
  });

  it('keeps the report and the filters usable when the server stops', async () => {
    const envelope: Envelope = structuredClone(unreviewed);
    const { session } = await loaded({ verdicts: [refuse({ kind: 'transport' })] }, envelope);
    await session.setVerdict('6032', 'vetoed');
    expect(session.connection).toBe('disconnected');
    expect(session.canMutate).toBe(false);
    expect(session.canRequest).toBe(true);
    expect(verdictOf(session, '6032')).toBe('');
    session.setKind('exact');
    expect(session.shown.map((group) => group.key)).toEqual(['exact:6031']);
    expect(session.scope).toBe('1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates');
  });

  it('treats a lost login and an unreadable answer as terminal', async () => {
    for (const failure of [http(401, 'authentication_required'), { kind: 'incompatible' } as const]) {
      const fake = fakeApi({ report: [refuse(failure)] });
      const session = new ReviewSession(fake.api);
      await session.load();
      expect(session.connection).toBe('terminal');
      expect(session.canRequest).toBe(false);
    }
  });

  it('drops a filter the new report cannot satisfy and says so', async () => {
    const twoClass: Envelope = structuredClone(unreviewed);
    twoClass.snapshot!.sections[0]!.armor!.same_stat_groups[0]!.guardian_class = 'Hunter';
    const { session } = await loaded({ report: [ok(unreviewed)] }, twoClass);
    session.setFacet('guardian_class', 'Hunter');
    expect(session.reconciliation).toBe('');
    await session.load();
    expect(session.filters.facets).toEqual({});
    expect(session.reconciliation).toBe('Filter no longer applies and was cleared: class Hunter.');
  });
});
