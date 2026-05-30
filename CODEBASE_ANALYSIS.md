# Flight Deal Finder — Codebase Analysis

Scope: full read of all source, tests, config, and docs. Tests pass (76/76). Lint has 3 errors.

---

## P0 — Critical (bugs, correctness, security)

| # | Issue | File(s) | Details |
|---|-------|---------|---------|
| 1 | Unused dependencies bloat install | `pyproject.toml` | `rich>=13.0`, `beautifulsoup4>=4.12`, `lxml>=5.3` are declared but never imported in source. Either use them (e.g., rich tables for `history`) or remove to shrink footprint and audit surface. |
| 2 | Default `source="amadeus"` in DB insert | `flight_deal_finder/db.py:48` | Hard-coded to legacy provider. All price records get mislabelled unless caller overrides. Fix default to `"flightapi"` or make it a required arg. |
| 3 | `search_roundtrip` missing error handling | `flight_deal_finder/api/flightapi.py:172-174` | `search_oneway` gracefully returns `[]` on 403/429/404. `search_roundtrip` calls `resp.raise_for_status()` blindly — a single 429 will crash the engine. Add the same guard. |
| 4 | `history` CLI unpack bug | `flight_deal_finder/cli.py:47` | `get_history` returns 6 cols `(origin, destination, price, dep_date, scraped_at, source)`. CLI unpacks only 5: `[row[1]] {row[0]}→{row[2]}: €{row[3]} @ {row[4]}`. Output is confusing: `[JFK] AMS→300.0: €2026-08-15 @ 2026-05-29 12:00`. Fix to `€{row[2]} | {row[0]}→{row[1]} on {row[3]} ({row[5]})`. |
| 5 | Ruff lint errors | `flightapi.py`, `engine.py` | 3 errors: ambiguous var `l`, line too long, unsorted imports. All trivial — `ruff check --fix` resolves 2/3. |

---

## P1 — Reliability / Quality

| # | Issue | File(s) | Details |
|---|-------|---------|---------|
| 6 | `FlightApiClient` never closes HTTP client | `flight_deal_finder/api/flightapi.py:40` | `httpx.Client` is instantiated in `__init__` but has no `close()`, `__enter__`, or `__exit__`. On long-lived cron runs this leaks connections. Add `close()` method or make it a context manager. |
| 7 | `search_window` ignores `min_stay`/`max_stay` | `flight_deal_finder/api/flightapi.py:176-214` | The engine passes trip-length constraints to `search_window`, but the method only does one-way searches with a date step. It never queries return dates, so the watchlist's `min_stay`/`max_stay` are effectively ignored. Either integrate `search_roundtrip` with stay logic, or drop the params from the API method. |
| 8 | No retry / backoff on transient API failures | `flight_deal_finder/api/flightapi.py` | `httpx.HTTPError` inside `search_window` is caught per-day but the whole day is lost. Add a small retry (2× with 1s backoff) on `ConnectError`, `ReadTimeout`, and 5xx. |
| 9 | `.env` loaded on every config read | `flight_deal_finder/config.py:17` | `load_dotenv()` runs inside `load_config()`, which is called every time `DealEngine` is instantiated. It's a no-op after the first call but still unnecessary I/O. Move to module level or guard with a flag. |
| 10 | `search_window` max-price filter is client-side only | `flight_deal_finder/api/flightapi.py:205-208` | FlightAPI.io supports server-side filtering; we download everything then filter. Wastes credits. Check if API supports a price param and pass it. |
| 11 | `DealEngine` has no route schema validation | `flight_deal_finder/engine.py:72-84` | Missing keys like `date_window`, `max_price`, or `destination` will raise `KeyError` at runtime. Add a small Pydantic/dataclass model for routes, or at least `route.get()` guards with skip+warn. |
| 12 | `get_median_price` query sorts client-side | `flight_deal_finder/db.py:60-77` | Fetches all rows for route, then computes median in Python. SQLite has no native `MEDIAN`, but `PERCENTILE_CONT` is available in some builds; at minimum this is fine for small datasets but should be noted as a scaling concern. |
| 13 | `deep_link` is fake for all offers | `flight_deal_finder/api/flightapi.py:110` | Always generates a Google Travel search URL, not the actual booking link from the API. If FlightAPI.io returns a real deep link, parse and use it; otherwise rename the field to `search_link` to avoid user confusion. |

