"""Tests for flight_deal_finder.api.flightapi — URL building, response parsing, HTTP status."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from flight_deal_finder.api.flightapi import (
    ONEWAY_URL,
    ROUNDTRIP_URL,
    FlightApiClient,
    FlightOffer,
)


class TestFlightOffer:
    def test_instantiation(self):
        offer = FlightOffer(
            origin="AMS",
            destination="JFK",
            price_eur=300.0,
            departure_date="2026-08-15",
            return_date="2026-08-30",
            airline="KLM",
            stops=0,
            deep_link="https://example.com",
        )
        assert offer.origin == "AMS"
        assert offer.price_eur == 300.0
        assert offer.stops == 0

    def test_offer_no_return_date(self):
        offer = FlightOffer(
            origin="AMS",
            destination="JFK",
            price_eur=300.0,
            departure_date="2026-08-15",
            return_date=None,
            airline="KLM",
            stops=0,
            deep_link="https://example.com",
        )
        assert offer.return_date is None


class TestBuildUrl:
    def test_build_url_oneway_path(self):
        client = FlightApiClient(api_key="test-key-123")
        url = client._build_url(
            ONEWAY_URL,
            origin="AMS",
            destination="JFK",
            date="2026-08-15",
            adults="1",
            children="0",
            infants="0",
            cabin="Economy",
            currency="EUR",
        )
        expected = (
            "https://api.flightapi.io/onewaytrip/test-key-123/"
            "AMS/JFK/2026-08-15/1/0/0/Economy/EUR"
        )
        assert url == expected

    def test_build_url_roundtrip_path(self):
        client = FlightApiClient(api_key="key-abc")
        url = client._build_url(
            ROUNDTRIP_URL,
            origin="LHR",
            destination="CDG",
            dep_date="2026-09-01",
            ret_date="2026-09-15",
            adults="2",
            children="0",
            infants="0",
            cabin="Economy",
            currency="EUR",
        )
        expected = (
            "https://api.flightapi.io/roundtrip/key-abc/LHR/CDG/2026-09-01/2026-09-15"
            "/2/0/0/Economy/EUR"
        )
        assert url == expected

    def test_raises_value_error_on_missing_api_key(self):
        with pytest.raises(ValueError, match="API key"):
            FlightApiClient(api_key="")


class TestParseOffers:
    def test_parse_single_direct_flight(self, flightapi_response_oneway: dict):
        client = FlightApiClient(api_key="test-key")
        offers = client._parse_offers(flightapi_response_oneway, "AMS", "JFK")
        assert len(offers) == 1
        o = offers[0]
        assert o.origin == "AMS"
        assert o.destination == "JFK"
        assert o.price_eur == 300.0
        assert o.departure_date == "2026-08-15"
        assert o.airline == "KLM Royal Dutch Airlines"
        assert o.stops == 0
        assert o.return_date is None
        assert "AMS" in o.deep_link

    def test_parse_skips_unpriced_entries(self, flightapi_response_unpriced: dict):
        client = FlightApiClient(api_key="test-key")
        offers = client._parse_offers(flightapi_response_unpriced, "AMS", "JFK")
        assert len(offers) == 0

    def test_parse_skips_no_amount(self):
        client = FlightApiClient(api_key="test-key")
        data = {
            "carriers": [],
            "legs": [],
            "segments": [],
            "itineraries": [
                {
                    "id": 1,
                    "leg_ids": [],
                    "pricing_options": [{"price": {}}],
                },
            ],
        }
        offers = client._parse_offers(data, "AMS", "JFK")
        assert len(offers) == 0

    def test_parse_empty_response(self):
        client = FlightApiClient(api_key="test-key")
        offers = client._parse_offers({}, "AMS", "JFK")
        assert len(offers) == 0

    def test_parse_two_legs_return_date(self):
        client = FlightApiClient(api_key="test-key")
        data = {
            "carriers": [{"id": 1, "name": "KLM", "iata": "KL"}],
            "legs": [
                {"id": 1001, "departure": "2026-08-15T10:00:00", "stop_count": 1,
                 "marketing_carrier_ids": [1], "segment_ids": [2001]},
                {"id": 1002, "departure": "2026-08-30T18:00:00", "stop_count": 0,
                 "marketing_carrier_ids": [1], "segment_ids": [2002]},
            ],
            "segments": [
                {"id": 2001, "marketing_carrier_id": 1},
                {"id": 2002, "marketing_carrier_id": 1},
            ],
            "itineraries": [
                {
                    "id": 3001,
                    "leg_ids": [1001, 1002],
                    "pricing_options": [{"price": {"amount": "450.00", "currency": "EUR"}}],
                },
            ],
        }
        offers = client._parse_offers(data, "AMS", "JFK")
        assert len(offers) == 1
        assert offers[0].departure_date == "2026-08-15"
        assert offers[0].return_date == "2026-08-30"
        assert offers[0].stops == 1

    def test_parse_fallback_to_segment_carrier(self):
        """When leg has no marketing_carrier_ids, fall back to first segment."""
        client = FlightApiClient(api_key="test-key")
        data = {
            "carriers": [{"id": 99, "name": "Some Airline", "iata": "SA"}],
            "legs": [
                {"id": 1001, "departure": "2026-08-15T10:00:00", "stop_count": 0,
                 "segment_ids": [2001]},
            ],
            "segments": [
                {"id": 2001, "marketing_carrier_id": 99},
            ],
            "itineraries": [
                {
                    "id": 3001,
                    "leg_ids": [1001],
                    "pricing_options": [{"price": {"amount": "200.00"}}],
                },
            ],
        }
        offers = client._parse_offers(data, "AMS", "JFK")
        assert len(offers) == 1
        assert offers[0].airline == "Some Airline"


class TestSearchOneway:
    def test_search_oneway_success(self, mock_httpx_get: MagicMock,
                                   flightapi_response_oneway: dict):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = flightapi_response_oneway
        mock_httpx_get.return_value = mock_response

        client = FlightApiClient(api_key="test-key")
        offers = client.search_oneway("AMS", "JFK", "2026-08-15")
        assert len(offers) == 1
        assert offers[0].price_eur == 300.0
        mock_httpx_get.assert_called_once()

    def test_search_oneway_rate_limited_returns_empty(self, mock_httpx_get: MagicMock):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_httpx_get.return_value = mock_response

        client = FlightApiClient(api_key="test-key")
        offers = client.search_oneway("AMS", "JFK", "2026-08-15")
        assert offers == []

    def test_search_oneway_404_returns_empty(self, mock_httpx_get: MagicMock):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_httpx_get.return_value = mock_response

        client = FlightApiClient(api_key="test-key")
        offers = client.search_oneway("AMS", "JFK", "2026-08-15")
        assert offers == []

    def test_search_oneway_500_raises(self, mock_httpx_get: MagicMock):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "server error", request=MagicMock(), response=mock_response,
        )
        mock_httpx_get.return_value = mock_response

        client = FlightApiClient(api_key="test-key")
        with pytest.raises(httpx.HTTPStatusError):
            client.search_oneway("AMS", "JFK", "2026-08-15")


class TestSearchRoundtrip:
    def test_search_roundtrip_success(self, mock_httpx_get: MagicMock,
                                      flightapi_response_oneway: dict):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = flightapi_response_oneway
        mock_httpx_get.return_value = mock_response

        client = FlightApiClient(api_key="test-key")
        offers = client.search_roundtrip("AMS", "JFK", "2026-08-15", "2026-08-30")
        assert len(offers) == 1
        mock_httpx_get.assert_called_once()

    def test_search_roundtrip_rate_limited_returns_empty(self, mock_httpx_get: MagicMock):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_httpx_get.return_value = mock_response

        client = FlightApiClient(api_key="test-key")
        offers = client.search_roundtrip("AMS", "JFK", "2026-08-15", "2026-08-30")
        assert offers == []

    def test_search_roundtrip_404_returns_empty(self, mock_httpx_get: MagicMock):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_httpx_get.return_value = mock_response

        client = FlightApiClient(api_key="test-key")
        offers = client.search_roundtrip("AMS", "JFK", "2026-08-15", "2026-08-30")
        assert offers == []

    def test_search_roundtrip_500_raises(self, mock_httpx_get: MagicMock):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "server error", request=MagicMock(), response=mock_response,
        )
        mock_httpx_get.return_value = mock_response

        client = FlightApiClient(api_key="test-key")
        with pytest.raises(httpx.HTTPStatusError):
            client.search_roundtrip("AMS", "JFK", "2026-08-15", "2026-08-30")


class TestSearchWindow:
    def test_search_window_wide_range_skips_every_third(self, mock_httpx_get: MagicMock):
        """30-day window → step=3 → 10 calls."""
        empty_response = MagicMock()
        empty_response.status_code = 200
        empty_response.json.return_value = {}
        mock_httpx_get.return_value = empty_response

        client = FlightApiClient(api_key="test-key")
        offers = client.search_window("AMS", "JFK", "2026-08-01", "2026-08-30")
        assert offers == []
        assert mock_httpx_get.call_count == 10

    def test_search_window_narrow_daily(self, mock_httpx_get: MagicMock):
        """7-day window → step=1 → 7 calls."""
        empty_response = MagicMock()
        empty_response.status_code = 200
        empty_response.json.return_value = {}
        mock_httpx_get.return_value = empty_response

        client = FlightApiClient(api_key="test-key")
        offers = client.search_window("AMS", "JFK", "2026-08-01", "2026-08-07")
        assert offers == []
        assert mock_httpx_get.call_count == 7

    def test_search_window_max_price_filter(self, mock_httpx_get: MagicMock,
                                            flightapi_response_oneway: dict):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = flightapi_response_oneway
        mock_httpx_get.return_value = mock_response

        client = FlightApiClient(api_key="test-key")
        offers = client.search_window("AMS", "JFK", "2026-08-15", "2026-08-16",
                                      max_price=200)
        # offer is 300 > max_price 200, so filtered out
        assert offers == []

    def test_search_window_handles_httperror(self, mock_httpx_get: MagicMock):
        """Individual day failures should not crash the whole window."""
        mock_httpx_get.side_effect = httpx.ConnectError("connection failed")

        client = FlightApiClient(api_key="test-key")
        offers = client.search_window("AMS", "JFK", "2026-08-01", "2026-08-03")
        assert offers == []

    def test_search_window_appends_offers_passing_max_price(
        self, mock_httpx_get: MagicMock, flightapi_response_oneway: dict
    ):
        """Offers that pass max_price filter should be appended to results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = flightapi_response_oneway
        mock_httpx_get.return_value = mock_response

        client = FlightApiClient(api_key="test-key")
        offers = client.search_window("AMS", "JFK", "2026-08-15", "2026-08-15",
                                       max_price=500)
        assert len(offers) == 1
        assert offers[0].price_eur == 300.0
