"""Alert delivery channels: console, email, Telegram, Obsidian."""

from __future__ import annotations

import dataclasses
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Deal:
    origin: str
    destination: str
    price_eur: float
    departure_date: str
    return_date: str | None
    airline: str
    stops: int
    median_price: float | None
    discount_pct: float | None
    deep_link: str
    route_name: str


class ConsoleChannel:
    def send(self, deal: Deal) -> None:
        """Print to stdout."""
        pct_str = f" ({deal.discount_pct:.0f}% below median)" if deal.discount_pct else ""
        med_str = f" | median €{deal.median_price:.0f}" if deal.median_price else ""
        stops_str = "nonstop" if deal.stops == 0 else f"{deal.stops} stop(s)"
        print(
            f"🔥 {deal.route_name}\n"
            f"   {deal.origin} → {deal.destination} | {deal.departure_date}"
            + (f" → {deal.return_date}" if deal.return_date else "")
            + f"\n"
            f"   €{deal.price_eur:.2f}{pct_str}{med_str}\n"
            f"   {deal.airline} | {stops_str}\n"
        )


class EmailChannel:
    def __init__(self, host: str, port: int, user: str, password: str,
                 from_addr: str, to_addr: str) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_addr = from_addr
        self.to_addr = to_addr

    def send(self, deal: Deal) -> None:
        if not all([self.host, self.user, self.password, self.from_addr, self.to_addr]):
            logger.warning("Email channel not fully configured. Skipping.")
            return

        pct = f" ({deal.discount_pct:.0f}% below median)" if deal.discount_pct else ""
        body = (
            f"🔥 Flight Deal: {deal.route_name}\n\n"
            f"Route: {deal.origin} → {deal.destination}\n"
            f"Departure: {deal.departure_date}"
            + (f" | Return: {deal.return_date}\n" if deal.return_date else "\n")
            + f"Price: €{deal.price_eur:.2f}{pct}\n"
            f"Airline: {deal.airline} | Stops: {deal.stops}\n"
            + (f"Book: {deal.deep_link}\n" if deal.deep_link else "")
        )

        msg = MIMEText(body)
        msg["Subject"] = f"🔥 {deal.route_name} — €{deal.price_eur:.0f}"
        msg["From"] = self.from_addr
        msg["To"] = self.to_addr

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as s:
                s.starttls()
                s.login(self.user, self.password)
                s.send_message(msg)
            logger.info("Email alert sent for %s → %s", deal.origin, deal.destination)
        except Exception as e:
            logger.error("Failed to send email: %s", e)


class TelegramChannel:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, deal: Deal) -> None:
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram channel not configured. Skipping.")
            return

        pct = f" ({deal.discount_pct:.0f}% below median)" if deal.discount_pct else ""
        stops_str = "nonstop ✈️" if deal.stops == 0 else f"{deal.stops} stop(s)"
        text = (
            f"🔥 *{deal.route_name}*\n\n"
            f"*{deal.origin} → {deal.destination}*\n"
            f"📅 {deal.departure_date}"
            + (f" → {deal.return_date}\n" if deal.return_date else "\n")
            + f"💰 *€{deal.price_eur:.2f}*{pct}\n"
            f"🛫 {deal.airline} | {stops_str}\n"
            + (f"[Book now]({deal.deep_link})" if deal.deep_link else "")
        )

        # Use subprocess — avoids pulling in python-telegram-bot dep for one call
        try:
            import httpx

            url = f"https://api.telegram.org/bot/{self.bot_token}/sendMessage"
            resp = httpx.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
            resp.raise_for_status()
            logger.info("Telegram alert sent for %s → %s", deal.origin, deal.destination)
        except Exception as e:
            logger.error("Failed to send Telegram alert: %s", e)


class ObsidianChannel:
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path) if vault_path else None

    def send(self, deal: Deal) -> None:
        if not self.vault_path or not self.vault_path.exists():
            logger.warning("Obsidian vault not found. Skipping.")
            return

        pct = f" ({deal.discount_pct:.0f}% below median)" if deal.discount_pct else ""
        stops_str = "nonstop" if deal.stops == 0 else f"{deal.stops} stop(s)"
        today = datetime.now().strftime("%Y-%m-%d")

        note_path = self.vault_path / "Log" / f"flight-deals-{today}.md"
        note_path.parent.mkdir(parents=True, exist_ok=True)

        entry = (
            f"## 🔥 {deal.route_name}\n\n"
            f"- **Route:** {deal.origin} → {deal.destination}\n"
            f"- **Departure:** {deal.departure_date}"
            + (f" | **Return:** {deal.return_date}\n" if deal.return_date else "\n")
            + f"- **Price:** €{deal.price_eur:.2f}{pct}\n"
            f"- **Airline:** {deal.airline} | {stops_str}\n"
            + (f"- **Book:** {deal.deep_link}\n" if deal.deep_link else "")
            + f"- **Scraped:** {datetime.now().strftime('%H:%M')}\n\n"
        )

        mode = "a" if note_path.exists() else "w"
        with open(note_path, mode) as f:
            f.write(entry)
        logger.info("Deal logged to Obsidian: %s", note_path)
