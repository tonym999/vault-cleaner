"""Write the DIM-importable tags/notes CSV and human-readable summaries."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping

OUTPUT_COLUMNS = ["Id", "Hash", "Tag", "Notes"]

# Tags DIM's importer understands. Empty string means "leave/clear tag" —
# we only emit rows we have a reason for, so it shouldn't normally appear.
VALID_TAGS = frozenset({"favorite", "keep", "junk", "infuse", "archive"})


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
