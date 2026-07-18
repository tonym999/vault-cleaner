"""vault-cleaner CLI.

M1 scope: `roundtrip` — parse a DIM weapons export, tag one sacrificial item,
and write a CSV that DIM's "Import tags/notes from CSV" accepts. Dry-run by
default; nothing touches disk until --write.
"""

from __future__ import annotations

import argparse
import sys

from vault_cleaner.parse import SchemaError, load_ghosts, load_weapons
from vault_cleaner.report import VALID_TAGS, write_import_csv

LOADERS = {
    "weapons": (load_weapons, "data/in/destiny-weapon.csv"),
    "ghosts": (load_ghosts, "data/in/destiny-ghost.csv"),
}
DEFAULT_OUTPUT = "data/out/dim-import.csv"


def _cmd_roundtrip(args: argparse.Namespace) -> int:
    loader, default_input = LOADERS[args.kind]
    input_path = args.input or default_input
    try:
        items = loader(input_path)
    except (FileNotFoundError, SchemaError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.id:
        matches = items[items["Id"] == args.id]
    else:
        matches = items[items["Name"].str.casefold() == args.item.casefold()]

    if matches.empty:
        wanted = args.id or args.item
        print(f"error: no item matching {wanted!r} in {input_path}", file=sys.stderr)
        return 1

    rows = [
        {"Id": r["Id"], "Hash": r["Hash"], "Tag": args.tag, "Notes": args.note}
        for _, r in matches.iterrows()
    ]

    print(f"parsed {len(items)} {args.kind} from {input_path}")
    for row, (_, r) in zip(rows, matches.iterrows()):
        print(f"  would tag {args.tag!r}: {r['Name']} (id {r['Id']}, owner {r.get('Owner', '?')})")

    if not args.write:
        print("dry run — pass --write to write the import CSV")
        return 0

    n = write_import_csv(rows, args.output)
    print(f"wrote {n} row(s) to {args.output} — import via DIM Settings → Import tags/notes from CSV")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vault-cleaner")
    sub = parser.add_subparsers(dest="command", required=True)

    rt = sub.add_parser("roundtrip", help="tag one item and write a DIM import CSV (M1 pipeline check)")
    rt.add_argument("--kind", default="weapons", choices=sorted(LOADERS), help="which DIM export to read (default weapons)")
    rt.add_argument("--input", default=None, help="DIM export CSV (default: data/in/ path for --kind)")
    rt.add_argument("--output", default=DEFAULT_OUTPUT, help=f"import CSV to write (default {DEFAULT_OUTPUT})")
    pick = rt.add_mutually_exclusive_group(required=True)
    pick.add_argument("--item", help="item name to tag (case-insensitive; tags every copy)")
    pick.add_argument("--id", help="exact instance id to tag (disambiguates dupes)")
    rt.add_argument("--tag", default="junk", choices=sorted(VALID_TAGS), help="DIM tag to apply (default junk)")
    rt.add_argument("--note", default="#vc-test: m1 round trip", help="note text (default '#vc-test: m1 round trip')")
    rt.add_argument("--write", action="store_true", help="actually write the output CSV (default is dry run)")
    rt.set_defaults(func=_cmd_roundtrip)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
