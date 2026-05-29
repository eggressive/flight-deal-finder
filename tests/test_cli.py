"""Tests for flight_deal_finder.cli — Click commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from flight_deal_finder.cli import main


class TestCheckCommand:
    def test_check_invokes_engine_run(self):
        runner = CliRunner()
        with patch("flight_deal_finder.cli.DealEngine") as mock_engine:
            mock_instance = MagicMock()
            mock_engine.return_value = mock_instance

            result = runner.invoke(main, ["check"])
            assert result.exit_code == 0
            mock_engine.assert_called_once_with(dry_run=False)
            mock_instance.run.assert_called_once()

    def test_check_dry_run_passes_flag(self):
        runner = CliRunner()
        with patch("flight_deal_finder.cli.DealEngine") as mock_engine:
            mock_instance = MagicMock()
            mock_engine.return_value = mock_instance

            result = runner.invoke(main, ["check", "--dry-run"])
            assert result.exit_code == 0
            mock_engine.assert_called_once_with(dry_run=True)


class TestWatchlistCommand:
    def test_watchlist_prints_routes(self, tmp_watchlist, monkeypatch):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        runner = CliRunner()

        with patch("flight_deal_finder.config.load_config") as mock_load:
            mock_load.return_value = {
                "routes": [
                    {"name": "AMS → JFK", "origin": "AMS", "destination": "JFK",
                     "max_price": 300, "enabled": True},
                    {"name": "AMS → SOF", "origin": "AMS", "destination": "SOF",
                     "max_price": 200, "enabled": False},
                ],
            }
            result = runner.invoke(main, ["watchlist"])
            assert result.exit_code == 0
            assert "AMS→JFK" in result.output
            assert "AMS→SOF" in result.output
            assert "🟢" in result.output
            assert "⚫" in result.output

    def test_watchlist_shows_max_price(self, tmp_watchlist, monkeypatch):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        runner = CliRunner()
        with patch("flight_deal_finder.config.load_config") as mock_load:
            mock_load.return_value = {
                "routes": [
                    {"name": "test", "origin": "AMS", "destination": "JFK",
                     "max_price": 350, "enabled": True},
                ],
            }
            result = runner.invoke(main, ["watchlist"])
            assert "€350" in result.output


class TestHistoryCommand:
    def test_history_prints_rows(self, tmp_watchlist, monkeypatch):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        runner = CliRunner()
        with patch("flight_deal_finder.db.get_history") as mock_history:
            mock_history.return_value = [
                ("AMS", "JFK", 300.0, "2026-08-15", "2026-05-29 12:00", "flightapi"),
            ]
            result = runner.invoke(main, ["history"])
            assert result.exit_code == 0
            assert "AMS" in result.output
            assert "JFK" in result.output
            assert "300.0" in result.output

    def test_history_empty_shows_message(self, tmp_watchlist, monkeypatch):
        monkeypatch.setenv("FLIGHTAPI_API_KEY", "test-key")
        runner = CliRunner()
        with patch("flight_deal_finder.db.get_history") as mock_history:
            mock_history.return_value = []
            result = runner.invoke(main, ["history"])
            assert result.exit_code == 0
            assert "No price history" in result.output
