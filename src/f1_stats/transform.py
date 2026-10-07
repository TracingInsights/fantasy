"""Transform raw API payloads into the year / grand-prix / session layout.

Each round (grand prix) gets a folder named after the slugified race name,
containing files per session (qualifying, race, sprint — sprint only where the
round had one). Every session is written three ways:

    {session}_drivers.json / .csv        per-driver records
    {session}_constructors.json / .csv   per-constructor records
    {session}_all.json / .csv            combined drivers + constructors

plus ``race.json`` with the race metadata from the ``races`` array.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path

SESSION_KEYS = {"Q": "qualifying", "R": "race", "S": "sprint"}


def slugify(name: str) -> str:
    """Convert a race name to a lowercase slug: 'Japanese Grand Prix' -> 'japanese-grand-prix'."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return text.strip("-")


def round_has_session(records: list[dict], session_key: str) -> bool:
    return any(session_key in r.get("raceResult", {}) for r in records)


def session_record(entity: dict, session_key: str) -> dict:
    """Build a per-session record from a driver/constructor dict.

    Keeps all round-level fields as-is (price, percentOwned, priceChange, ...),
    replaces the full ``raceResult`` with this session's detail, and adds
    flattened session point totals.
    """
    record = {k: v for k, v in entity.items() if k != "raceResult"}
    session = entity.get("raceResult", {}).get(session_key)
    if session is not None:
        record["sessionResult"] = session
        total = session.get("totalPoints", {})
        record["sessionPoints"] = total.get("points")
        record["sessionNnPoints"] = total.get("nnPoints")
    return record


def race_meta(race: dict) -> dict:
    """Race metadata written to race.json (full entry from the races array)."""
    return dict(race)


def flatten(obj, prefix: str = "") -> dict:
    """Flatten nested dicts into a single-level mapping with dotted keys."""
    flat: dict = {}
    for key, value in obj.items():
        name = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flat.update(flatten(value, name))
        else:
            flat[name] = value
    return flat


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns: list[str] = []
    seen: set[str] = set()
    for record in records:
        for key in flatten(record):
            if key not in seen:
                seen.add(key)
                columns.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(flatten(record))


def transform_year(payload: dict, out_dir: Path) -> list[Path]:
    """Write the transformed tree for one season's payload.

    Returns the list of files written. Files are always rewritten; callers can
    use the list to detect changes.
    """
    races = {r["roundNumber"]: r for r in payload.get("races", [])}
    race_results = payload.get("seasonResult", {}).get("raceResults", {})

    written: list[Path] = []
    for round_str, round_data in sorted(race_results.items(), key=lambda kv: int(kv[0])):
        round_number = int(round_str)
        race = races.get(round_number)
        if race is None:
            continue
        gp_dir = out_dir / str(payload.get("seasonResult", {}).get("season", "")) / slugify(race["name"])
        written.append(gp_dir / "race.json")
        _write_json(gp_dir / "race.json", race_meta(race))

        drivers = round_data.get("drivers", [])
        constructors = round_data.get("constructors", [])
        all_records = drivers + constructors

        for session_key, session_name in SESSION_KEYS.items():
            if not round_has_session(all_records, session_key):
                continue
            for suffix, records in (
                ("drivers", drivers),
                ("constructors", constructors),
                ("all", all_records),
            ):
                session_records = [session_record(e, session_key) for e in records]
                base = gp_dir / f"{session_name}_{suffix}"
                _write_json(base.with_suffix(".json"), session_records)
                _write_csv(base.with_suffix(".csv"), session_records)
                written.extend([base.with_suffix(".json"), base.with_suffix(".csv")])
    return written
