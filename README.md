# f1-stats

Syncs F1 Fantasy statistics from
[f1fantasytools.com/statistics](https://f1fantasytools.com/statistics) into this
repo, using a scheduled GitHub Actions workflow.

- **Source**: `GET https://f1fantasytools.com/api/statistics/{year}` (public,
  no auth) — seasons **2023–2026**
- **Schedule**: weekly, Monday 10:00 PM IST (`cron: 30 16 * * 1` UTC), plus
  manual runs via `workflow_dispatch`
- **On every sync**: new data is committed to `main` and published as a GitHub
  **release** (tag `data-sync-YYYYMMDD-HHMMSS`), so any snapshot can be pinned
  or fetched via jsDelivr

## Repository layout

```
data/
├── raw/                                # full API responses, append-only history
│   └── 2025/
│       ├── 2025-10-07T163000Z.json      # one file per sync run, only if data changed
│       └── ...
└── transformed/                         # rebuilt from the latest raw snapshot
    └── 2025/
        ├── australian-grand-prix/
        │   ├── race.json                # race metadata (name, round, country, flag)
        │   ├── qualifying_drivers.json / .csv
        │   ├── qualifying_constructors.json / .csv
        │   ├── qualifying_all.json / .csv
        │   ├── race_drivers.json / .csv
        │   ├── race_constructors.json / .csv
        │   ├── race_all.json / .csv
        │   └── sprint_*                 # only for rounds that had a sprint
        └── ...
```

Each per-session record keeps all round-level context from the source (price,
price change, % owned, total points, points-per-million, ...) plus the
session's point breakdown in `sessionResult` and flat totals in
`sessionPoints` / `sessionNnPoints`.

**Skip-if-identical**: if a season's payload is byte-equivalent (after key
normalization) to the latest existing snapshot, no new snapshot is written and
the workflow produces no commit and no release.

## Usage

```bash
uv sync
uv run f1-stats sync                    # all years (2023-2026)
uv run f1-stats sync --years 2025 2026  # subset
uv run f1-stats sync --data-dir data    # custom output dir
uv run pytest                           # tests
```

## Fetching data via jsDelivr

```text
# Latest version on main (12h CDN cache)
https://cdn.jsdelivr.net/gh/TracingInsights/fantasy@main/data/transformed/2025/japanese-grand-prix/race_drivers.csv

# Pinned to a specific sync release
https://cdn.jsdelivr.net/gh/TracingInsights/fantasy@data-sync-20251013-163000/data/transformed/2025/japanese-grand-prix/race_drivers.csv
```

Releases are listed under
[github.com/TracingInsights/fantasy/releases](https://github.com/TracingInsights/fantasy/releases).

## Data source details

- Provider: f1fantasytools.com's own backend, aggregating the official F1
  Fantasy game (prices, % owned, points) plus their computed fields
  (`nnPoints`, `pointsPerMillion`)
- Sessions in the source payload: `Q` (qualifying), `R` (race), `S` (sprint —
  only on sprint rounds)
- The implementation plan lives in [.agents/plan.md](.agents/plan.md)
