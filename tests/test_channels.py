"""Tests for flight_deal_finder.alerts.channels — Deal dataclass and alert channels."""

from __future__ import annotations

import dataclasses
from unittest.mock import MagicMock

from flight_deal_finder.alerts.channels import (
    ConsoleChannel,
    Deal,
    EmailChannel,
    ObsidianChannel,
    TelegramChannel,
)


class TestDeal:
    def test_fields_exist(self):
        fields = {f.name for f in dataclasses.fields(Deal)}
        expected = {
            "origin", "destination", "price_eur", "departure_date",
            "return_date", "airline", "stops", "median_price",
            "discount_pct", "deep_link", "route_name",
        }
        assert expected.issubset(fields)


class TestConsoleChannel:
    def test_send_prints_formatted_output(self, sample_deal: Deal, capfd):
        channel = ConsoleChannel()
        channel.send(sample_deal)
        captured = capfd.readouterr().out

        assert "Amsterdam → New York" in captured
        assert "AMS" in captured and "JFK" in captured
        assert "€300.00" in captured
        assert "25% below median" in captured
        assert "€400" in captured  # median
        assert "KLM" in captured
        assert "nonstop" in captured

    def test_send_with_none_median_and_discount(self, sample_deal: Deal, capfd):
        deal = dataclasses.replace(sample_deal, median_price=None, discount_pct=None)
        channel = ConsoleChannel()
        channel.send(deal)
        captured = capfd.readouterr().out

        assert "below median" not in captured
        assert "median" not in captured

    def test_send_with_stops_formatting(self, sample_deal: Deal, capfd):
        deal_1stop = dataclasses.replace(sample_deal, stops=1)
        channel = ConsoleChannel()
        channel.send(deal_1stop)
        captured = capfd.readouterr().out
        assert "1 stop(s)" in captured


class TestEmailChannel:
    def test_skips_when_not_configured(self, sample_deal: Deal, caplog):
        channel = EmailChannel(
            host="", port=587, user="", password="",
            from_addr="", to_addr="",
        )
        channel.send(sample_deal)
        assert "not fully configured" in caplog.text


class TestTelegramChannel:
    def test_skips_when_no_bot_token(self, sample_deal: Deal, caplog):
        channel = TelegramChannel(bot_token="", chat_id="")
        channel.send(sample_deal)
        assert "not configured" in caplog.text

    def test_sends_message_when_configured(self, sample_deal: Deal, mock_httpx_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_post.return_value = mock_response

        channel = TelegramChannel(bot_token="test-token", chat_id="12345")
        channel.send(sample_deal)

        mock_httpx_post.assert_called_once()
        call_args = mock_httpx_post.call_args
        assert call_args[0][0] == "https://api.telegram.org/bot/test-token/sendMessage"
        assert call_args[1]["json"]["chat_id"] == "12345"
        assert "Amsterdam" in call_args[1]["json"]["text"]


class TestObsidianChannel:
    def test_skips_when_no_vault_path(self, sample_deal: Deal, caplog):
        channel = ObsidianChannel(vault_path="")
        channel.send(sample_deal)
        assert "vault not found" in caplog.text

    def test_skips_when_vault_path_nonexistent(self, sample_deal: Deal, caplog, tmp_path):
        nonexistent = tmp_path / "nope"
        channel = ObsidianChannel(vault_path=str(nonexistent))
        channel.send(sample_deal)
        assert "vault not found" in caplog.text

    def test_writes_to_vault_when_configured(self, sample_deal: Deal, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        channel = ObsidianChannel(vault_path=str(vault))
        channel.send(sample_deal)

        today_log = vault / "Log"
        assert today_log.exists()
        md_files = list(today_log.glob("flight-deals-*.md"))
        assert len(md_files) == 1
        content = md_files[0].read_text()
        assert "Amsterdam → New York" in content
        assert "€300.00" in content
