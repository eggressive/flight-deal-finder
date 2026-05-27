"""CLI entry point."""

from __future__ import annotations

import click

from flight_deal_finder.engine import DealEngine


@click.group()
def main() -> None:
    """Flight Deal Finder — personalized flight price alerts."""


@main.command()
@click.option("--dry-run", is_flag=True, help="Check prices without sending alerts")
def check(dry_run: bool) -> None:
    """Run a one-shot price check against the watchlist."""
    engine = DealEngine(dry_run=dry_run)
    engine.run()


@main.command()
def watchlist() -> None:
    """Print the current watchlist."""
    from flight_deal_finder.config import load_config

    config = load_config()
    for route in config["routes"]:
        status = "🟢" if route.get("enabled", True) else "⚫"
        print(
            f"{status} {route['origin']}→{route['destination']} "
            f"max €{route['max_price']} | {route['name']}"
        )


@main.command()
def history() -> None:
    """Show recent price history."""
    from flight_deal_finder.db import get_history

    rows = get_history(limit=20)
    if not rows:
        print("No price history yet. Run `check` first.")
        return
    for row in rows:
        print(f"[{row[1]}] {row[0]}→{row[2]}: €{row[3]} @ {row[4]}")


if __name__ == "__main__":
    main()
