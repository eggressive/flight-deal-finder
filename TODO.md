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
| 5 | `search_window` actually uses `min_stay`/`max_stay` via roundtrip integration | `flight_deal_finder/api/flightapi.py` | ✅ Done | Roundtrip search added: `search_roundtrip_window` |
| 6 | ~~Route-level `check_interval_h` support~~ | — | ✅ Removed | Field was never consumed by engine/CLI; removed in PR #9
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

1. **Per-route scheduling:** `check_interval_h` was removed in PR #9 because no scheduler exists. Build a daemon/systemd timer that respects per-route intervals, or keep the tool as a one-shot cron job?    
2. **`min_stay`/`max_stay` for oneway:** Currently used by `search_roundtrip_window()` for return-date computation, but still ignored by `search_window()` (oneway). Should oneway routes also respect these (e.g., for multi-city trips), or are they strictly roundtrip params?
3. **`deep_link` is fake:** `flightapi.py` generates a Google Travel search URL, not an actual booking link. Rename to `search_link`? Parse real deep links from API response?
4. **CI/CD:** Add GitHub Actions for pytest + ruff on PRs? (Low effort, high value.)
5. **Error monitoring:** Add Sentry or similar for silent API/alert failures? Currently only logs to console.

---

*Last updated: 2026-05-31 — after PR #8 (roundtrip) + PR #9 (remove check_interval_h).*
