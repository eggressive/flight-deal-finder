"""Tests for flight_deal_finder.engine — DealEngine orchestration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from flight_deal_finder.api.flightapi import FlightOffer
from flight_deal_finder.engine import DealEngine


@pytest.fixture
def mock_db():
    """Mock all db module functions."""
    with (
        patch("flight_deal_finder.engine.get_median_price") as mock_median,
        patch("flight_deal_finder.engine.insert_price") as mock_insert,
        patch("flight_deal_finder.engine.was_alerted_recently") as mock_was_alerted,
        patch("flight_deal_finder.engine.record_alert") as mock_record,
    ):
        mock_median.return_value = 400.0
        mock_was_alerted.return_value = False
        yield {
            "median": mock_median,
            "insert": mock_insert,
            "was_alerted": mock_was_alerted,
            "record": mock_record,
        }


@pytest.fixture
def engine_with_tmp_config(tmp_watchlist, mock_db, monkeypatch):
    """Create a DealEngine that uses the temp watchlist."""
    monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
    with patch("flight_deal_finder.engine.load_dotenv", return_value=None):
        yield DealEngine(dry_run=False)


class TestDealEngineInit:
    def test_loads_config_and_secrets(self, tmp_watchlist, monkeypatch):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        with patch("flight_deal_finder.engine.load_config") as mock_load_cfg:
            mock_load_cfg.return_value = {
                "_secrets": {"flightapi_api_key": "test-key"},
                "alerts": {"channels": ["console"]},
                "routes": [],
                "providers": ["flightapi"],
            }
            engine = DealEngine()
            assert engine.secrets["flightapi_api_key"] == "test-key"

    def test_channel_wiring_console_only(self, tmp_watchlist, monkeypatch):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        with patch("flight_deal_finder.engine.load_config") as mock_load_cfg:
            mock_load_cfg.return_value = {
                "_secrets": {"flightapi_api_key": "test-key"},
                "alerts": {"channels": ["console"]},
                "routes": [],
                "providers": ["flightapi"],
            }
            engine = DealEngine()
            assert len(engine.channels) == 1  # console always present

    def test_channel_wiring_all_channels(self, tmp_watchlist, monkeypatch):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        monkeypatch.setenv("SMTP_HOST", "smtp.test.com")
        monkeypatch.setenv("SMTP_PORT", "587")
        monkeypatch.setenv("SMTP_USER", "user")
        monkeypatch.setenv("SMTP_PASSWORD", "pass")
        monkeypatch.setenv("ALERT_EMAIL_FROM", "from@test.com")
        monkeypatch.setenv("ALERT_EMAIL_TO", "to@test.com")
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-tok")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/vault")
        with patch("flight_deal_finder.engine.load_config") as mock_load_cfg:
            mock_load_cfg.return_value = {
                "_secrets": {
                    "flightapi_api_key": "test-key",
                    "smtp_host": "smtp.test.com",
                    "smtp_port": 587,
                    "smtp_user": "user",
                    "smtp_password": "pass",
                    "alert_email_from": "from@test.com",
                    "alert_email_to": "to@test.com",
                    "telegram_bot_token": "bot-tok",
                    "telegram_chat_id": "123",
                    "obsidian_vault_path": "/tmp/vault",
                },
                "alerts": {"channels": ["email", "telegram", "obsidian"]},
                "routes": [],
                "providers": ["flightapi"],
            }
            engine = DealEngine()
            # console + email + telegram + obsidian = 4
            assert len(engine.channels) == 4

    def test_channel_wiring_email_configured(self, tmp_watchlist, monkeypatch):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        monkeypatch.setenv("SMTP_HOST", "smtp.test.com")
        with patch("flight_deal_finder.engine.load_config") as mock_load_cfg:
            mock_load_cfg.return_value = {
                "_secrets": {
                    "flightapi_api_key": "test-key",
                    "smtp_host": "smtp.test.com",
                    "smtp_port": 587,
                    "smtp_user": "user",
                    "smtp_password": "",
                    "alert_email_from": "",
                    "alert_email_to": "",
                },
                "alerts": {"channels": ["email"]},
                "routes": [],
                "providers": ["flightapi"],
            }
            engine = DealEngine()
            assert len(engine.channels) == 2  # console + email


class TestDealEngineRun:
    def test_no_providers_returns_early(self, tmp_watchlist, monkeypatch):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        with patch("flight_deal_finder.engine.load_config") as mock_load_cfg:
            mock_load_cfg.return_value = {
                "_secrets": {"flightapi_api_key": "test-key"},
                "alerts": {"channels": ["console"]},
                "routes": [{"name": "test", "origin": "AMS", "destination": "JFK",
                            "max_price": 300, "date_window": ["2026-08-01", "2026-08-02"]}],
                "providers": [],
            }
            engine = DealEngine()
            engine.run()  # should warn and return without making API calls

    def test_skips_disabled_routes(self, tmp_watchlist, monkeypatch):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        with patch("flight_deal_finder.engine.load_config") as _mock_cfg:
            alerts = {"channels": ["console"], "deal_threshold_pct": 25,
                      "cooldown_hours": 168}
            _mock_cfg.return_value = {
                "_secrets": {"flightapi_api_key": "test-key"},
                "alerts": alerts,
                "routes": [{"name": "disabled", "origin": "AMS", "destination": "SOF",
                            "max_price": 200, "date_window": ["2026-08-01", "2026-08-02"],
                            "enabled": False}],
                "providers": ["flightapi"],
            }
            engine = DealEngine()
            # Should not call search_window — route is disabled
            engine.run()

    def test_direct_only_filters_connecting_flights(self, tmp_watchlist, monkeypatch,
                                                     connecting_offer, mock_db):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        direct_offer = FlightOffer(
            origin="AMS", destination="SOF", price_eur=150.0,
            departure_date="2026-07-20", return_date=None,
            airline="Bulgaria Air", stops=0,
            deep_link="https://example.com",
        )
        with (
            patch("flight_deal_finder.engine.load_config"),
            patch.object(DealEngine, "__init__", lambda self: None),
        ):
            engine = DealEngine.__new__(DealEngine)
            alerts = {"channels": ["console"], "deal_threshold_pct": 25,
                      "cooldown_hours": 168}
            engine.config = {
                "_secrets": {"flightapi_api_key": "test-key"},
                "alerts": alerts,
                "routes": [{"name": "AMS->SOF (direct only)", "origin": "AMS",
                            "destination": "SOF", "max_price": 200,
                            "date_window": ["2026-07-15", "2026-07-20"],
                            "direct_only": True, "enabled": True}],
                "providers": ["flightapi"],
            }
            engine.dry_run = True
            engine.channels = [MagicMock()]
            engine.flightapi = MagicMock()
            engine.flightapi.search_window.return_value = [connecting_offer, direct_offer]
            engine.run()

            # connecting_offer (stops=2) should be filtered out
            # direct_offer (stops=0) should pass through
            # insert_price should only be called for direct_offer
            calls = mock_db["insert"].call_args_list
            assert len(calls) == 1
            assert calls[0][1]["destination"] == "SOF"
            assert calls[0][1]["airline"] == "Bulgaria Air"

    def test_direct_only_passes_nonstop(self, tmp_watchlist, monkeypatch, mock_db):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        direct_offer = FlightOffer(
            origin="AMS", destination="SOF", price_eur=150.0,
            departure_date="2026-07-20", return_date=None,
            airline="Bulgaria Air", stops=0,
            deep_link="https://example.com",
        )
        with patch("flight_deal_finder.engine.load_config"), \
             patch.object(DealEngine, "__init__", lambda self: None):
            engine = DealEngine.__new__(DealEngine)
            engine.config = {
                "_secrets": {"flightapi_api_key": "test-key"},
                "alerts": {"channels": ["console"], "deal_threshold_pct": 0, "cooldown_hours": 168},
                "routes": [{"name": "test", "origin": "AMS", "destination": "SOF",
                            "max_price": 200, "date_window": ["2026-07-20", "2026-07-20"],
                            "direct_only": True, "enabled": True}],
                "providers": ["flightapi"],
            }
            engine.dry_run = True
            engine.channels = [MagicMock()]
            engine.flightapi = MagicMock()
            engine.flightapi.search_window.return_value = [direct_offer]
            engine.run()
            assert mock_db["insert"].call_count == 1

    def test_run_no_offers_found(self, tmp_watchlist, monkeypatch, mock_db):
        """Route returns zero offers — logger path covered."""
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        alerts = {"channels": ["console"], "deal_threshold_pct": 25,
                  "cooldown_hours": 168}
        with (
            patch("flight_deal_finder.engine.load_config"),
            patch.object(DealEngine, "__init__", lambda self: None),
        ):
            engine = DealEngine.__new__(DealEngine)
            engine.dry_run = False
            engine.channels = [MagicMock()]
            engine.config = {
                "_secrets": {"flightapi_api_key": "test-key"},
                "alerts": alerts,
                "routes": [{"name": "AMS->SOF", "origin": "AMS",
                            "destination": "SOF", "max_price": 200,
                            "date_window": ["2026-07-01", "2026-07-01"],
                            "enabled": True}],
                "providers": ["flightapi"],
            }
            engine.flightapi = MagicMock()
            engine.flightapi.search_window.return_value = []
            engine.run()
            mock_db["insert"].assert_not_called()

    def test_deal_detected_when_discount_above_threshold(self, tmp_watchlist,
                                                          monkeypatch, mock_db):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        offer = FlightOffer(
            origin="AMS", destination="JFK", price_eur=280.0,
            departure_date="2026-08-15", return_date=None,
            airline="KLM", stops=0, deep_link="https://example.com",
        )
        with (
            patch("flight_deal_finder.engine.load_config"),
            patch.object(DealEngine, "__init__", lambda self: None),
        ):
            engine = DealEngine.__new__(DealEngine)
            engine.config = {
                "_secrets": {"flightapi_api_key": "test-key"},
                "alerts": {"channels": ["console"], "deal_threshold_pct": 25,
                           "cooldown_hours": 168},
                "routes": [{"name": "AMS->JFK", "origin": "AMS", "destination": "JFK",
                            "max_price": 350, "date_window": ["2026-08-15", "2026-08-15"]}],
                "providers": ["flightapi"],
            }
            engine.dry_run = True
            engine.channels = [MagicMock()]
            engine.flightapi = MagicMock()
            engine.flightapi.search_window.return_value = [offer]
            mock_db["median"].return_value = 400.0  # 280 is 30% below 400

            engine.run()
            assert mock_db["insert"].call_count == 1
            # dry_run: ConsoleChannel().send() is called directly, not through self.channels
            mock_db["record"].assert_not_called()

    def test_skips_when_discount_below_threshold(self, tmp_watchlist, monkeypatch,
                                                  mock_db):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        offer = FlightOffer(
            origin="AMS", destination="JFK", price_eur=380.0,
            departure_date="2026-08-15", return_date=None,
            airline="KLM", stops=0, deep_link="https://example.com",
        )
        with patch("flight_deal_finder.engine.load_config"), \
             patch.object(DealEngine, "__init__", lambda self: None):
            engine = DealEngine.__new__(DealEngine)
            engine.dry_run = False
            engine.channels = [MagicMock()]
            alerts = {"channels": ["console"], "deal_threshold_pct": 25,
                      "cooldown_hours": 168}
            engine.config = {
                "_secrets": {"flightapi_api_key": "test-key"},
                "alerts": alerts,
                "routes": [{"name": "AMS->JFK", "origin": "AMS", "destination": "JFK",
                            "max_price": 350, "date_window": ["2026-08-15", "2026-08-15"]}],
                "providers": ["flightapi"],
            }
            engine.flightapi = MagicMock()
            engine.flightapi.search_window.return_value = [offer]
            mock_db["median"].return_value = 400.0  # 380 is 5% below 400

            engine.run()
            # price was inserted but no deal alert
            assert mock_db["insert"].call_count == 1
            engine.channels[0].send.assert_not_called()

    def test_skips_when_already_alerted_within_cooldown(self, tmp_watchlist,
                                                         monkeypatch, mock_db):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        offer = FlightOffer(
            origin="AMS", destination="JFK", price_eur=280.0,
            departure_date="2026-08-15", return_date=None,
            airline="KLM", stops=0, deep_link="https://example.com",
        )
        with patch("flight_deal_finder.engine.load_config"), \
             patch.object(DealEngine, "__init__", lambda self: None):
            engine = DealEngine.__new__(DealEngine)
            engine.dry_run = False
            engine.channels = [MagicMock()]
            engine.config = {
                "_secrets": {"flightapi_api_key": "test-key"},
                "alerts": {"channels": ["console"], "deal_threshold_pct": 0, "cooldown_hours": 168},
                "routes": [{"name": "AMS->JFK", "origin": "AMS", "destination": "JFK",
                            "max_price": 350, "date_window": ["2026-08-15", "2026-08-15"]}],
                "providers": ["flightapi"],
            }
            engine.flightapi = MagicMock()
            engine.flightapi.search_window.return_value = [offer]
            mock_db["was_alerted"].return_value = True  # already alerted

            engine.run()
            engine.channels[0].send.assert_not_called()

    def test_no_deal_when_no_median(self, tmp_watchlist, monkeypatch, mock_db):
        """When no historical median exists, discount_pct is None.
        The is_deal check requires both price <= max_price AND
        (discount_pct is not None AND discount_pct >= threshold).
        With no median, discount_pct is None → is_deal is False.
        This prevents false-positive alerts without historical data."""
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        offer = FlightOffer(
            origin="AMS", destination="JFK", price_eur=300.0,
            departure_date="2026-08-15", return_date=None,
            airline="KLM", stops=0, deep_link="https://example.com",
        )
        with patch("flight_deal_finder.engine.load_config"), \
             patch.object(DealEngine, "__init__", lambda self: None):
            engine = DealEngine.__new__(DealEngine)
            engine.dry_run = False
            engine.channels = [MagicMock()]
            engine.config = {
                "_secrets": {"flightapi_api_key": "test-key"},
                "alerts": {"channels": ["console"], "deal_threshold_pct": 0, "cooldown_hours": 168},
                "routes": [{"name": "AMS->JFK", "origin": "AMS", "destination": "JFK",
                            "max_price": 350, "date_window": ["2026-08-15", "2026-08-15"]}],
                "providers": ["flightapi"],
            }
            engine.flightapi = MagicMock()
            engine.flightapi.search_window.return_value = [offer]
            mock_db["median"].return_value = None

            engine.run()
            # price inserted but no deal triggered (discount_pct is None)
            assert mock_db["insert"].call_count == 1
            engine.channels[0].send.assert_not_called()

    def test_non_dry_run_sends_and_records(self, tmp_watchlist, monkeypatch, mock_db):
        """In live mode, alerts get sent and recorded."""
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        offer = FlightOffer(
            origin="AMS", destination="JFK", price_eur=200.0,
            departure_date="2026-08-15", return_date=None,
            airline="KLM", stops=0, deep_link="https://example.com",
        )
        with patch("flight_deal_finder.engine.load_config"), \
             patch.object(DealEngine, "__init__", lambda self: None):
            engine = DealEngine.__new__(DealEngine)
            engine.dry_run = False
            engine.channels = [MagicMock(), MagicMock()]
            engine.config = {
                "_secrets": {"flightapi_api_key": "test-key"},
                "alerts": {"channels": ["console"], "deal_threshold_pct": 0, "cooldown_hours": 168},
                "routes": [{"name": "AMS->JFK", "origin": "AMS", "destination": "JFK",
                            "max_price": 350, "date_window": ["2026-08-15", "2026-08-15"]}],
                "providers": ["flightapi"],
            }
            engine.flightapi = MagicMock()
            engine.flightapi.search_window.return_value = [offer]
            mock_db["median"].return_value = 400.0  # 50% below → deal

            engine.run()
            # Both channels got called
            engine.channels[0].send.assert_called_once()
            engine.channels[1].send.assert_called_once()
            # Alert recorded
            mock_db["record"].assert_called_once()
