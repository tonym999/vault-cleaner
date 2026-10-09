// Requests to the unmodified Flask routes.  No state lives here.

import { isEnvelope, type Envelope } from './envelope';

export type Failure =
  | { kind: 'http'; status: number; code: string; message: string }
  | { kind: 'transport' }
  | { kind: 'incompatible' };

export type Result<T> = { ok: true; value: T } | { ok: false; failure: Failure };

export type Fetch = (input: string, init?: RequestInit) => Promise<Response>;

export interface VerdictRequest {
  report_revision: number;
  verdict_revision: number;
  fingerprint: string;
  decisions: { id: string; verdict: string | null }[];
}

export interface Api {
  report(): Promise<Result<Envelope>>;
  verdicts(body: VerdictRequest): Promise<Result<Envelope>>;
  finalize(body: Omit<VerdictRequest, 'decisions'>): Promise<Result<null>>;
  reset(body: Pick<VerdictRequest, 'report_revision' | 'verdict_revision'>): Promise<Result<Envelope>>;
}

const JSON_HEADERS = { 'Content-Type': 'application/json', Accept: 'application/json' };

async function httpFailure(response: Response): Promise<Failure> {
  // The server's error body is {"error": {"code", "message"}}.  Anything
  // else is reported by status alone.
  let code = '';
  let message = '';
  try {
    const body: unknown = await response.json();
    const error = (body as { error?: { code?: unknown; message?: unknown } }).error;
    if (typeof error?.code === 'string') code = error.code;
    if (typeof error?.message === 'string') message = error.message;
  } catch {
    // Not JSON: keep the status.
  }
  return { kind: 'http', status: response.status, code, message };
}

export function fetchApi(fetcher: Fetch): Api {
  async function send(path: string, init?: RequestInit): Promise<Result<Response>> {
    let response: Response;
    try {
      response = await fetcher(path, init);
    } catch {
      return { ok: false, failure: { kind: 'transport' } };
    }
    if (!response.ok) return { ok: false, failure: await httpFailure(response) };
    return { ok: true, value: response };
  }

  async function envelope(path: string, init?: RequestInit): Promise<Result<Envelope>> {
    const sent = await send(path, init);
    if (!sent.ok) return sent;
    try {
      const body: unknown = await sent.value.json();
      if (isEnvelope(body)) return { ok: true, value: body };
    } catch {
      // Fall through: a body that is not JSON is not ours either.
    }
    return { ok: false, failure: { kind: 'incompatible' } };
  }

  const post = (body: unknown): RequestInit => ({
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });

  return {
    report: () => envelope('/api/report', { headers: { Accept: 'application/json' } }),
    verdicts: (body) => envelope('/api/verdicts', post(body)),
    reset: (body) => envelope('/api/reset', post(body)),
    async finalize(body) {
      // The response is the reviewed CSV, not an envelope; the caller reads
      // the new state from /api/report afterwards.
      const sent = await send('/api/finalize', post(body));
      return sent.ok ? { ok: true, value: null } : sent;
    },
  };
}
