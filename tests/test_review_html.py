"""The static HTML review artifact (#37): self-containment and safe embedding.

The browser-side logic is exercised for real in test_review_html_js.py; this
module covers what Python is responsible for — what goes into the file, and
what must never come back out of it as executable markup.
"""

import json
import re
from pathlib import Path

import pytest
from test_review import BIG_ID, build_report, proposals

from vault_cleaner.report import reason_slug
from vault_cleaner.report_run import (
    RULESET_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
    run_report,
    snapshot_dict,
)
from vault_cleaner.review_html import (
    APP_ELEMENT_ID,
    APP_JS,
    BODY_HTML,
    CSS,
    PRIVACY_WARNING,
    SNAPSHOT_ELEMENT_ID,
    embed_json,
    render_review_html,
    write_review_html,
)

FIXTURES = Path(__file__).parent / "fixtures"
HOSTILE = FIXTURES / "weapons_hostile.csv"

_SNAPSHOT_BLOCK = re.compile(
    rf'<script type="application/json" id="{SNAPSHOT_ELEMENT_ID}">(.*?)</script>',
    re.DOTALL,
)
_APP_BLOCK = re.compile(rf'<script id="{APP_ELEMENT_ID}">(.*?)</script>', re.DOTALL)


def hostile_report():
    """A run whose every item name is shaped like an injection attempt."""
    return run_report(
        config_path="nonexistent.toml",
        weapons_path=HOSTILE,
        armor_path=FIXTURES / "does-not-exist.csv",
        ghosts_path=FIXTURES / "does-not-exist.csv",
        no_wishlists=True,
    )


def split_artifact(html: str) -> tuple[str, str, str]:
    """(chrome, embedded snapshot JSON, app script) from a rendered artifact.

    Splitting on the *shipped* markers is the point: if either script block
    stopped being extractable, the browser would mis-parse the file the same
    way this helper does.
    """
    snapshot = _SNAPSHOT_BLOCK.search(html)
    app = _APP_BLOCK.search(html)
    assert snapshot and app, "both script blocks must be extractable"
    chrome = _APP_BLOCK.sub("", _SNAPSHOT_BLOCK.sub("", html))
    return chrome, snapshot.group(1), app.group(1)


def embedded_snapshot(html: str) -> dict:
    return json.loads(split_artifact(html)[1])


# --------------------------------------------------------------- containment


def test_artifact_is_one_self_contained_file():
    chrome, _, app = split_artifact(render_review_html(build_report()))
    for blob, where in ((chrome, "markup"), (app, "app script")):
        assert "http://" not in blob, f"{where} references a remote URL"
        assert "https://" not in blob, f"{where} references a remote URL"
    assert "@import" not in chrome
    assert "url(" not in chrome, "CSS must not fetch anything"
    # The only link in the document is the in-page skip link.
    assert re.findall(r'href="([^"]*)"', chrome) == ["#vc-list"]
    assert not re.search(r"\ssrc\s*=", chrome), "no element may load a remote asset"


def test_head_declares_a_no_network_csp():
    html = render_review_html(build_report())
    policy = re.search(r'Content-Security-Policy" content="([^"]+)"', html).group(1)
    assert "default-src 'none'" in policy
    assert "connect-src 'none'" in policy
    # Inline is the one concession a file:// artifact cannot avoid.
    assert "script-src 'unsafe-inline'" in policy


def test_page_carries_the_privacy_warning():
    html = render_review_html(build_report())
    assert PRIVACY_WARNING in html
    assert "keep this file local" in html


def test_render_is_byte_deterministic():
    # No timestamps: two renders of the same inputs must be diffable.
    assert render_review_html(build_report()) == render_review_html(build_report())


def test_artifact_does_not_leak_local_paths(tmp_path):
    export = tmp_path / "weapons_dupes.csv"
    export.write_bytes((FIXTURES / "weapons_dupes.csv").read_bytes())
    run = run_report(
        config_path="nonexistent.toml",
        weapons_path=export,
        armor_path=tmp_path / "missing-armor.csv",
        ghosts_path=tmp_path / "missing-ghosts.csv",
        no_wishlists=True,
    )
    html = render_review_html(run)
    assert str(tmp_path) not in html
    assert "weapons_dupes.csv" in html, "the basename is still useful provenance"


# -------------------------------------------------------------- safe embedding


