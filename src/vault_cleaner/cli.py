"""vault-cleaner CLI.

M1 scope: `roundtrip` — parse a DIM weapons export, tag one sacrificial item,
and write a CSV that DIM's "Import tags/notes from CSV" accepts. Dry-run by
default; nothing touches disk until --write.
"""

from __future__ import annotations

import argparse
import sys

from vault_cleaner.config import ConfigError, load_config
from vault_cleaner.parse import SchemaError, load_ghosts, load_weapons
from vault_cleaner.report import VALID_TAGS, write_import_csv
from vault_cleaner.manifest import ManifestError, load_perk_map
from vault_cleaner.rules import dupes, weapons as weapons_rules
from vault_cleaner.wishlist import WishlistError, fetch, load_all, parse_wishlist

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


def _cmd_dupes(args: argparse.Namespace) -> int:
    input_path = args.input or LOADERS["weapons"][1]
    try:
        weapons = load_weapons(input_path)
        cfg = load_config(args.config)
    except (FileNotFoundError, SchemaError, ConfigError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    clp = cfg["rails"]["crafted_level_protect"]
    use_wishlists = not args.no_wishlists and bool(cfg["wishlists"]["sources"])
    if use_wishlists:
        try:
            wl = load_all(cfg)
            perk_map = load_perk_map(
                cfg["paths"]["manifest_cache_dir"], cfg["manifest"]["max_age_days"]
            )
        except (WishlistError, ManifestError) as e:
            print(f"error: {e}", file=sys.stderr)
            print("(pass --no-wishlists to run dupes without wishlist data)", file=sys.stderr)
            return 1
        result = weapons_rules.run(weapons, wl, perk_map, clp)
        decisions = result.decisions
        conflicts = result.keep_trash_conflicts
    else:
        decisions = dupes.resolve(weapons, clp)
        conflicts = 0

    junk = [d for d in decisions if d.action == "junk"]
    review = [d for d in decisions if d.action == "review"]
    trash = [d for d in decisions if "wishlist-trash" in d.note]
    print(f"parsed {len(weapons)} weapons from {input_path}")
    wl_note = f" ({len(trash)} from wishlist-trash)" if use_wishlists else " (wishlists off)"
    print(f"resolved: {len(junk)} junk, {len(review)} review (soft-protected){wl_note}")
    if conflicts:
        print(f"note: {conflicts} item(s) matched both keep and trash lists — keep won, no action taken")
    for d in decisions:
        marker = "junk  " if d.action == "junk" else "review"
        print(f"  {marker} {d.name} (id {d.id}, {d.owner}) — {d.note.split('#vc-')[-1]}")

    if not args.write:
        print("dry run — pass --write to write the import CSV")
        return 0

    rows = [{"Id": d.id, "Hash": d.hash, "Tag": d.tag, "Notes": d.note} for d in decisions]
    n = write_import_csv(rows, args.output)
    print(f"wrote {n} row(s) to {args.output} — import via DIM Settings → Import tags/notes from CSV")
    return 0


def _cmd_wishlists(args: argparse.Namespace) -> int:
    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    sources = cfg["wishlists"]["sources"]
    if not sources:
        print("error: no [wishlists.sources] configured in config.toml", file=sys.stderr)
        return 1

    total_keep = total_trash = 0
    for name, url in sources.items():
        try:
            path = fetch(
                name, url,
                cache_dir=cfg["paths"]["wishlist_cache_dir"],
                max_age_days=cfg["wishlists"]["max_age_days"],
                refresh=args.refresh,
            )
        except WishlistError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        wl = parse_wishlist(path.read_text(encoding="utf-8"), name)
        keep = sum(len(v) for v in wl.keep.values())
        trash = sum(len(v) for v in wl.trash.values())
        total_keep += keep
        total_trash += trash
        extras = []
        if wl.skipped:
            extras.append(f"{wl.skipped} malformed lines skipped")
        if wl.wildcards:
            extras.append(f"{wl.wildcards} wildcard entries ignored")
        suffix = f" ({', '.join(extras)})" if extras else ""
        print(
            f"{name}: {keep} keep rolls across {len(wl.keep)} items, "
            f"{trash} trash entries across {len(wl.trash)} items{suffix}"
        )
    print(f"total: {total_keep} keep rolls, {total_trash} trash entries")
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

    dp = sub.add_parser("dupes", help="resolve weapon dupes: best copy per Hash survives, rest junk/review")
    dp.add_argument("--input", default=None, help="DIM weapons export (default data/in/destiny-weapon.csv)")
    dp.add_argument("--output", default=DEFAULT_OUTPUT, help=f"import CSV to write (default {DEFAULT_OUTPUT})")
    dp.add_argument("--config", default="config.toml", help="config file (default config.toml)")
    dp.add_argument("--write", action="store_true", help="actually write the output CSV (default is dry run)")
    dp.add_argument("--no-wishlists", action="store_true",
                    help="skip the wishlist pass (trash tagging + keep-roll ranking)")
    dp.set_defaults(func=_cmd_dupes)

    wp = sub.add_parser("wishlists", help="download/refresh wishlist caches and show parse stats")
    wp.add_argument("--config", default="config.toml", help="config file (default config.toml)")
    wp.add_argument("--refresh", action="store_true", help="re-download even if the cache is fresh")
    wp.set_defaults(func=_cmd_wishlists)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
