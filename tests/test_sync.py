"""Tests for snapshot / change-detection logic in sync.py."""

import json
from pathlib import Path

from f1_stats.sync import run_timestamp, snapshot_year

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
