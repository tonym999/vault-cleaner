import ast
from dataclasses import replace
from pathlib import Path

import pytest

from vault_cleaner import review
from vault_cleaner.report_run import run_report
from vault_cleaner.review_session import (
    ManifestDecision,
    merge_verdicts,
    retain_verdicts,
    same_proposal,
)

FIXTURES = Path(__file__).parent / "fixtures"
WEAPONS = FIXTURES / "weapons_dupes.csv"
ARMOR = FIXTURES / "armor.csv"
GHOSTS = FIXTURES / "ghosts_cleanup.csv"


def build_report(**kwargs):
    return run_report(
        config_path="nonexistent.toml",
        weapons_path=kwargs.pop("weapons_path", WEAPONS),
        armor_path=kwargs.pop("armor_path", ARMOR),
        ghosts_path=kwargs.pop("ghosts_path", GHOSTS),
        no_wishlists=True,
        **kwargs,
    )


def proposals(run):
    return [decision for section in run.sections for decision in section.decisions]


def replace_proposal(run, item_id, **changes):
    sections = []
    for section in run.sections:
        decisions = tuple(
            replace(decision, **changes) if decision.id == item_id else decision
            for decision in section.decisions
        )
        sections.append(replace(section, decisions=decisions))
    return replace(run, sections=tuple(sections))


def verdicts_for(*decisions, verdict="vetoed"):
    return [{"id": decision.id, "verdict": verdict} for decision in decisions]


def test_same_proposal_ignores_display_metadata_but_compares_all_identity_fields():
    run = build_report()
    decision = proposals(run)[0]
    display_only = replace(decision, name="renamed", owner="another vault")
    assert same_proposal(decision, display_only)
    assert not same_proposal(decision, replace(decision, id="different-id"))

    for field in ("kind", "hash", "action", "reason"):
        changed = replace(decision, **{field: f"changed-{field}"})
        assert not same_proposal(decision, changed)


@pytest.mark.parametrize("field", ["kind", "hash", "action", "reason"])
def test_retention_discards_each_identity_mutation_individually(field):
    old_run = build_report()
    decision = proposals(old_run)[0]
    # The test deliberately keeps the old fingerprint: retention is the
    # cross-fingerprint seam and must inspect proposal identity itself.
    new_run = replace_proposal(
        old_run,
        decision.id,
        **{field: f"changed-{field}"},
    )

    result = retain_verdicts(verdicts_for(decision), old_run, new_run)
    assert result.retained == ()
    assert result.discarded == (decision.id,)


def test_retention_discards_a_missing_proposal_and_keeps_an_unchanged_one():
    old_run = build_report()
    first, second = proposals(old_run)[:2]
    sections = []
    for section in old_run.sections:
        decisions = tuple(d for d in section.decisions if d.id != second.id)
        sections.append(replace(section, decisions=decisions))
    new_run = replace(old_run, sections=tuple(sections))

    result = retain_verdicts(verdicts_for(first, second), old_run, new_run)
    assert result.retained_ids == (first.id,)
    assert result.discarded_ids == (second.id,)


def test_manifest_merge_deliberately_ignores_mutated_display_fields():
    run = build_report()
    decision = proposals(run)[0]
    manifest_decision = ManifestDecision(
        id=decision.id,
        kind="ghosts",
        hash="not-the-run-hash",
        name="not-the-run-name",
        action="review",
        reason="not-the-run-reason",
        verdict="vetoed",
    )
    manifest = review.ReviewManifest(
        schema_version=1,
        snapshot_schema_version=1,
        ruleset_version=1,
        fingerprint=run.fingerprint,
        decisions=(manifest_decision,),
    )

    merged = review.merge_manifest(review.empty_store(), manifest, run)
    veto = merged.store.by_id()[decision.id]
    assert (veto.kind, veto.hash, veto.name) == (
        decision.kind,
        decision.hash,
        decision.name,
    )
    assert (veto.action, veto.reason) == (decision.action, decision.reason)


def test_manifest_adapter_and_manifest_free_core_have_the_same_result():
    run = build_report()
    decisions = proposals(run)[:3]
    manifest_decisions = tuple(
        ManifestDecision(
            id=decision.id,
            kind=decision.kind,
            hash=decision.hash,
            name=decision.name,
            action=decision.action,
            reason=decision.reason,
            verdict="vetoed" if index < 2 else "approved",
        )
        for index, decision in enumerate(decisions)
    )
    manifest = review.ReviewManifest(
        schema_version=1,
        snapshot_schema_version=1,
        ruleset_version=1,
        fingerprint=run.fingerprint,
        decisions=manifest_decisions,
    )
    store = review.empty_store()
    adapter = review.merge_manifest(
        store,
        manifest,
        run,
        recorded_at="2026-08-22T12:00:00Z",
    )
    core = merge_verdicts(
        store,
        {entry.id: entry.verdict for entry in manifest_decisions},
        run,
        recorded_at="2026-08-22T12:00:00Z",
    )
    assert core == adapter


