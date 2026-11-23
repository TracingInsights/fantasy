"""Tests for snapshot / change-detection logic in sync.py."""

import json
from pathlib import Path

from f1_stats.sync import run_timestamp, snapshot_year, write_index

PAYLOAD = {
    "seasonResult": {
        "season": 2025,
        "raceResults": {"1": {"drivers": [{"id": "ALP_DOO", "price": 7.2}], "constructors": []}},
    },
    "races": [],
}


def test_snapshot_written_when_new(tmp_path):
    result = snapshot_year(PAYLOAD, tmp_path, run_timestamp())
    assert result.snapshot_written is not None
    assert result.unchanged is False
    assert result.snapshot_written == tmp_path / "2025" / f"{result.snapshot_written.name}"
    assert json.loads(result.snapshot_written.read_text()) == PAYLOAD


def test_snapshot_skipped_when_identical(tmp_path):
    first = snapshot_year(PAYLOAD, tmp_path, "2025-10-07T160000Z")
    assert first.snapshot_written is not None
    second = snapshot_year(PAYLOAD, tmp_path, "2025-10-07T220000Z")
    assert second.snapshot_written is None
    assert second.unchanged is True
    # no duplicate history file was created
    assert list((tmp_path / "2025").glob("*.json")) == [first.snapshot_written]


def test_snapshot_written_when_changed(tmp_path):
    snapshot_year(PAYLOAD, tmp_path, "2025-10-07T160000Z")
    changed = json.loads(json.dumps(PAYLOAD))
    changed["seasonResult"]["raceResults"]["1"]["drivers"][0]["price"] = 9.9
    result = snapshot_year(changed, tmp_path, "2025-10-07T220000Z")
    assert result.snapshot_written is not None
    assert len(list((tmp_path / "2025").glob("*.json"))) == 2


def test_index_names_each_seasons_newest_snapshot(tmp_path):
    snapshot_year(PAYLOAD, tmp_path, "2025-10-07T160000Z")
    changed = json.loads(json.dumps(PAYLOAD))
    changed["seasonResult"]["raceResults"]["1"]["drivers"][0]["price"] = 9.9
    snapshot_year(changed, tmp_path, "2025-10-14T160000Z")
    newer = json.loads(json.dumps(PAYLOAD))
    newer["seasonResult"]["season"] = 2026
    snapshot_year(newer, tmp_path, "2026-03-01T120000Z")
    (tmp_path / "2026" / "notes.txt").write_text("not a snapshot")

    path = write_index(tmp_path)

    assert path == tmp_path / "index.json"
    assert json.loads(path.read_text()) == {
        "seasons": {
            "2025": {
                "latest": "2025-10-14T160000Z.json",
                "snapshots": ["2025-10-07T160000Z.json", "2025-10-14T160000Z.json"],
            },
            "2026": {
                "latest": "2026-03-01T120000Z.json",
                "snapshots": ["2026-03-01T120000Z.json"],
            },
        }
    }


def test_index_is_byte_stable_and_not_read_as_a_snapshot(tmp_path):
    first = snapshot_year(PAYLOAD, tmp_path, "2025-10-07T160000Z")
    before = write_index(tmp_path).read_bytes()
    assert write_index(tmp_path).read_bytes() == before
    # the index never shadows a season's newest snapshot
    again = snapshot_year(PAYLOAD, tmp_path, "2025-10-07T220000Z")
    assert again.unchanged is True
    assert list((tmp_path / "2025").glob("*.json")) == [first.snapshot_written]