---

## P2 — Architecture / Features

| # | Issue | File(s) | Details |
|---|-------|---------|---------|
| 14 | `search_roundtrip` is dead code | `flight_deal_finder/api/flightapi.py:147-174` | Method exists, fully tested, but `DealEngine.run()` never calls it. The engine only uses `search_window` (one-way only). Either wire roundtrip into `run()` for routes that need return flights, or remove the method to reduce maintenance surface. |
| 15 | `check_interval_h` in watchlist is unused | `watchlist.yaml` (example + live) | Every route declares `check_interval_h` but engine and CLI never read it. It's supposed to drive cron scheduling but currently ignored. Could be used by a future scheduler or removed. |
| 16 | `providers` list in config is a no-op | `flight_deal_finder/engine.py:66-70` | Only `"flightapi"` is supported. The fallback logic (`if "flightapi" not in enabled_providers`) is fine for future expansion, but right now it's dead complexity. Document the roadmap or simplify. |
| 17 | No structured output from `check` command | `flight_deal_finder/cli.py:15-20` | `flight-deals check` runs silently on success (only logs). User sees nothing unless a deal fires. Print a summary: "Checked 3 routes, 12 offers, 1 deal found". |
| 18 | Console alerts bypass channel list in dry-run | `flight_deal_finder/engine.py:152-154` | In dry-run mode the engine instantiates a *new* `ConsoleChannel()` instead of re-using `self.channels[0]`. Harmless, but inconsistent — use `self.channels[0]` if it's a `ConsoleChannel`. |
| 19 | `tests/test_cli.py` `history` test passes a 6-tuple but asserts on 5-field output | `tests/test_cli.py:76-82` | The test data has 6 elements but the assertion matches the buggy 5-field unpacking. If `history` is fixed (P0 #4), this test must be updated too. |
| 20 | `tests/test_engine.py` mixes integration concerns | `tests/test_engine.py` | Several tests use `patch.object(DealEngine, "__init__", lambda self: None)` which is a sharp pattern that bypasses the actual constructor. It works but makes tests brittle to init changes. Prefer a factory fixture that injects a fully mocked config. |

---

## P3 — Polish / DX

| # | Issue | File(s) | Details |
|---|-------|---------|---------|
| 21 | `.gitignore` gaps | `.gitignore` | Missing `.pytest_cache/`, `.ruff_cache/`, `.coverage` (present in repo but ignored in file). Add them. |
| 22 | `__init__.py` is a stub | `flight_deal_finder/__init__.py` | Only contains a module docstring. Add `__all__` and expose top-level classes (`DealEngine`, `FlightApiClient`, `Deal`) for programmatic use. |
| 23 | `README` cron snippet uses wrong module path | `README.md:69` | `python -m flight_deal_finder.cli check` — the module path is correct, but since `flight-deals` entrypoint exists, suggest using that: `flight-deals check`. |
| 24 | `pyproject.toml` lacks coverage tooling | `pyproject.toml` | No `pytest-cov` in dev deps, no coverage config. Add `pytest-cov>=6.0` and a `[tool.coverage.run]` section if coverage is desired. |
| 25 | `EmailChannel` uses plain-text only | `flight_deal_finder/alerts/channels.py:46-84` | HTML email would look better for deal links. Minor, but worth a note. |

---

## Recommended First Sprint (do in order)

1. **Fix lint + `.gitignore`** — `ruff check --fix`, add cache dirs. Pure hygiene, zero risk.
2. **Fix P0 bugs** — `source` default in `db.py`, `history` CLI output, `search_roundtrip` error handling.
3. **Close HTTP client** — add `FlightApiClient.close()` and call it from `DealEngine.run()`.
4. **Add route validation** — `dataclass` for routes with `required=True` fields; skip malformed entries with a warning.
5. **Remove or use dead dependencies** — decide on `rich`/`beautifulsoup4`/`lxml`.
6. **Wire `search_roundtrip` or remove it** — architectural decision on whether roundtrip is a desired feature.

---

*Report generated from full source read. All file paths are relative to project root `/home/dimitar/projects/flight-deal-finder/`.*
