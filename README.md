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

# 4. Edit your watchlist
vim watchlist.yaml

# 5. One-shot check
flight-deals check

# 6. Dry-run (no alerts sent, just see what would fire)
flight-deals check --dry-run

# 7. View history
flight-deals history
```

## Architecture

```
watchlist.yaml  ──→  DealEngine  ──→  FlightAPI.io (oneway + roundtrip)
                          │
                          ├── price history (SQLite)
                          ├── deal scoring (median-based)
                          └── alert channels (console, email, Telegram, Obsidian)
```

## API Provider

| Feature | FlightAPI.io |
|---------|-------------|
| Auth | API key in URL (no OAuth) |
| Free tier | 20 calls |
| Pricing | Lite $49/mo, Standard $99/mo |
| Coverage | 700+ airlines |
| Endpoints | Oneway, roundtrip, multi-city, tracking, schedules |
| Credits | 2 per flight search |

## Alert Channels

| Channel | Config |
|---------|--------|
| `console` | Always on |
| `email` | SMTP via `.env` |
| `telegram` | Bot token + chat ID via `.env` |
| `obsidian` | Writes to `Log/flight-deals-YYYY-MM-DD.md` |

## Cron Setup

```bash
# Run every 6 hours
0 */6 * * * cd ~/projects/flight-deal-finder && /path/to/venv/bin/python -m flight_deal_finder.cli check >> /tmp/flight-deals.log 2>&1
```
