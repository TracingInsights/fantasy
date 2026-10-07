# Implementation Plan: F1 Fantasy Stats Sync

Sync and save statistics data from https://f1fantasytools.com/statistics into this
repo using a uv-managed Python project and a scheduled GitHub Actions workflow.

## Data source (verified)

- `GET https://f1fantasytools.com/api/statistics/{year}`
- Public, no auth, no cookies, returns `application/json` (~2MB per season).
- Valid years: **2023, 2024, 2025, 2026**. Invalid years return `400`.
- Contains per-round driver & constructor stats: price, price change, total
  points, % owned, qualifying/race/sprint results, DNFs, overtakes,
  points-per-million, etc.
- The site's CSV export endpoint requires auth; the JSON endpoint is the source.

## Requirements (decided)

1. Save the raw API response as-is per year, **with history** (timestamped
   snapshots, append-only).
2. Also save a **transformed** layout: `year / grand-prix / session` folders,
   where session is qualifying, race, or sprint.
3. All available years (2023-2026).
4. Transformed files in **both JSON and CSV**.
5. Within each session: **separate** driver and constructor files **and** a
   combined `_all` file.
6. Schedule: **weekly, Monday 10pm IST** (`cron: 30 16 * * 1` UTC) **plus manual**
   `workflow_dispatch`.
7. Changes land as **auto-commits directly to main**.
8. **Skip the commit when nothing changed** (raw snapshot is only saved when it
   differs semantically from the latest existing snapshot).

## Repo layout

```
fantasy/
├── .github/workflows/sync.yml      # weekly cron + manual dispatch
├── pyproject.toml                   # uv project, Python 3.13
├── uv.lock
├── README.md
├── src/f1_stats/
│   ├── __init__.py
│   ├── client.py                    # fetch a year's JSON from the API
│   ├── transform.py                 # raw JSON → per-GP session files (JSON + CSV)
│   ├── sync.py                      # orchestration: snapshot + transform + change detection
│   └── __main__.py                  # CLI: `uv run f1-stats sync [--years ...]`
├── tests/
│   ├── test_transform.py            # unit tests against a trimmed real fixture
│   └── fixtures/statistics_sample.json
└── data/
    ├── raw/{year}/{timestamp}.json          # history, append-only
    └── transformed/{year}/{gp-slug}/
        ├── qualifying_drivers.json/.csv
        ├── qualifying_constructors.json/.csv
        ├── qualifying_all.json/.csv
        ├── race_drivers.json/.csv
        ├── race_constructors.json/.csv
        ├── race_all.json/.csv
        └── sprint_*.{json,csv}               # only where a sprint exists
```

## Behavior

### Sync run (same code locally and in CI)

1. Fetch each year (2023-2026; configurable, invalid years skipped gracefully).
2. **Raw snapshot**: save to `data/raw/{year}/{UTC timestamp}.json` only if
   semantically different from the latest existing snapshot (normalized JSON
   compare) so weekly no-ops produce no commits and no duplicate history.
3. **Transform**: rebuild `data/transformed/` from the latest snapshot for
   each year.
   - GP folders named from the `races` array in the payload, slugified
     (e.g. `japanese-grand-prix`).
   - Sessions: qualifying, race, sprint.
   - Driver and constructor stats kept in separate per-type files and in a
     combined `_all` file, in JSON and CSV.
   - Each record carries round-level context (price, % owned, price change)
     alongside session results.
4. Exit code reflects whether anything changed (CI uses this to decide on
   commit).

### CLI

- `uv run f1-stats sync` — all years
- `uv run f1-stats sync --years 2025` — subset

### GitHub Actions (`sync.yml`)

- Triggers: `schedule: cron 30 16 * * 1` (Mon 10pm IST = 16:30 UTC) and
  `workflow_dispatch`.
- Steps: checkout → `astral-sh/setup-uv` → `uv sync` → `uv run f1-stats sync`
  → if `git diff` non-empty: commit + push.
- `permissions: contents: write`; concurrency guard against overlapping runs.

## Build order

1. Scaffold uv project + package skeleton, README.
2. Curl a real 2024 payload, save trimmed sample as test fixture (confirms
   exact field shapes: `races[]` naming, sprint key, constructor fields).
3. `client.py` + `sync.py` snapshot logic with change detection.
4. `transform.py` (GP/session/file generation) + tests.
5. CLI wiring.
6. `sync.yml` workflow + dry run (verify skip-if-identical works).
7. Final README with usage, cron explanation, data schema notes.
