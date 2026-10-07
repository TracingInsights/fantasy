"""Orchestrate fetching, snapshotting and transforming."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .client import DEFAULT_YEARS, YearNotAvailableError, fetch_year
from .transform import transform_year

logger = logging.getLogger(__name__)

RAW_DIR = "raw"
TRANSFORMED_DIR = "transformed"


def run_timestamp(now: datetime | None = None) -> str:
    """UTC timestamp used to name snapshots from a single sync run."""
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H%M%SZ")


def _normalized(payload) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def latest_snapshot(raw_dir: Path, year: int) -> Path | None:
    """Newest existing raw snapshot file for a year, or None."""
    year_dir = raw_dir / str(year)
    if not year_dir.is_dir():
        return None
    files = sorted(year_dir.glob("*.json"))
    return files[-1] if files else None


@dataclass
class YearResult:
    year: int
    fetched: bool = False
    snapshot_written: Path | None = None
    unchanged: bool = False
    skipped_reason: str | None = None


@dataclass
class SyncResult:
    timestamp: str
    year_results: list[YearResult] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return any(r.snapshot_written is not None for r in self.year_results)


def snapshot_year(payload: dict, raw_dir: Path, timestamp: str) -> YearResult:
    """Save a raw snapshot only if it differs from the latest existing one."""
    year = payload.get("seasonResult", {}).get("season")
    if year is None:
        return YearResult(year=0, skipped_reason="payload missing season")
    year_dir = raw_dir / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)

    latest = latest_snapshot(raw_dir, int(year))
    if latest is not None:
        try:
            if _normalized(json.loads(latest.read_text(encoding="utf-8"))) == _normalized(payload):
                return YearResult(year=int(year), fetched=True, unchanged=True)
        except (json.JSONDecodeError, OSError) as exc:  # corrupt latest -> just overwrite history
            logger.warning("Could not compare with %s: %s", latest, exc)

    snapshot_path = year_dir / f"{timestamp}.json"
    snapshot_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return YearResult(year=int(year), fetched=True, snapshot_written=snapshot_path)


def sync(years: tuple[int, ...] | list[int], data_dir: Path) -> SyncResult:
    """Run a full sync: fetch each year, snapshot (if changed), transform.

    Even when the raw payload is unchanged, the transformed tree is rebuilt so
    that transform-logic changes propagate; identical content produces no git
    diff.
    """
    timestamp = run_timestamp()
    result = SyncResult(timestamp=timestamp)

    for year in years:
        try:
            payload = fetch_year(year)
        except YearNotAvailableError as exc:
            logger.warning("Skipping %s: %s", year, exc)
            result.year_results.append(YearResult(year=year, skipped_reason=str(exc)))
            continue

        year_result = snapshot_year(payload, data_dir / RAW_DIR, timestamp)
        result.year_results.append(year_result)

        # Transform from the payload we just fetched (which equals the latest
        # snapshot whether or not a new snapshot was written).
        written = transform_year(payload, data_dir / TRANSFORMED_DIR)
        logger.info(
            "Year %s: %s (%d files transformed)",
            year,
            "new snapshot" if year_result.snapshot_written else "unchanged",
            len(written),
        )
        time.sleep(0.5)  # be polite between season fetches
    return result


def default_years() -> tuple[int, ...]:
    return DEFAULT_YEARS
