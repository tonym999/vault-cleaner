// Application logic: the adopted envelope, requests, the in-flight gate,
// stale-state reconciliation and the session lifecycle.
//
// The server is the only authority.  Nothing on screen changes for a verdict
// until the server's answer has been adopted, and a rejected action is never
// sent again.  Everything the page shows derives from `envelope`, so state
// the server changes without moving a revision (a finalise sets `state` and
// `override_status` and bumps neither) is shown as soon as an envelope
// carrying it is adopted.  Nothing is cached by revision.

import type { Api, Failure, Result } from './api';
import type { Envelope } from './envelope';
import {
  applyFilters,
  NO_FILTERS,
  reconcile,
  scopeText,
  type Filters,
  type KindFilter,
} from './filters';
import { duplicateGroups, sameView, type GroupView } from './view';

export type Connection = 'connecting' | 'connected' | 'disconnected' | 'terminal';
export type Tone = 'info' | 'ok' | 'error';

const FROZEN_STATES = new Set(['finalized', 'closed']);

export class ReviewSession {
  /** The last envelope the server sent.  Replaced whole; never edited. */
  envelope = $state.raw<Envelope | null>(null);
  connection = $state<Connection>('connecting');
  /** The request in flight, if any.  Mutation controls are off while set. */
  busy = $state<string | null>(null);
  status = $state.raw<{ tone: Tone; text: string }>({
    tone: 'info',
    text: 'Connecting to the local review server…',
  });
  /** What the last adoption or filter change dropped from the local view. */
  reconciliation = $state('');
  filters = $state.raw<Filters>(NO_FILTERS);

  groups = $state.raw<GroupView[]>([]);
  readonly shown = $derived(applyFilters(this.groups, this.filters));
  readonly scope = $derived(scopeText(this.groups, this.shown, this.filters));
  readonly serverState = $derived(this.envelope?.state ?? 'idle');
  readonly frozen = $derived(FROZEN_STATES.has(this.serverState));
  /** Changes exactly when the report does; used for the focus policy. */
  readonly reportKey = $derived(
    this.envelope ? `${this.envelope.report_revision}:${this.envelope.fingerprint}` : '',
  );
  readonly canMutate = $derived(
    this.connection === 'connected' && this.busy === null && !this.frozen,
  );
  readonly canReset = $derived(
    this.connection === 'connected' && this.busy === null && this.envelope?.snapshot != null,
  );
  readonly canRequest = $derived(this.connection !== 'terminal' && this.busy === null);

  readonly #api: Api;

  constructor(api: Api) {
    this.#api = api;
  }

  /** Read the current report.  Also the reconnect and "check again" action. */
  async load(): Promise<void> {
    if (!this.canRequest) return;
    this.busy = 'report';
    const result = await this.#api.report();
    this.busy = null;
    if (!result.ok) return this.#fail(result.failure, 'The report could not be loaded.');
    this.#adopt(result.value);
    this.#say(this.serverState === 'closed' ? 'error' : 'ok', this.#loadedText());
  }

