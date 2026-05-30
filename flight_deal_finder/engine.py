"""Deal Engine — orchestrates API checks, price comparison, and alert dispatching."""

from __future__ import annotations

import logging
from typing import Any

from flight_deal_finder.alerts.channels import (
    Deal,
    ConsoleChannel,
    EmailChannel,
    ObsidianChannel,
    TelegramChannel,
)
from flight_deal_finder.api.flightapi import FlightApiClient
from flight_deal_finder.config import load_config
from flight_deal_finder.db import get_median_price, insert_price, record_alert, was_alerted_recently

logger = logging.getLogger(__name__)


class DealEngine:
    def __init__(self, dry_run: bool = False) -> None:
        self.config = load_config()
        self.dry_run = dry_run
        self.secrets: dict[str, Any] = self.config["_secrets"]

        # Build API clients
        self.flightapi = FlightApiClient(
            self.secrets["flightapi_api_key"] or "",
        )

        # Build alert channels
        self.channels: list[Any] = [ConsoleChannel()]
        channels_cfg = self.config.get("alerts", {}).get("channels", [])

        if "email" in channels_cfg:
            self.channels.append(
                EmailChannel(
                    host=self.secrets["smtp_host"],
                    port=self.secrets["smtp_port"],
                    user=self.secrets["smtp_user"] or "",
                    password=self.secrets["smtp_password"] or "",
                    from_addr=self.secrets["alert_email_from"] or "",
                    to_addr=self.secrets["alert_email_to"] or "",
                )
            )

        if "telegram" in channels_cfg:
            self.channels.append(
                TelegramChannel(
                    bot_token=self.secrets["telegram_bot_token"] or "",
                    chat_id=self.secrets["telegram_chat_id"] or "",
                )
            )

        if "obsidian" in channels_cfg:
            vault = self.secrets.get("obsidian_vault_path") or ""
            self.channels.append(ObsidianChannel(vault_path=vault))

    def close(self) -> None:
        """Close underlying API clients to release connection resources."""
        self.flightapi.close()

    def run(self) -> None:
        """One-shot check against all enabled routes."""
        alert_cfg: dict[str, Any] = self.config.get("alerts", {})
        deal_threshold_pct: float = float(alert_cfg.get("deal_threshold_pct", 25))
        cooldown_hours: int = int(alert_cfg.get("cooldown_hours", 168))
        enabled_providers: list[str] = self.config.get("providers", ["flightapi"])

        if "flightapi" not in enabled_providers:
            logger.warning("No API providers configured. Nothing to do.")
            return

        for route in self.config.get("routes", []):
            if not route.get("enabled", True):
                continue

            origin = route["origin"]
            destination = route["destination"]
            max_price = route["max_price"]
            date_from, date_to = route["date_window"]
            min_stay = route.get("min_stay", 7)
            max_stay = route.get("max_stay", 14)
            route_name = route["name"]

            logger.info("Checking %s (%s→%s)", route_name, origin, destination)

            # Search across date window
            offers = self.flightapi.search_window(
                origin, destination, date_from, date_to, min_stay, max_stay, max_price
            )

            if not offers:
                logger.info("  No offers found under €%.0f", max_price)
                continue

            # Get historical median for deal scoring
            median = get_median_price(origin, destination)

            for offer in offers:
                # Store the price regardless
                insert_price(
                    origin=origin,
                    destination=destination,
                    price_eur=offer.price_eur,
                    departure_date=offer.departure_date,
                    return_date=offer.return_date,
                    airline=offer.airline,
                    url=offer.deep_link,
                    source="amadeus",
                )

                # Deal logic
                discount_pct = None
                if median and median > 0:
                    discount_pct = ((median - offer.price_eur) / median) * 100

                is_deal = (
                    offer.price_eur <= max_price
                    and (discount_pct is not None and discount_pct >= deal_threshold_pct)
                )

                if not is_deal:
                    continue

                route_key = f"{origin}:{destination}:{offer.departure_date}"
                if was_alerted_recently(route_key, cooldown_hours):
                    logger.debug("  Skipping %s — already alerted recently", route_key)
                    continue

                deal = Deal(
                    origin=offer.origin,
                    destination=offer.destination,
                    price_eur=offer.price_eur,
                    departure_date=offer.departure_date,
                    return_date=offer.return_date,
                    airline=offer.airline,
                    stops=offer.stops,
                    median_price=median,
                    discount_pct=discount_pct,
                    deep_link=offer.deep_link,
                    route_name=route_name,
                )

                if self.dry_run:
                    logger.info("[DRY RUN] Would alert on: %s", route_name)
                    ConsoleChannel().send(deal)
                else:
                    for channel in self.channels:
                        channel.send(deal)
                    record_alert(route_key, offer.price_eur)
                    logger.info("✅ Alert sent: %s @ €%.2f", route_name, offer.price_eur)
