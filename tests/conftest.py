"""Shared fixtures for flight-deal-finder tests."""

from __future__ import annotations

import sqlite3
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from flight_deal_finder.alerts.channels import Deal
from flight_deal_finder.api.flightapi import FlightOffer


@pytest.fixture
def sample_offer() -> FlightOffer:
    return FlightOffer(
        origin="AMS",
        destination="JFK",
        price_eur=300.0,
        departure_date="2026-08-15",
        return_date="2026-08-30",
        airline="KLM",
        stops=0,
        search_link="https://www.google.com/travel/flights?q=Flights+to+JFK+from+AMS+on+2026-08-15",
    )


@pytest.fixture
def sample_deal(sample_offer: FlightOffer) -> Deal:
    return Deal(
        origin=sample_offer.origin,
        destination=sample_offer.destination,
        price_eur=sample_offer.price_eur,
        departure_date=sample_offer.departure_date,
        return_date=sample_offer.return_date or "",
        airline=sample_offer.airline,
        stops=sample_offer.stops,
        median_price=400.0,
        discount_pct=25.0,
        search_link=sample_offer.search_link,
        route_name="Amsterdam → New York",
    )


@pytest.fixture
def connecting_offer(sample_offer: FlightOffer) -> FlightOffer:
    return FlightOffer(
        origin=sample_offer.origin,
        destination=sample_offer.destination,
        price_eur=sample_offer.price_eur - 50,
        departure_date=sample_offer.departure_date,
        return_date=sample_offer.return_date,
        airline="Lufthansa",
        stops=2,
        search_link=sample_offer.search_link,
    )


@pytest.fixture
def tmp_db(monkeypatch: pytest.MonkeyPatch) -> Generator[sqlite3.Connection, None, None]:
    """Monkeypatch DB_PATH to a temp file. Yields connection for direct queries."""
    import flight_deal_finder.db as db_mod

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_path = f.name

    monkeypatch.setattr(db_mod, "DB_PATH", Path(tmp_path))

    conn = db_mod._get_conn()
    yield conn
    conn.close()
    Path(tmp_path).unlink(missing_ok=True)


@pytest.fixture
def tmp_watchlist(tmp_path: Path) -> Path:
    """Create a minimal valid watchlist YAML file for config tests."""
    data = {
        "routes": [
            {
                "name": "Amsterdam → New York",
                "origin": "AMS",
                "destination": "JFK",
                "max_price": 350,
                "date_window": ["2026-08-01", "2026-08-31"],
                "min_stay": 5,
                "max_stay": 10,
                "enabled": True,
            },
            {
                "name": "Amsterdam → Sofia (direct only)",
                "origin": "AMS",
                "destination": "SOF",
                "max_price": 200,
                "date_window": ["2026-07-15", "2026-09-30"],
                "min_stay": 4,
                "max_stay": 14,
                "direct_only": True,
                "enabled": True,
            },
        ],
        "alerts": {
            "deal_threshold_pct": 25,
            "cooldown_hours": 168,
            "channels": ["console"],
        },
        "providers": ["flightapi"],
    }
    yaml_file = tmp_path / "watchlist.yaml"
    yaml_file.write_text(yaml.dump(data))
    return yaml_file


@pytest.fixture
def mock_httpx_get(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Monkeypatch httpx.Client.get to return a mock response."""
    mock = MagicMock()
    monkeypatch.setattr("flight_deal_finder.api.flightapi.httpx.Client.get", mock)
    return mock


@pytest.fixture
def mock_httpx_post(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Monkeypatch httpx.post to return a mock response."""
    mock = MagicMock()
    monkeypatch.setattr("httpx.post", mock)
    return mock


@pytest.fixture
def flightapi_response_oneway() -> dict:
    """Minimal FlightAPI oneway response with one direct KLM flight."""
    return {
        "carriers": [
            {"id": 1, "name": "KLM Royal Dutch Airlines", "iata": "KL"},
        ],
        "legs": [
            {
                "id": 1001,
                "departure": "2026-08-15T10:00:00",
                "arrival": "2026-08-15T13:00:00",
                "stop_count": 0,
                "marketing_carrier_ids": [1],
                "segment_ids": [2001],
            },
        ],
        "segments": [
            {
                "id": 2001,
                "marketing_carrier_id": 1,
                "operating_carrier_id": 1,
            },
        ],
        "itineraries": [
            {
                "id": 3001,
                "leg_ids": [1001],
                "pricing_options": [
                    {
                        "price": {"amount": "300.00", "currency": "EUR"},
                    },
                ],
            },
        ],
    }


@pytest.fixture
def flightapi_response_unpriced() -> dict:
    """Response with an unpriced entry that should be skipped."""
    return {
        "carriers": [{"id": 1, "name": "KLM", "iata": "KL"}],
        "legs": [{"id": 1001, "departure": "2026-08-15T10:00:00", "stop_count": 0,
                  "marketing_carrier_ids": [1]}],
        "segments": [{"id": 2001, "marketing_carrier_id": 1}],
        "itineraries": [
            {
                "id": 3001,
                "leg_ids": [1001],
                "pricing_options": [
                    {"unpriced_type": "itinerary_not_returned"},
                ],
            },
        ],
    }
