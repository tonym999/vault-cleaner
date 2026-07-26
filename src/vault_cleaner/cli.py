"""vault-cleaner CLI.

M1 scope: `roundtrip` — parse a DIM weapons export, tag one sacrificial item,
and write a CSV that DIM's "Import tags/notes from CSV" accepts. Dry-run by
default; nothing touches disk until --write.
"""

from __future__ import annotations

import argparse
import sys

from vault_cleaner.config import ConfigError, load_config
from vault_cleaner.export_discovery import ExportDiscoveryError, select_export
from vault_cleaner.manifest import ManifestError
from vault_cleaner.parse import SchemaError, load_armor, load_ghosts, load_weapons
from vault_cleaner.pipeline import resolve_armor, resolve_weapons
from vault_cleaner.report import VALID_TAGS, summarize, write_import_csv
from vault_cleaner.report_run import (
    DEFAULT_INPUT_DIR,
    NoExportsError,
    ReportRun,
    SourceReadError,
    run_report,
)
from vault_cleaner.review import (
    DEFAULT_OVERRIDES_PATH,
    ReviewError,
    apply_vetoes,
    check_manifest_matches,
    classify,
    imported_junk_tags,
    load_overrides,
    merge_manifest,
    parse_manifest,
    save_overrides,
)
from vault_cleaner.review_html import (
    DEFAULT_REVIEW_HTML,
    PRIVACY_WARNING,
    write_review_html,
)
from vault_cleaner.rules import ghosts as ghost_rules
from vault_cleaner.wishlist import WishlistError, fetch, parse_wishlist

LOADERS = {
    "weapons": load_weapons,
    "ghosts": load_ghosts,
}
DEFAULT_OUTPUT = "data/out/dim-import.csv"


def _cmd_roundtrip(args: argparse.Namespace) -> int:
    loader = LOADERS[args.kind]
    try:
        input_path = select_export(args.kind, args.input, DEFAULT_INPUT_DIR)
        items = loader(input_path)
    except (ExportDiscoveryError, FileNotFoundError, SchemaError) as e:
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


def _resolve_weapons(weapons, cfg, no_wishlists: bool):
    """Compatibility tuple around the public pipeline result."""
    result = resolve_weapons(weapons, cfg, no_wishlists)
    return (
        result.decisions,
        result.keep_trash_conflicts,
        result.wishlists_used,
    )


def _cmd_dupes(args: argparse.Namespace) -> int:
    try:
        input_path = select_export("weapons", args.input, DEFAULT_INPUT_DIR)
        weapons = load_weapons(input_path)
        cfg = load_config(args.config)
    except (
        ExportDiscoveryError,
        FileNotFoundError,
        SchemaError,
        ConfigError,
    ) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    try:
        decisions, conflicts, use_wishlists = _resolve_weapons(weapons, cfg, args.no_wishlists)
    except (WishlistError, ManifestError) as e:
        print(f"error: {e}", file=sys.stderr)
        print("(pass --no-wishlists to run without wishlist data)", file=sys.stderr)
        return 1

    junk = [d for d in decisions if d.action == "junk"]
    review = [d for d in decisions if d.action == "review"]
    trash = [d for d in decisions if "wishlist-trash" in d.note]
    print(f"parsed {len(weapons)} weapons from {input_path}")
    wl_note = f" ({len(trash)} from wishlist-trash)" if use_wishlists else " (wishlists off)"
    print(f"resolved: {len(junk)} junk, {len(review)} review (soft-protected){wl_note}")
    if conflicts:
        print(
            f"note: {conflicts} item(s) matched both keep and trash lists — "
            "keep outranked trash; normal dupe rules still apply to these items"
        )
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


def _resolve_armor(armor, cfg):
    """Compatibility tuple around the public armor pipeline result."""
    result = resolve_armor(armor, cfg)
    return result.decisions, result.scored


def _cmd_armor(args: argparse.Namespace) -> int:
    try:
        input_path = select_export("armor", args.input, DEFAULT_INPUT_DIR)
        armor = load_armor(input_path)
        cfg = load_config(args.config)
    except (
        ExportDiscoveryError,
        FileNotFoundError,
        SchemaError,
        ConfigError,
    ) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    decisions, scored = _resolve_armor(armor, cfg)
    junk = [d for d in decisions if d.action == "junk"]
    review = [d for d in decisions if d.action == "review"]
    dupe_rows = [d for d in decisions if "armor-exact-dupe" in d.note]
    close_rows = [d for d in decisions if "armor-dominated" in d.note or "armor-similar" in d.note]
    print(f"parsed {len(armor)} armor pieces from {input_path} ({scored} legendaries scored)")
    print(
        f"resolved: {len(junk)} junk, {len(review)} review "
        f"({len(dupe_rows)} from exact dupes, {len(close_rows)} close-dupe reviews)"
    )
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


