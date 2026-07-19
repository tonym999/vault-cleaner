"""Write the DIM-importable tags/notes CSV and human-readable summaries."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping

OUTPUT_COLUMNS = ["Id", "Hash", "Tag", "Notes"]

# Tags DIM's importer understands. Empty string means "leave/clear tag" —
# we only emit rows we have a reason for, so it shouldn't normally appear.
VALID_TAGS = frozenset({"favorite", "keep", "junk", "infuse", "archive"})


# Matches the reason slug in "#vc-junk: dupe-lower, kept 123" or
# "#vc-review: wishlist-trash whole-item (locked)": lowercase hyphenated
# words only, so it stops naturally at numbers, commas, and parens.
_REASON_RE = re.compile(r"#vc-(junk|review): ([a-z-]+(?: [a-z-]+)*)")


def reason_slug(note: str) -> tuple[str, str]:
    """(action, slug) parsed from the #vc- hashtag in a Notes value."""
    m = _REASON_RE.search(note)
    if not m:
        return "unknown", "unknown"
    return m.group(1), m.group(2)


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
            lines.append(f"  {d.name} (id {d.id}, {d.owner})")
    return "\n".join(lines)


def write_import_csv(rows: Iterable[Mapping[str, str]], path: str | Path) -> int:
    """Write rows of {Id, Hash, Tag, Notes} in the format DIM imports.

    Returns the number of rows written. Ids are re-wrapped in literal quotes
    to match DIM's own export style (spreadsheet-proofing the 64-bit id).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            tag = row.get("Tag", "")
            if tag and tag not in VALID_TAGS:
                raise ValueError(f"invalid DIM tag {tag!r} for id {row.get('Id')}")
            out = dict(row)
            out["Id"] = '"' + str(row["Id"]).strip('"') + '"'
            writer.writerow(out)
            count += 1
    return count
