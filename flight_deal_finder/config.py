"""Configuration loader — YAML watchlist + .env secrets."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WATCHLIST = PROJECT_ROOT / "watchlist.yaml"


def load_config(path: str | Path | None = None) -> dict:
    """Load watchlist YAML, merge with .env secrets."""
    load_dotenv(PROJECT_ROOT / ".env")

    path = Path(path) if path else DEFAULT_WATCHLIST
    if not path.exists():
        raise FileNotFoundError(f"Watchlist not found: {path}")

    with open(path) as f:
        config = yaml.safe_load(f)

    # Inject secrets from env
    config["_secrets"] = {
        "flightapi_api_key": os.getenv("FLIGHTAPI_API_KEY"),
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "smtp_user": os.getenv("SMTP_USER"),
        "smtp_password": os.getenv("SMTP_PASSWORD"),
        "alert_email_from": os.getenv("ALERT_EMAIL_FROM"),
        "alert_email_to": os.getenv("ALERT_EMAIL_TO"),
        "obsidian_vault_path": os.getenv("OBSIDIAN_VAULT_PATH"),
    }
    return config
