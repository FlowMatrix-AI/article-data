"""``article-data`` command line: fetch sources, run each analysis, or run them all."""

from __future__ import annotations

import argparse
import sys

from article_data import eaglei, exhibits, fetch, penetration_gap, storm_multiplier, trends


def cmd_fetch(args: argparse.Namespace) -> None:
    for source in fetch.resolve(args.sources or list(fetch.GROUPS)):
        path = fetch.fetch(source, force=args.force)
        print(f"{source.name}: {path} ({path.stat().st_size:,} bytes, sha256 verified)")


def cmd_storm(_: argparse.Namespace) -> None:
    result = storm_multiplier.run()
    print(f"excluded: {result.impossible} impossible, {result.zero_baseline} zero-baseline")
    for k, v in storm_multiplier.summarize(result.rows).items():
        print(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}")


def cmd_eaglei(args: argparse.Namespace) -> None:
    years = args.years or list(eaglei.YEARS)
    source_for = (lambda y: fetch.fetch(fetch.SOURCES[f"eaglei_{y}"])) if args.stream else None
    cm = eaglei.run(years=years, source_for=source_for, delete_after=args.stream)
    by_year = cm.groupby("year")["customer_hours"].sum() / 1e6
    print(f"county-month rows: {len(cm):,}")
    print(by_year.round(1).to_string())


def cmd_gap(_: argparse.Namespace) -> None:
    acs, top, cutoff = penetration_gap.run()
    print(f"counties: {len(acs):,}; qualifying homes: {acs['qualifying'].sum() / 1e6:.1f}M")
    print(f"exposure cutoff (top quartile): {cutoff:.2f}M customer-hours")
    print(top.to_string(index=False))


def cmd_trends(args: argparse.Namespace) -> None:
    events, national = trends.run(refresh=args.pull)
    print(events.to_string(index=False))
    print(national.to_string(index=False))


def cmd_exhibits(args: argparse.Namespace) -> None:
    for path in exhibits.render(args.names or None):
        print(f"{path.name}: {path.stat().st_size:,} bytes")


def cmd_all(args: argparse.Namespace) -> None:
    cmd_storm(args)
    cmd_eaglei(argparse.Namespace(years=None, stream=args.stream))
    cmd_gap(args)
    cmd_trends(argparse.Namespace(pull=False))
    cmd_exhibits(argparse.Namespace(names=None))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="article-data", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    f = sub.add_parser("fetch", help="download and verify raw sources (default: all)")
    f.add_argument("sources", nargs="*", help=f"groups {sorted(fetch.GROUPS)} or source names")
    f.add_argument("--force", action="store_true", help="re-download even if verified")
    f.set_defaults(func=cmd_fetch)

    sub.add_parser("storm-multiplier", help="EIA-861 storm multiplier").set_defaults(func=cmd_storm)

    e = sub.add_parser("eaglei", help="EAGLE-I county-month and 2025 county-week aggregates")
    e.add_argument("--years", nargs="*", type=int, help="subset of years (default: 2014-2025)")
    e.add_argument(
        "--stream",
        action="store_true",
        help="fetch each year just before aggregating and delete it after (one year on disk)",
    )
    e.set_defaults(func=cmd_eaglei)

    sub.add_parser("penetration-gap", help="ACS qualifying homes x EAGLE-I exposure").set_defaults(
        func=cmd_gap
    )

    t = sub.add_parser("trends", help="Google Trends seven-day window")
    t.add_argument("--pull", action="store_true", help="re-pull the pinned series (live)")
    t.set_defaults(func=cmd_trends)

    x = sub.add_parser("exhibits", help="draw the article SVGs from the computed CSVs")
    x.add_argument(
        "names", nargs="*", help=f"file names (default: all of {list(exhibits.EXHIBITS_BY_FILE)})"
    )
    x.set_defaults(func=cmd_exhibits)

    a = sub.add_parser("all", help="run every analysis from fetched sources")
    a.add_argument("--stream", action="store_true", help="stream EAGLE-I years (see eaglei)")
    a.set_defaults(func=cmd_all)

    args = p.parse_args(argv)
    try:
        args.func(args)
    except FileNotFoundError as e:
        sys.exit(f"missing input {e.filename}; run `article-data fetch` first")