def test_no_source_blob_can_close_the_script_element():
    """A closing script tag in our own source truncates its element.

    Case-insensitive, and without requiring the `>`: HTML matches the end tag
    ASCII case-insensitively and terminates on whitespace or `/` as well, so
    `</SCRIPT >` and `</script/` both end the element. Verified in Chromium —
    a mixed-case tag inside a JS comment silently cut the shipped script in
    half, which is the bug this test exists to prevent.
    """
    for name, blob in (("APP_JS", APP_JS), ("CSS", CSS), ("BODY_HTML", BODY_HTML)):
        assert not re.search(r"</script", blob, re.IGNORECASE), (
            f"{name} would truncate its script element"
        )
        assert "<!--" not in blob and "-->" not in blob, f"{name} spells a comment"


def test_embed_json_escapes_without_changing_any_value():
    payload = json.dumps(
        {"name": "</script><img src=x onerror=alert(1)>", "sep": "a\u2028b\u2029c"},
        ensure_ascii=False,
    )
    embedded = embed_json(payload)
    assert json.loads(embedded) == json.loads(payload)
    for unsafe in ("<", ">", "&", "\u2028", "\u2029"):
        assert unsafe not in embedded


def test_hostile_item_names_are_inert_data():
    html = render_review_html(hostile_report())
    names = [d["name"] for s in embedded_snapshot(html)["sections"] for d in s["decisions"]]
    assert "</script><img src=x onerror=alert(1)>" in names, "value survives intact"

    # ...but the file only ever spells it escaped, so the parser never sees a
    # tag: exactly two script elements close, the two the renderer emitted.
    assert html.count("</script>") == 2
    assert "\\u003c/script\\u003e" in html
    assert "<img src=x onerror=alert(1)>" not in html


def test_formula_and_unicode_names_survive_as_text():
    names = [
        d["name"]
        for s in embedded_snapshot(render_review_html(hostile_report()))["sections"]
        for d in s["decisions"]
    ]
    assert "=cmd|' /C calc'!A0" in names, "CSV formula text is data, not a formula"
    assert any("💀" in name for name in names), "non-BMP Unicode survives"
    assert "__proto__" in names, "a prototype-shaped name is still just a name"


def test_hostile_notes_round_trip_through_the_snapshot():
    snapshot = embedded_snapshot(render_review_html(hostile_report()))
    decisions = [d for s in snapshot["sections"] for d in s["decisions"]]
    notes = [d["original_notes"] for d in decisions]
    assert any('"quoted" & <b>bold</b>' == note for note in notes)
    assert any("\u2028" in note for note in notes)


# ------------------------------------------------------------------ precision


def test_embedded_ids_and_hashes_are_json_strings():
    snapshot = embedded_snapshot(render_review_html(hostile_report()))
    decisions = [d for s in snapshot["sections"] for d in s["decisions"]]
    assert decisions, "the hostile fixture must produce decisions to check"
    for decision in decisions:
        assert isinstance(decision["id"], str)
        assert isinstance(decision["hash"], str)


def test_widest_instance_id_survives_the_embedding_verbatim():
    html = render_review_html(hostile_report())
    ids = [d["id"] for s in embedded_snapshot(html)["sections"] for d in s["decisions"]]
    assert BIG_ID in ids
    # Not just equal after parsing — present as those exact digits in the file.
    assert BIG_ID in html


def test_embedded_snapshot_matches_the_python_snapshot_exactly():
    run = build_report()
    assert embedded_snapshot(render_review_html(run)) == snapshot_dict(run)


def test_embedded_versions_are_what_a_manifest_must_claim():
    snapshot = embedded_snapshot(render_review_html(build_report()))
    assert snapshot["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert snapshot["ruleset_version"] == RULESET_VERSION
    assert len(snapshot["fingerprint"]) == 64


# ------------------------------------------------------------ grouping parity


def test_action_and_reason_fields_agree_with_the_note_hashtag():
    """The page groups from `action`/`reason`; the terminal re-parses `note`.

    They must be the same two values, or the two views would disagree about
    which group an item belongs to.
    """
    for decision in proposals(build_report()):
        assert reason_slug(decision.note) == (decision.action, decision.reason)


# ----------------------------------------------------------------- filesystem


def test_write_creates_the_parent_directory(tmp_path):
    target = write_review_html(build_report(), tmp_path / "out" / "nested" / "r.html")
    assert target.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_write_replaces_an_existing_artifact(tmp_path):
    target = tmp_path / "review.html"
    target.write_text("stale", encoding="utf-8")
    write_review_html(build_report(), target)
    assert "stale" not in target.read_text(encoding="utf-8")


@pytest.mark.parametrize("marker", ["vc-summary", "vc-controls", "vc-list", "vc-status"])
def test_chrome_provides_the_hooks_the_app_fills_in(marker):
    chrome = split_artifact(render_review_html(build_report()))[0]
    assert f'id="{marker}"' in chrome
