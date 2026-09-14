"""Command-line front end: ``python3 -m gasbrinebench``.

Prints an inventory of the database, or writes a filtered selection to a file::

    python3 -m gasbrinebench
    python3 -m gasbrinebench --by gas
    python3 -m gasbrinebench --gas co2 --quality R -o co2_recommended.csv
    python3 -m gasbrinebench --family solubility -o solubility.parquet

Exit code 0 on success, 2 on a bad argument, 1 if an export backend is
missing (the message names the package to install).
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from . import __version__, inventory, load, write
from .export import MissingDependencyError
from .vocab import GASES, QUALITY_CODES, TAGS


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python3 -m gasbrinebench",
        description=__doc__.split("::")[0].strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--family", default="all",
                   help="property family, or 'all' (default)")
    p.add_argument("--gas", nargs="+", metavar="GAS",
                   help=f"restrict to these gases ({', '.join(GASES)})")
    p.add_argument("--property", nargs="+", metavar="PROP",
                   help="restrict to these property names")
    p.add_argument("--quality", nargs="+", metavar="CODE",
                   help=f"restrict to these quality codes "
                        f"({', '.join(QUALITY_CODES)})")
    p.add_argument("--tag", nargs="+", metavar="TAG",
                   help=f"restrict to these tags ({', '.join(TAGS)})")
    p.add_argument("--include-lle", action="store_true",
                   help="keep the 144 lle-regime rows, which the default "
                        "loader drops because they are liquid-liquid mutual "
                        "solubilities, not gas solubilities")
    p.add_argument("--T", nargs=2, type=float, metavar=("LO", "HI"),
                   help="temperature window [K]")
    p.add_argument("--P", nargs=2, type=float, metavar=("LO", "HI"),
                   help="pressure window [bar]")
    p.add_argument("--by", default="family",
                   help="group the inventory on this column (default: family)")
    p.add_argument("-o", "--output", metavar="PATH",
                   help="write the selection to PATH (.csv, .parquet, .h5) "
                        "instead of printing an inventory")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    filters = {}
    if args.gas:
        filters["gas"] = args.gas
    if args.property:
        filters["property"] = args.property
    if args.quality:
        filters["quality"] = args.quality
    if args.tag:
        filters["tag"] = args.tag
    if args.T:
        filters["T"] = tuple(args.T)
    if args.P:
        filters["P"] = tuple(args.P)

    try:
        df = load(
            args.family,
            exclude_tags=None if args.include_lle else ("lle-regime",),
            **filters,
        )
    except (ValueError, KeyError, FileNotFoundError) as exc:
        print(f"gasbrinebench: {exc}", file=sys.stderr)
        return 2

    if args.output:
        try:
            path = write(df, args.output)
        except MissingDependencyError as exc:
            print(f"gasbrinebench: {exc}", file=sys.stderr)
            return 1
        except ValueError as exc:
            print(f"gasbrinebench: {exc}", file=sys.stderr)
            return 2
        print(f"wrote {len(df):,} rows to {path}")
        return 0

    with pd.option_context("display.width", 200,
                           "display.max_columns", 20,
                           "display.max_rows", 200):
        print(f"GasBrineBench {__version__} -- {len(df):,} rows, "
              f"{df['source'].nunique()} sources")
        print()
        try:
            print(inventory(df, by=args.by))
        except KeyError:
            print(f"gasbrinebench: no column {args.by!r} to group on",
                  file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
