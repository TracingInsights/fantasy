"""Command line entry point: f1-stats sync [--years ...] [--data-dir DIR]."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .sync import default_years, sync


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="f1-stats",
        description="Sync F1 Fantasy statistics from f1fantasytools.com",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    sync_parser = sub.add_parser("sync", help="fetch, snapshot and transform stats data")
    sync_parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=list(default_years()),
        help="seasons to sync (default: 2023 2024 2025 2026)",
    )
    sync_parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="data directory (default: ./data)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.command == "sync":
        result = sync(args.years, args.data_dir)
        for yr in result.year_results:
            if yr.skipped_reason:
                print(f"{yr.year}: skipped ({yr.skipped_reason})")
            elif yr.snapshot_written:
                print(f"{yr.year}: new snapshot {yr.snapshot_written}")
            else:
                print(f"{yr.year}: unchanged, no snapshot written")
        print(f"sync result: {'CHANGED' if result.changed else 'UNCHANGED'}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