def test_manifest_adapter_and_core_cover_categories_and_diagnostics():
    run = build_report()
    add, unchanged, update, approved = proposals(run)[:4]
    unknown = ManifestDecision(
        id="404404404",
        kind="weapons",
        hash="gone-hash",
        name="Gone",
        action="junk",
        reason="dupe-lower",
        verdict="vetoed",
    )
    entries = (
        ManifestDecision(
            id=add.id,
            kind=add.kind,
            hash=add.hash,
            name=add.name,
            action=add.action,
            reason=add.reason,
            verdict="vetoed",
        ),
        ManifestDecision(
            id=unchanged.id,
            kind=unchanged.kind,
            hash=unchanged.hash,
            name=unchanged.name,
            action=unchanged.action,
            reason=unchanged.reason,
            verdict="vetoed",
        ),
        ManifestDecision(
            id=update.id,
            kind=update.kind,
            hash=update.hash,
            name=update.name,
            action=update.action,
            reason=update.reason,
            verdict="vetoed",
        ),
        ManifestDecision(
            id=approved.id,
            kind=approved.kind,
            hash=approved.hash,
            name=approved.name,
            action=approved.action,
            reason=approved.reason,
            verdict="approved",
        ),
        unknown,
    )
    old_same = review.Veto(
        id=unchanged.id,
        kind=unchanged.kind,
        hash=unchanged.hash,
        name=unchanged.name,
        action=unchanged.action,
        reason=unchanged.reason,
        fingerprint="old",
        recorded_at="2026-08-21T00:00:00Z",
    )
    old_update = replace(
        old_same,
        id=update.id,
        kind=update.kind,
        hash=update.hash,
        name=update.name,
        action="review",
        reason="old-reason",
    )
    old_approved = replace(
        old_same,
        id=approved.id,
        kind=approved.kind,
        hash=approved.hash,
        name=approved.name,
        action=approved.action,
        reason=approved.reason,
    )
    store = review.OverrideStore(
        schema_version=1,
        vetoes=(old_same, old_update, old_approved),
    )
    manifest = review.ReviewManifest(
        schema_version=1,
        snapshot_schema_version=1,
        ruleset_version=1,
        fingerprint=run.fingerprint,
        decisions=entries,
    )
    recorded_at = "2026-08-22T12:00:00Z"
    adapter = review.merge_manifest(store, manifest, run, recorded_at=recorded_at)
    core = merge_verdicts(
        store,
        {entry.id: entry.verdict for entry in entries},
        run,
        recorded_at=recorded_at,
    )

    def ids(values):
        return tuple(value if isinstance(value, str) else value.id for value in values)

    assert core.store == adapter.store
    assert ids(core.added) == ids(adapter.added) == (add.id,)
    assert ids(core.updated) == ids(adapter.updated) == (update.id,)
    assert ids(core.unchanged) == ids(adapter.unchanged) == (unchanged.id,)
    assert ids(core.unknown_ids) == ids(adapter.unknown_ids) == (unknown.id,)
    assert ids(core.already_vetoed_but_approved) == ids(
        adapter.already_vetoed_but_approved
    ) == (approved.id,)
    # The core intentionally has only ids; the adapter preserves the exact
    # legacy ManifestDecision diagnostics for CLI names/kinds.
    assert adapter.unknown_ids == (unknown,)
    assert adapter.already_vetoed_but_approved == (entries[3],)


def test_merge_verdicts_rejects_non_string_mapping_ids():
    run = build_report()
    with pytest.raises(TypeError, match="verdict id must be a string"):
        merge_verdicts(review.empty_store(), {123: "vetoed"}, run)


def test_only_retention_consumes_same_proposal():
    source_root = Path(__file__).parents[1] / "src"
    calls = []

    class SameProposalCallVisitor(ast.NodeVisitor):
        def __init__(self):
            self.function_stack = []
            self.calls = []

        def visit_FunctionDef(self, node):
            self.function_stack.append(node.name)
            self.generic_visit(node)
            self.function_stack.pop()

        def visit_AsyncFunctionDef(self, node):
            self.function_stack.append(node.name)
            self.generic_visit(node)
            self.function_stack.pop()

        def visit_Call(self, node):
            called_name = None
            if isinstance(node.func, ast.Name):
                called_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                called_name = node.func.attr
            if called_name == "same_proposal":
                self.calls.append((node.lineno, tuple(self.function_stack)))
            self.generic_visit(node)

    for path in source_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        visitor = SameProposalCallVisitor()
        visitor.visit(tree)
        calls.extend((path, lineno, stack) for lineno, stack in visitor.calls)
    assert len(calls) == 1
    assert calls[0][0].name == "review_session.py"
    assert calls[0][2] == ("retain_verdicts",)


def test_strict_review_primitives_are_public():
    assert review.MAX_TEXT == 200
    assert review.ID_RE.fullmatch("18446744073709551615")
    assert callable(review.check_keys)
    assert callable(review.require_text)
    assert callable(review.require_id)
    assert callable(review.require_kind)
