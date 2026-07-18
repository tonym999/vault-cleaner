# Worklog

Newest first. One entry per working session: what happened, decisions made,
surprises the next agent should know about.

## 2026-07-18 — Repo bootstrap, M1, ghosts, published

- Initialized repo from PLAN.md; `data/` gitignored from the first commit.
  Layout: `src/vault_cleaner/` (parse, report, cli, rules/), `tests/`,
  `wishlists/`, `data/in|out/`, `config.toml` stub.
- **M1 done.** `vault-cleaner roundtrip` parses a DIM export by header name
  (loud `SchemaError` on drift), tags one sacrificial item, writes a DIM
  `Id/Hash/Tag/Notes` import CSV. Dry-run default, `--write` to emit.
  Verified against a real export (684 weapons). *DIM import of
  `data/out/dim-import.csv` still pending manual confirmation in DIM.*
- **Ghost support added** (`--kind ghosts`). Ghost exports lack the `Type`
  column, which forced per-kind schema sets — see AGENTS.md gotchas.
- **Finding:** "A Good Shout" exists under two different item hashes
  (seasonal reissue). Dupe resolution (M2) must group by `Hash`, not name.
- Published to https://github.com/tonym999/vault-cleaner (public). Verified
  no vault data anywhere in git history first.
- Decisions: pandas as the only runtime dep; fixtures pinned to real export
  headers with fake rows; `wishlists/` gitignored for now (PLAN.md marks it
  TBD).
