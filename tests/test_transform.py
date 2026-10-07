"""Tests for the transform layer, using a trimmed real 2025 payload."""

import json
from pathlib import Path

import pytest

from f1_stats.transform import (
    flatten,
    session_record,
    slugify,
    transform_year,
)

FIXTURE = Path(__file__).parent / "fixtures" / "statistics_sample.json"


@pytest.fixture()
def payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_slugify():
    assert slugify("Japanese Grand Prix") == "japanese-grand-prix"
    assert slugify("São Paulo Grand Prix") == "sao-paulo-grand-prix"
    assert slugify("Emilia-Romagna Grand Prix") == "emilia-romagna-grand-prix"


def test_flatten():
    assert flatten({"a": 1, "b": {"c": 2, "d": {"e": 3}}}) == {"a": 1, "b.c": 2, "b.d.e": 3}


def test_session_record_shapes(payload):
    driver = payload["seasonResult"]["raceResults"]["1"]["drivers"][0]
    rec = session_record(driver, "Q")
    assert "raceResult" not in rec
    assert rec["sessionResult"] == driver["raceResult"]["Q"]
    assert rec["sessionPoints"] == driver["raceResult"]["Q"]["totalPoints"]["points"]
    # round-level context is preserved
    for key in ("id", "price", "percentOwned", "priceChange"):
        assert rec[key] == driver[key]


def test_transform_year_layout(payload, tmp_path):
    files = transform_year(payload, tmp_path)
    written = {f.name for f in files}

    aussie = tmp_path / "2025" / "australian-grand-prix"
    china = tmp_path / "2025" / "chinese-grand-prix"

    # race metadata
    assert (aussie / "race.json").is_file()
    race_meta = json.loads((aussie / "race.json").read_text())
    assert race_meta["name"] == "Australian Grand Prix"
    assert race_meta["roundNumber"] == 1

    # qualifying + race sessions everywhere
    for sess in ("qualifying", "race"):
        for suffix in ("drivers", "constructors", "all"):
            assert f"{sess}_{suffix}.json" in written
            assert f"{sess}_{suffix}.csv" in written

    # sprint exists for China (round 2) but not Australia (round 1)
    for suffix in ("drivers", "constructors", "all"):
        assert (china / f"sprint_{suffix}.json").is_file()
        assert (china / f"sprint_{suffix}.csv").is_file()
        assert not (aussie / f"sprint_{suffix}.json").exists()


def test_transform_all_contains_both_types(payload, tmp_path):
    transform_year(payload, tmp_path)
    race_all = json.loads(
        (tmp_path / "2025" / "australian-grand-prix" / "race_all.json").read_text()
    )
    types = {r["type"] for r in race_all}
    assert types == {"driver", "constructor"}


def test_csv_rows_match_json(payload, tmp_path):
    transform_year(payload, tmp_path)
    gp = tmp_path / "2025" / "chinese-grand-prix"
    json_records = json.loads((gp / "sprint_drivers.json").read_text())
    with (gp / "sprint_drivers.csv").open() as fh:
        import csv
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(json_records)
    for row, record in zip(rows, json_records):
        assert row["id"] == record["id"]
        assert float(row["price"]) == record["price"]
