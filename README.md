# Flight Deal Finder

Personalized flight deal alerts. Set routes + max prices → get notified when prices drop.

## Quick Start

```bash
# 1. Install
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
# Fill in your Amadeus API key/secret from https://developers.amadeus.com

# 3. Edit your watchlist
vim watchlist.yaml

# 4. One-shot check
flight-deals check

# 5. Dry-run (no alerts sent, just see what would fire)
flight-deals check --dry-run

# 6. View history
flight-deals history
```

## Architecture

```
watchlist.yaml  ──→  DealEngine  ──→  API Clients (Amadeus)
                          │
                          ├── price history (SQLite)
                          ├── deal scoring (median-based)
                          └── alert channels (console, email, Telegram, Obsidian)
```

## Alert Channels

Enable channels in `watchlist.yaml` → `alerts.channels`:

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

## API Strategy

- **Now → July 2026:** Amadeus Self-Service (2,000 free calls/mo)
- **After July 2026:** Google Flights scraper or Duffel

## Project Status

- [x] Amadeus API client
- [x] SQLite price history
- [x] Deal scoring (median-based)
- [x] Multi-channel alerts (console, email, Telegram, Obsidian)
- [x] Dedup/cooldown
- [x] Dry-run mode
- [ ] Google Flights scraper (post-Amadeus)
- [ ] Web dashboard
- [ ] Push notifications
- [ ] Historical trend charts
