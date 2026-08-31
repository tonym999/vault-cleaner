"""Write the DIM-importable tags/notes CSV and human-readable summaries."""

from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path

from vault_cleaner.duplicate_reference import note_tail, safe_fragment

OUTPUT_COLUMNS = ["Id", "Hash", "Tag", "Notes"]
# Generated duplicate tails contain a bounded reference plus a bounded detail
# suffix. Keep the summary bound explicit, while leaving the selection reason
# at the end visible when the reference reaches its own presentation limit.
_SUMMARY_TAIL_LIMIT = 512

# Tags DIM's importer understands. Empty string means "leave/clear tag" —
# we only emit rows we have a reason for, so it shouldn't normally appear.
VALID_TAGS = frozenset({"favorite", "keep", "junk", "infuse", "archive"})


# Matches the reason slug in "#vc-junk: dupe-lower, kept 123" or
# "#vc-review: wishlist-trash whole-item (locked)": lowercase hyphenated
# words only, so it stops naturally at numbers, commas, and parens.
_REASON_RE = re.compile(r"#vc-(junk|review): ([a-z-]+(?: [a-z-]+)*)")


def reason_slug(note: str) -> tuple[str, str]:
    """(action, slug) parsed from the #vc- hashtag in a Notes value.

    The LAST match wins. Rules replace complete known tool clauses at the
    Notes tail, but ambiguous historical or user-authored marker text is
    deliberately preserved ahead of the current generated clause."""
    matches = list(_REASON_RE.finditer(note))
    if not matches:
        return "unknown", "unknown"
    return matches[-1].group(1), matches[-1].group(2)


def summarize(sections: Iterable[tuple[str, list]]) -> str:
    """Human-readable dry-run summary (PLAN.md M5).

    `sections` is (kind, decisions) per pass, e.g. ("weapons", [...]).
    Groups by action + reason with per-item lines beneath each group;
    junk groups first, then review, largest first.
    """
    groups: dict[tuple[str, str, str], list] = defaultdict(list)
    for kind, decisions in sections:
        for d in decisions:
            action, slug = reason_slug(d.note)
            groups[(action, kind, slug)].append(d)

    n_junk = sum(len(v) for (a, _, _), v in groups.items() if a == "junk")
    n_review = sum(len(v) for (a, _, _), v in groups.items() if a == "review")
    lines = [f"would junk {n_junk} item(s) and flag {n_review} for review"]

    ordered = sorted(
        groups.items(),
        key=lambda kv: (kv[0][0] != "junk", -len(kv[1]), kv[0]),
    )
    for (action, kind, slug), ds in ordered:
        lines.append("")
        lines.append(f"{action.upper()} {slug} ({kind}) — {len(ds)} item(s)")
        for d in ds:
            line = (
                f"  {safe_fragment(d.name, limit=120)} "
                f"(id {safe_fragment(d.id, limit=48)}, "
                f"{safe_fragment(d.owner, limit=80)})"
            )
            if d.kept_id:
                line += (
                    " — "
                    f"{safe_fragment(note_tail(d.note), limit=_SUMMARY_TAIL_LIMIT, escape_structure=False)}"
                )
            lines.append(line)
    return "\n".join(lines)


def render_import_csv(rows: Iterable[Mapping[str, str]]) -> bytes:
    """Render rows of ``{Id, Hash, Tag, Notes}`` in DIM's import format.

    Ids are re-wrapped in literal quotes to match DIM's own export style
    (spreadsheet-proofing the 64-bit id). The returned UTF-8 bytes use the
    CRLF line endings emitted by DIM's CSV writer.
    """
    output = io.StringIO(newline="")
    # The csv module's default dialect uses CRLF, which is the byte format DIM
    # currently emits and imports.
    writer = csv.DictWriter(output, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        tag = row.get("Tag", "")
        if tag and tag not in VALID_TAGS:
            raise ValueError(f"invalid DIM tag {tag!r} for id {row.get('Id')}")
        out = dict(row)
        out["Id"] = '"' + str(row["Id"]).strip('"') + '"'
        writer.writerow(out)
    return output.getvalue().encode("utf-8")


def write_import_csv(rows: Iterable[Mapping[str, str]], path: str | Path) -> int:
    """Write rows of {Id, Hash, Tag, Notes} in the format DIM imports.

    Returns the number of rows written. Ids are re-wrapped in literal quotes
    to match DIM's own export style (spreadsheet-proofing the 64-bit id).
    Rows are rendered completely in memory before the destination is opened.
    """
    path = Path(path)
    materialized_rows = list(rows)
    content = render_import_csv(materialized_rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return len(materialized_rows)
