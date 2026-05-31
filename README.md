# Flight Deal Finder

Personalized flight deal alerts. Set routes + max prices → get notified when prices drop.

**Now using [FlightAPI.io](https://flightapi.io)** — simple API-key auth (no OAuth, no enterprise gate).
Amadeus Self-Service is closed to new registrations as of June 2026.

## Quick Start

```bash
# 1. Install
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# 2. Get an API key
# → https://flightapi.io  (20 free calls, then Lite from $49/mo)

# 3. Configure
cp .env.example .env
# Fill in FLIGHTAPI_API_KEY from your FlightAPI dashboard

# 4. Set up your watchlist
cp watchlist.yaml.example watchlist.yaml
vim watchlist.yaml
# (If watchlist.yaml is missing, the tool auto-copies watchlist.yaml.example on first run)

# 5. One-shot check
flight-deals check

# 6. Dry-run (no alerts sent, just see what would fire)
flight-deals check --dry-run

# 7. View history
flight-deals history

# 8. List watchlist routes
flight-deals watchlist
```

## Architecture

```
watchlist.yaml  ──→  Route Validation  ──→  DealEngine  ──→  FlightAPI.io (oneway search across date window)
                              │
                              ├── price history (SQLite)
                              ├── deal scoring (median-based)
                              └── alert channels (console, email, Telegram, Obsidian)
```

Invalid routes (missing fields, bad types) are silently skipped with a logged warning.

## API Provider

| Feature | FlightAPI.io |
|---------|-------------|
| Auth | API key in URL (no OAuth) |
| Free tier | 20 calls |
| Pricing | Lite $49/mo, Standard $99/mo |
| Coverage | 700+ airlines |
| Endpoints | Oneway, roundtrip, multi-city, tracking, schedules |
| Credits | 2 per flight search |

## Route Options

The watchlist supports these optional fields per route:

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `true` | Set `false` to skip checking this route |
| `direct_only` | `false` | Skip flights with 1+ stops |
| `min_stay` | `7` | Minimum trip length in days |
| `max_stay` | `14` | Maximum trip length in days |

## Alert Channels

| Channel | Config |
|---------|--------|
| `console` | Always on |
| `email` | SMTP via `.env` |
| `telegram` | Bot token + chat ID via `.env` |
| `obsidian` | Writes to `Log/flight-deals-YYYY-MM-DD.md` |

## Development

```bash
# Run tests
pytest tests/

# Run lint
cd ~/projects/flight-deal-finder && source venv/bin/activate && ruff check flight_deal_finder/ tests/
```

The project includes a full pytest suite covering channels, CLI, config, DB, engine,
flight API, and route validation.

## Cron Setup

```bash
# Run every 6 hours
0 */6 * * * cd ~/projects/flight-deal-finder && /path/to/venv/bin/flight-deals check >> /tmp/flight-deals.log 2>&1
```

The CLI uses `FlightApiClient` with automatic HTTP cleanup via context manager.