  async setVerdict(id: string, verdict: 'approved' | 'vetoed' | null): Promise<void> {
    const envelope = this.envelope;
    if (!this.canMutate || !envelope || envelope.fingerprint === null) return;
    const action = verdict === 'approved' ? 'approval' : verdict === 'vetoed' ? 'veto' : 'unset';
    this.busy = 'verdict';
    const result = await this.#api.verdicts({
      report_revision: envelope.report_revision,
      verdict_revision: envelope.verdict_revision,
      fingerprint: envelope.fingerprint,
      decisions: [{ id, verdict }],
    });
    if (!result.ok) return this.#rejected(result.failure, `Your ${action}`);
    this.busy = null;
    this.#adopt(result.value);
    this.#say('ok', `The server recorded your ${action} for item ${id}.`);
  }

  async finalize(): Promise<void> {
    const envelope = this.envelope;
    if (!this.canMutate || !envelope || envelope.fingerprint === null) return;
    this.busy = 'finalize';
    const result = await this.#api.finalize({
      report_revision: envelope.report_revision,
      verdict_revision: envelope.verdict_revision,
      fingerprint: envelope.fingerprint,
    });
    if (!result.ok) return this.#rejected(result.failure, 'Finalising');
    // Finalising moves neither revision, so the frozen state and the saved
    // vetoes are only visible in a fresh envelope.
    const after = await this.#api.report();
    this.busy = null;
    if (!after.ok) {
      return this.#fail(after.failure, 'The review was finalised, but its new state could not be read.');
    }
    this.#adopt(after.value);
    this.#say('ok', 'Finalised. This review is frozen and its vetoes are saved.');
  }

  async reset(): Promise<void> {
    const envelope = this.envelope;
    if (!this.canReset || !envelope) return;
    this.busy = 'reset';
    const result = await this.#api.reset({
      report_revision: envelope.report_revision,
      verdict_revision: envelope.verdict_revision,
    });
    if (!result.ok) return this.#rejected(result.failure, 'The reset');
    this.busy = null;
    this.#adopt(result.value);
    this.#say('ok', 'The session was reset. No report is loaded.');
  }

  setKind(kind: KindFilter): void {
    this.#applyFilters({ ...this.filters, kind });
  }

  setFacet(key: string, value: string): void {
    this.#applyFilters({ ...this.filters, facets: { ...this.filters.facets, [key]: value } });
  }

  resetFilters(): void {
    this.#applyFilters(NO_FILTERS);
  }

  #applyFilters(wanted: Filters): void {
    const { filters, dropped } = reconcile(this.groups, wanted);
    if (!sameView(this.filters, filters)) this.filters = filters;
    this.reconciliation = dropped.length ? `Filter no longer applies and was cleared: ${dropped.join('; ')}.` : '';
  }

  #adopt(envelope: Envelope): void {
    this.groups = duplicateGroups(envelope, this.groups);
    this.envelope = envelope;
    this.connection = 'connected';
    this.#applyFilters(this.filters);
  }

  #loadedText(): string {
    switch (this.serverState) {
      case 'idle':
        return 'Connected. No report is loaded yet.';
      case 'finalized':
        return 'Connected. This review is finalised and frozen.';
      case 'closed':
        return 'This review session has ended.';
      default:
        return 'Connected. The report is loaded.';
    }
  }

  /**
   * A mutation the server refused.  It is reported and never replayed.  When
   * the refusal means the page is behind the server (a stale revision, or a
   * state that no longer accepts the action) the current report is read so
   * the page shows what is true now.
   */
  async #rejected(failure: Failure, what: string): Promise<void> {
    const behind =
      failure.kind === 'http' &&
      ['stale_report', 'stale_verdicts', 'illegal_state'].includes(failure.code);
    if (!behind) {
      this.busy = null;
      return this.#fail(failure, `${what} was not applied.`);
    }
    const current: Result<Envelope> = await this.#api.report();
    this.busy = null;
    if (!current.ok) {
      return this.#fail(current.failure, `${what} was not applied, and the current report could not be read.`);
    }
    this.#adopt(current.value);
    this.#say(
      'error',
      this.frozen
        ? `${what} was not applied: this review is ${this.serverState === 'closed' ? 'closed' : 'finalised'}.`
        : `${what} was not applied because the review changed. Repeat it if you still want it.`,
    );
  }

  #fail(failure: Failure, what: string): void {
    if (failure.kind === 'transport') {
      this.connection = 'disconnected';
      this.#say('error', `${what} The review server did not answer. Filters still work; use Reload to reconnect.`);
    } else if (failure.kind === 'incompatible') {
      this.connection = 'terminal';
      this.#say('error', `${what} The server's answer was not one this page understands. Reload the page.`);
    } else if (failure.status === 401) {
      this.connection = 'terminal';
      this.#say('error', `${what} The session is not authenticated. Restart vault-cleaner serve and open its new link.`);
    } else if (failure.code === 'illegal_state') {
      this.connection = 'terminal';
      this.#say('error', `${what} This review session has ended.`);
    } else {
      this.#say('error', `${what} ${failure.message || `The server answered HTTP ${failure.status}.`}`);
    }
  }

  #say(tone: Tone, text: string): void {
    this.status = { tone, text };
  }
}
