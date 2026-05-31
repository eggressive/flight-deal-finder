# Flight Deal Finder — TODO / Roadmap

Last updated: 2026-05-31

## Done ✅

| # | Item | PR | Status |
|---|------|-----|--------|
| 1 | Fix ruff lint errors (E741, E501, I001) | #2 | ✅ Merged |
| 2 | Fix DB default source label (`amadeus` → `flightapi`) | #3 | ✅ Merged |
| 3 | Fix history CLI output format (5-col → 6-col unpack) | #2 | ✅ Merged |
| 4 | Fix search_roundtrip error handling (403/429 guards) | #3 | ✅ Merged |
| 5 | Fix .gitignore (add cache dirs) | #2 | ✅ Merged |
| 6 | Add FlightApiClient `close()` + context manager | #4 | ✅ Merged |
| 7 | Add route schema validation (`Route` dataclass) | #5 | ✅ Merged |
| 8 | Remove dead deps (rich, beautifulsoup4, lxml) | #6 | ✅ Merged |
| 9 | Wire/remove search_roundtrip (removed from engine, kept in client) | #7 | ✅ Merged |
| 10 | Add `direct_only` filtering in engine | #4/#6 | ✅ Merged |
| 11 | Auto-copy `watchlist.yaml.example` on missing watchlist | #2 | ✅ Merged |
| 12 | Fix watchlist route date window consistency | #2 | ✅ Merged |
| 13 | Full test suite (pytest 76/76 passing) | #1 | ✅ Merged |
| 14 | Review comment resolution (all 7 PRs, 27 threads) | #2–#7 | ✅ Resolved |
| 15 | README refresh (architecture, CLI commands, route options, dev section) | This sprint | ✅ Done |

---

## Ready 🟢 (low-hanging fruit)

| # | Item | File(s) | Effort | Notes |
|---|------|---------|--------|-------|
| 1 | `__init__.py` expose top-level API | `flight_deal_finder/__init__.py` | 5 min | Add `__all__` with `DealEngine`, `FlightApiClient`, `Route`, `Deal` |
| 2 | Move `load_dotenv()` to module level | `flight_deal_finder/config.py` | 5 min | Called every `DealEngine` init; unnecessary I/O after first call |
| 3 | Fix console alerts in dry-run (reuse channel vs new instance) | `flight_deal_finder/engine.py` | 10 min | Currently instantiates new `ConsoleChannel()` in dry-run mode |
| 4 | Fix `deep_link` naming (it's a search URL, not a booking link) | `flight_deal_finder/api/flightapi.py` | 10 min | Rename to `search_link` or `booking_url` for clarity |
| 5 | Add `pytest-cov` to dev deps + coverage config | `pyproject.toml` | 10 min | `pytest-cov>=6.0` + `[tool.coverage.run]` |
| 6 | Add `.ruff_cache/` to `.gitignore` | `.gitignore` | 1 min | Missing from current ignore list |
| 7 | Clean stale git worktrees | `~/.worktrees/` | 5 min | Remove leftover worktrees from kanban workers |
| 8 | Fix `search_window` test to use realistic mock data | `tests/test_flightapi.py` | 15 min | Current mocks return empty offers; need richer test data |

---

## Planned 🟡 (medium effort)

| # | Item | File(s) | Effort | Notes |
|---|------|---------|--------|-------|
| 1 | Retry / backoff on transient API failures | `flight_deal_finder/api/flightapi.py` | 2 hrs | 2× retry with 1s exponential backoff on `ConnectError`, `ReadTimeout`, 5xx |
| 2 | Server-side max-price filter (save credits) | `flight_deal_finder/api/flightapi.py` | 2 hrs | Pass price param to FlightAPI.io instead of client-side filtering |
| 3 | Structured output from `check` command | `flight_deal_finder/cli.py` | 1 hr | Print summary: "Checked 3 routes, 12 offers, 1 deal found" |
| 4 | HTML email for deal alerts | `flight_deal_finder/alerts/channels.py` | 2 hrs | Better formatting + clickable links in email alerts |
| 5 | `search_window` actually uses `min_stay`/`max_stay` | `flight_deal_finder/api/flightapi.py` | 4 hrs | Currently one-way only; return-date logic needs roundtrip integration |
| 6 | Route-level `check_interval_h` support | `flight_deal_finder/engine.py` + scheduler | 4 hrs | Watchlist declares it but engine never reads it |
| 7 | CI/CD (GitHub Actions) | `.github/workflows/` | 2 hrs | pytest + ruff on every PR |
| 8 | `get_median_price` scaling note | `flight_deal_finder/db.py` | 30 min | Client-side median on all rows; fine for now, document scaling concern |

---

## Icebox 🔵 (future ideas)

| # | Item | Notes |
|---|------|-------|
| 1 | Docker image for deployment | Alpine-based, multi-stage |
| 2 | Deploy docs / systemd service | For running as a daemon |
| 3 | Error monitoring (Sentry) | Catch API/alert failures silently |
| 4 | Rate-limit dashboard | Track FlightAPI.io credit burn |
| 5 | Web UI for watchlist editing | React/Vue, replaces YAML editing |
| 6 | Multi-provider support (Skyscanner, etc.) | Engine already has provider abstraction |
| 7 | Deal persistence (not just price history) | Store "deal fired" events separately |

---

## Open Questions ❓

1. **Roundtrip search:** `search_roundtrip()` exists in `FlightApiClient` but engine never calls it. Do we want return-flight support, or should the method be removed entirely?
2. **`min_stay`/`max_stay`:** Currently ignored by `search_window()`. Do we need true roundtrip date-range search, or should these params be removed from the watchlist schema?
3. **`check_interval_h`:** Watchlist declares it but engine never reads it. Remove from schema, or implement per-route scheduling?

---

*Generated from CODEBASE_ANALYSIS.md audit (11/25 items resolved, 14 open) + README accuracy audit.*
