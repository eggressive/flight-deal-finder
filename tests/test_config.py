"""Tests for flight_deal_finder.config — YAML loading and .env secret injection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from flight_deal_finder.config import load_config


class TestLoadConfig:
    def test_loads_routes_from_yaml(self, tmp_watchlist: Path):
        with patch("flight_deal_finder.config.load_dotenv"):
            config = load_config(tmp_watchlist)
        routes = config["routes"]
        assert len(routes) == 2
        assert routes[0]["origin"] == "AMS"
        assert routes[0]["destination"] == "JFK"
        assert routes[0]["enabled"] is True

    def test_loads_direct_only_field(self, tmp_watchlist: Path):
        with patch("flight_deal_finder.config.load_dotenv"):
            config = load_config(tmp_watchlist)
        sofia = config["routes"][1]
        assert sofia["direct_only"] is True

    def test_raises_file_not_found_for_missing_file(self):
        with (
            patch("flight_deal_finder.config.load_dotenv"),
            pytest.raises(FileNotFoundError, match="Watchlist not found"),
        ):
            load_config("/nonexistent/path/watchlist.yaml")

    def test_injects_secrets_from_env(self, tmp_watchlist: Path, monkeypatch):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "secret-key-123")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-token-456")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100999")

        config = load_config(tmp_watchlist)
        secrets = config["_secrets"]
        assert secrets["flightapi_api_key"] == "secret-key-123"
        assert secrets["telegram_bot_token"] == "bot-token-456"
        assert secrets["telegram_chat_id"] == "-100999"

    def test_defaults_when_env_vars_missing(self, tmp_watchlist: Path, monkeypatch):
        monkeypatch.delenv("FLIGHTAPI_API_KEY", raising=False)
        monkeypatch.delenv("SMTP_HOST", raising=False)

        with patch("flight_deal_finder.config.load_dotenv"):
            config = load_config(tmp_watchlist)
        secrets = config["_secrets"]
        assert secrets["flightapi_api_key"] is None
        assert secrets["smtp_host"] == "smtp.gmail.com"
        assert secrets["smtp_port"] == 587

    def test_custom_path_argument(self, tmp_watchlist: Path):
        with patch("flight_deal_finder.config.load_dotenv"):
            config = load_config(str(tmp_watchlist))
        assert config["providers"] == ["flightapi"]