def _cmd_ghosts(args: argparse.Namespace) -> int:
    # No config involvement at all: the ghost policy is purely
    # protection-based, and an unrelated config error must not block it.
    try:
        input_path = select_export("ghosts", args.input, DEFAULT_INPUT_DIR)
        ghosts = load_ghosts(input_path)
    except (ExportDiscoveryError, FileNotFoundError, SchemaError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    decisions = ghost_rules.run(ghosts)
    kept = len(ghosts) - len(decisions)
    print(f"parsed {len(ghosts)} ghosts from {input_path}")
    print(f"resolved: {len(decisions)} junk ({kept} protected: equipped/locked/tagged/in-loadout)")
    for d in decisions:
        print(f"  junk   {d.name} (id {d.id}, {d.owner}) — {d.note.split('#vc-')[-1]}")

    if not args.write:
        print("dry run — pass --write to write the import CSV")
        return 0

    rows = [{"Id": d.id, "Hash": d.hash, "Tag": d.tag, "Notes": d.note} for d in decisions]
    n = write_import_csv(rows, args.output)
    print(f"wrote {n} row(s) to {args.output} — import via DIM Settings → Import tags/notes from CSV")
    return 0


def _build_report(args: argparse.Namespace) -> tuple[ReportRun | None, int]:
    """Run every pass, reporting the usual load failures as exit code 1."""
    try:
        result = run_report(
            config_path=args.config,
            weapons_path=args.weapons,
            armor_path=args.armor,
            ghosts_path=args.ghosts,
            input_dir=DEFAULT_INPUT_DIR,
            no_wishlists=args.no_wishlists,
        )
    except (
        ConfigError,
        ExportDiscoveryError,
        SchemaError,
        NoExportsError,
        SourceReadError,
    ) as e:
        print(f"error: {e}", file=sys.stderr)
        return None, 1
    except (WishlistError, ManifestError) as e:
        print(f"error: {e}", file=sys.stderr)
        print("(pass --no-wishlists to run without wishlist data)", file=sys.stderr)
        return None, 1
    return result, 0


def _cmd_report(args: argparse.Namespace) -> int:
    """Run every pass and print the aggregated would-junk summary (#9)."""
    result, rc = _build_report(args)
    if result is None:
        return rc

    for warning in result.warnings:
        print(warning.render(), file=sys.stderr)

    print(summarize(result.summary_sections()))
    if result.keep_trash_conflicts:
        print(
            f"\nnote: {result.keep_trash_conflicts} weapon(s) matched both "
            "keep and trash lists — keep outranked trash; normal dupe rules "
            "still apply to these items"
        )

    # `report` deliberately shows what the rules propose, not what the user
    # has already approved — but silently omitting known vetoes would make
    # this look like the final word. Point at `review` instead of applying.
    try:
        store = load_overrides(args.overrides)
    except ReviewError as e:
        print(f"warning: ignoring overrides — {e}", file=sys.stderr)
    else:
        if store.vetoes:
            print(
                f"\nnote: {len(store.vetoes)} persisted veto(es) in "
                f"{args.overrides} are not applied here — run "
                "`vault-cleaner review` for the reviewed export"
            )

    if not args.write:
        print("\ndry run — pass --write to write the combined import CSV")
        return 0

    rows = result.import_rows()
    n = write_import_csv(rows, args.output)
    print(
        f"\nwrote {n} row(s) to {args.output} — "
        "import via DIM Settings → Import tags/notes from CSV"
    )
    return 0


def _action_counts(decisions) -> str:
    junk = sum(1 for d in decisions if d.action == "junk")
    review = sum(1 for d in decisions if d.action == "review")
    return f"{len(decisions)} decision(s) ({junk} junk, {review} review)"


def _describe(veto) -> str:
    return f"{veto.name or '(unnamed)'} (id {veto.id}, {veto.kind}, {veto.action}/{veto.reason})"


def _print_override_status(status, overrides_path: str) -> None:
    print(
        f"\noverrides: {overrides_path} — {len(status.active)} active, "
        f"{len(status.stale)} stale, {len(status.orphaned)} orphaned, "
        f"{len(status.unchecked)} unchecked"
    )
    for veto, _ in status.active:
        print(f"  active    {_describe(veto)}")
    for entry in status.stale:
        print(f"  stale     {_describe(entry.veto)} — {entry.detail}")
    for veto in status.orphaned:
        print(f"  orphaned  {_describe(veto)} — no longer in the export")
    for veto in status.unchecked:
        print(f"  unchecked {_describe(veto)} — {veto.kind} export not loaded this run")


def _cmd_review(args: argparse.Namespace) -> int:
    """Inspect/apply a review manifest and write the reviewed export (#36).

    Without --manifest this only reports how persisted vetoes line up with a
    fresh run. With one, the manifest is validated against that run's
    fingerprint before a single veto is persisted.
    """
    result, rc = _build_report(args)
    if result is None:
        return rc

    for warning in result.warnings:
        print(warning.render(), file=sys.stderr)

    manifest = None
    merge = None
    try:
        store = load_overrides(args.overrides)
        if args.manifest:
            manifest = parse_manifest(args.manifest)
            # Refuse before touching anything: a manifest from another run
            # would suppress rows nobody reviewed.
            check_manifest_matches(manifest, result)
            merge = merge_manifest(store, manifest, result)
            store = merge.store
    except ReviewError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    proposed = [d for section in result.sections for d in section.decisions]
    print(f"report: {_action_counts(proposed)}")

    if merge is not None:
        manifest_counts = (
            f"{len(manifest.decisions)} verdict(s) "
            f"({len(manifest.vetoed)} vetoed, {len(manifest.approved)} approved)"
        )
        print(f"manifest: {args.manifest} — {manifest_counts}, fingerprint matches")
        counts = (len(merge.added), len(merge.updated), len(merge.unchanged))
        print(
            "overrides: added {}, updated {}, {} unchanged".format(*counts)
            if args.write
            else "overrides: would add {}, update {}, leave {} unchanged".format(*counts)
        )
        for entry in merge.unknown_ids:
            print(
                f"  ignored   id {entry.id} ({entry.name or 'unnamed'}) — "
                "vetoed in the manifest but not proposed by this run",
                file=sys.stderr,
            )
        for entry in merge.already_vetoed_but_approved:
            print(
                f"  kept      id {entry.id} ({entry.name or 'unnamed'}) — approved in "
                "the manifest but already vetoed; applying a manifest never "
                "removes a veto, edit the overrides file to undo one",
                file=sys.stderr,
            )

    status = classify(store, result)
    _print_override_status(status, args.overrides)

    kept = apply_vetoes(result, status.active_ids)
    print(f"\nafter vetoes: {_action_counts(kept)}")

    already_junk = imported_junk_tags(status)
    if already_junk:
        print(
            f"\nwarning: {len(already_junk)} vetoed item(s) are already tagged "
            "junk in DIM from an earlier cleanup. A veto suppresses the "
            "proposal, it does not restore the previous tag — clear those "
            "tags in DIM if you want them back:",
            file=sys.stderr,
        )
        for veto, _ in already_junk:
            print(f"  {_describe(veto)}", file=sys.stderr)

    if not args.write:
        print(f"\nwould write {args.output}")
        if merge is not None:
            print(f"would update {args.overrides}")
        print("dry run — nothing written; pass --write to persist vetoes and the CSV")
        return 0

    if merge is not None:
        save_overrides(store, args.overrides)
        print(f"\nupdated {args.overrides}")
    n = write_import_csv([d.import_row() for d in kept], args.output)
    print(
        f"wrote {n} row(s) to {args.output} — "
        "import via DIM Settings → Import tags/notes from CSV"
    )
    return 0


def _cmd_review_html(args: argparse.Namespace) -> int:
    """Generate the self-contained static HTML review artifact (#37).

    A third output surface, deliberately not a mode of the other two:
    `report --write` still writes the proposal CSV and `review --write` still
    writes the reviewed one. This command only ever produces the review page,
    and the page only ever produces a manifest for `review` to re-validate.
    """
    result, rc = _build_report(args)
    if result is None:
        return rc

    for warning in result.warnings:
        print(warning.render(), file=sys.stderr)

    proposed = [d for section in result.sections for d in section.decisions]
    print(f"review page: {_action_counts(proposed)} to review")
    print(f"fingerprint: {result.fingerprint}")

    # Persisted vetoes are not pre-applied here for the same reason `report`
    # does not apply them: the page shows what the rules propose. Re-vetoing
    # in the page is harmless — merging a manifest never removes a veto.
    if not args.write:
        print(f"would write {args.output}")
        print("dry run — nothing written; pass --write to generate the review page")
        return 0

    target = write_review_html(result, args.output)
    size = target.stat().st_size
    print(
        f"wrote {target} ({size} bytes) — open it in a browser, review, export "
        "a review manifest, then apply it with "
        "`vault-cleaner review --manifest <file> --write`"
    )
    print(f"note: {PRIVACY_WARNING}")
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

    ap = sub.add_parser("armor", help="armor pipeline: exact dupes then archetype scoring; junk with reasons")
    ap.add_argument("--input", default=None, help="DIM armor export (default data/in/destiny-armor.csv)")
    ap.add_argument("--output", default=DEFAULT_OUTPUT, help=f"import CSV to write (default {DEFAULT_OUTPUT})")
    ap.add_argument("--config", default="config.toml", help="config file (default config.toml)")
    ap.add_argument("--write", action="store_true", help="actually write the output CSV (default is dry run)")
    ap.set_defaults(func=_cmd_armor)

    gp = sub.add_parser("ghosts", help="junk every shell not equipped/locked/tagged/in a loadout")
    gp.add_argument("--input", default=None, help="DIM ghost export (default data/in/destiny-ghost.csv)")
    gp.add_argument("--output", default=DEFAULT_OUTPUT, help=f"import CSV to write (default {DEFAULT_OUTPUT})")
    gp.add_argument("--write", action="store_true", help="actually write the output CSV (default is dry run)")
    gp.set_defaults(func=_cmd_ghosts)

    rp = sub.add_parser("report", help="run all passes dry and print the aggregated would-junk summary")
    rp.add_argument("--weapons", default=None, help="weapons export (default data/in/destiny-weapon.csv)")
    rp.add_argument("--armor", default=None, help="armor export (default data/in/destiny-armor.csv)")
    rp.add_argument("--ghosts", default=None, help="ghost export (default data/in/destiny-ghost.csv)")
    rp.add_argument("--output", default=DEFAULT_OUTPUT, help=f"combined import CSV to write (default {DEFAULT_OUTPUT})")
    rp.add_argument("--config", default="config.toml", help="config file (default config.toml)")
    rp.add_argument("--no-wishlists", action="store_true", help="skip the wishlist pass for weapons")
    rp.add_argument("--overrides", default=DEFAULT_OVERRIDES_PATH,
                    help=f"persisted vetoes to mention but not apply (default {DEFAULT_OVERRIDES_PATH})")
    rp.add_argument("--write", action="store_true", help="write the combined import CSV (default is dry run)")
    rp.set_defaults(func=_cmd_report)

    vp = sub.add_parser("review", help="apply a review manifest's vetoes and write the reviewed import CSV")
    vp.add_argument("--manifest", default=None,
                    help="review manifest JSON to validate and apply (omit to only report override status)")
    vp.add_argument("--overrides", default=DEFAULT_OVERRIDES_PATH,
                    help=f"persistent veto store (default {DEFAULT_OVERRIDES_PATH})")
    vp.add_argument("--weapons", default=None, help="weapons export (default data/in/destiny-weapon.csv)")
    vp.add_argument("--armor", default=None, help="armor export (default data/in/destiny-armor.csv)")
    vp.add_argument("--ghosts", default=None, help="ghost export (default data/in/destiny-ghost.csv)")
    vp.add_argument("--output", default=DEFAULT_OUTPUT, help=f"reviewed import CSV to write (default {DEFAULT_OUTPUT})")
    vp.add_argument("--config", default="config.toml", help="config file (default config.toml)")
    vp.add_argument("--no-wishlists", action="store_true", help="skip the wishlist pass for weapons")
    vp.add_argument("--write", action="store_true",
                    help="persist vetoes and write the reviewed CSV (default is dry run)")
    vp.set_defaults(func=_cmd_review)

    hp = sub.add_parser("review-html",
                        help="generate the self-contained static HTML review page")
    hp.add_argument("--weapons", default=None, help="weapons export (default data/in/destiny-weapon.csv)")
    hp.add_argument("--armor", default=None, help="armor export (default data/in/destiny-armor.csv)")
    hp.add_argument("--ghosts", default=None, help="ghost export (default data/in/destiny-ghost.csv)")
    hp.add_argument("--output", default=DEFAULT_REVIEW_HTML,
                    help=f"review page to write (default {DEFAULT_REVIEW_HTML})")
    hp.add_argument("--config", default="config.toml", help="config file (default config.toml)")
    hp.add_argument("--no-wishlists", action="store_true", help="skip the wishlist pass for weapons")
    hp.add_argument("--write", action="store_true",
                    help="write the review page (default is dry run)")
    hp.set_defaults(func=_cmd_review_html)

    wp = sub.add_parser("wishlists", help="download/refresh wishlist caches and show parse stats")
    wp.add_argument("--config", default="config.toml", help="config file (default config.toml)")
    wp.add_argument("--refresh", action="store_true", help="re-download even if the cache is fresh")
    wp.set_defaults(func=_cmd_wishlists)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
