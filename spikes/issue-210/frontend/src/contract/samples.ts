// The type contract with Python (experiment S11).
//
// The JSON files are written by `spikes/issue-206/contract.py` from the real
// server.  Assigning them to `Envelope` makes `npm run check` fail when a
// field this slice reads is renamed, removed or retyped on the Python side.

import type { Envelope } from '../lib/envelope';
import finalized from './finalized.json';
import reviewing from './reviewing.json';

export const samples: { reviewing: Envelope; finalized: Envelope } = { reviewing, finalized };
