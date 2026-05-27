"""FlightAPI.io client — oneway + roundtrip flight price search.

Ref: https://docs.flightapi.io
Auth: API key in URL path (no OAuth). 2 credits per request.
Free tier: 20 calls, then Lite from $49/mo.
"""

from __future__ import annotations

import dataclasses
import logging

import httpx

logger = logging.getLogger(__name__)

ONEWAY_URL = "https://api.flightapi.io/onewaytrip"
ROUNDTRIP_URL = "https://api.flightapi.io/roundtrip"


@dataclasses.dataclass
class FlightOffer:
    origin: str
    destination: str
    price_eur: float
    departure_date: str
    return_date: str | None
    airline: str
    stops: int
    deep_link: str


class FlightApiClient:
    """FlightAPI.io client — simple API-key auth, relational JSON responses."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("FlightAPI.io API key is required. Get one at https://flightapi.io")
        self.api_key = api_key
        self._client = httpx.Client(timeout=30)

    def _build_url(self, base: str, **params: str) -> str:
        """Build URL: base/api_key/param1/param2/..."""
        return f"{base}/{self.api_key}/" + "/".join(params.values())

    # ── response parsing ─────────────────────────────────────────────

    def _parse_offers(
        self,
        data: dict,
        origin: str,
        destination: str,
    ) -> list[FlightOffer]:
        """Parse FlightAPI.io relational JSON response into FlightOffer list."""
        places = {p["id"]: p for p in data.get("places", [])}
        carriers = {c["id"]: c for c in data.get("carriers", [])}
        legs = {l["id"]: l for l in data.get("legs", [])}

        offers: list[FlightOffer] = []
        for itin in data.get("itineraries", []):
            for p_opt in itin.get("pricing_options", []):
                price = float(p_opt["price"]["amount"])

                # Resolve leg → segments → airline + stops
                leg_ids = itin.get("leg_ids", [])
                airline = "unknown"
                stops = 0
                departure_date = ""
                return_date = None

                if leg_ids:
                    outbound = legs.get(leg_ids[0], {})
                    stops = outbound.get("stop_count", 0)
                    departure_date = outbound.get("departure", "")[:10]
                    seg_ids = outbound.get("segment_ids", [])
                    if seg_ids and seg_ids[0] in data.get("segments", {}):
                        carrier_id = data["segments"][seg_ids[0]].get("carrier_id")
                        if carrier_id and carrier_id in carriers:
                            airline = carriers[carrier_id].get("name", "unknown")

                # Roundtrip: second leg for return
                if len(leg_ids) > 1:
                    inbound = legs.get(leg_ids[1], {})
                    return_date = inbound.get("departure", "")[:10]

                offers.append(
                    FlightOffer(
                        origin=origin,
                        destination=destination,
                        price_eur=price,
                        departure_date=departure_date or "",
                        return_date=return_date,
                        airline=airline,
                        stops=stops,
                        deep_link=f"https://www.google.com/travel/flights?q=Flights+to+{destination}+from+{origin}+on+{departure_date}",
                    )
                )
        return offers

    # ── public API ────────────────────────────────────────────────────

    def search_oneway(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        adults: int = 1,
    ) -> list[FlightOffer]:
        """Search one-way flights. 2 credits."""
        url = self._build_url(
            ONEWAY_URL,
            origin=origin,
            destination=destination,
            date=departure_date,
            adults=str(adults),
            children="0",
            infants="0",
            cabin="Economy",
            currency="EUR",
            region="NL",
        )
        logger.info("FlightAPI oneway: %s→%s %s", origin, destination, departure_date)
        resp = self._client.get(url)
        resp.raise_for_status()
        return self._parse_offers(resp.json(), origin, destination)

    def search_roundtrip(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        adults: int = 1,
    ) -> list[FlightOffer]:
        """Search round-trip flights. 2 credits."""
        url = self._build_url(
            ROUNDTRIP_URL,
            origin=origin,
            destination=destination,
            dep_date=departure_date,
            ret_date=return_date,
            adults=str(adults),
            children="0",
            infants="0",
            cabin="Economy",
            currency="EUR",
            region="NL",
        )
        logger.info(
            "FlightAPI roundtrip: %s→%s %s→%s",
            origin, destination, departure_date, return_date,
        )
        resp = self._client.get(url)
        resp.raise_for_status()
        return self._parse_offers(resp.json(), origin, destination)

    def search_window(
        self,
        origin: str,
        destination: str,
        date_from: str,
        date_to: str,
        min_stay: int = 7,
        max_stay: int = 14,
        max_price: float | None = None,
    ) -> list[FlightOffer]:
        """Search across a date window.

        Checks every 3rd departure date (or daily for narrow windows).
        Uses oneway search to minimize credits. If return dates matter,
        use search_roundtrip directly.
        """
        from datetime import datetime, timedelta

        d_start = datetime.strptime(date_from, "%Y-%m-%d")
        d_end = datetime.strptime(date_to, "%Y-%m-%d")
        delta = d_end - d_start

        all_offers: list[FlightOffer] = []
        step = 3 if delta.days > 14 else 1
        current = d_start
        while current <= d_end:
            dep_str = current.strftime("%Y-%m-%d")
            try:
                offers = self.search_oneway(origin, destination, dep_str)
                for o in offers:
                    if max_price and o.price_eur > max_price:
                        continue
                    all_offers.append(o)
            except httpx.HTTPError as e:
                logger.error("FlightAPI error for %s: %s", dep_str, e)
            current += timedelta(days=step)

        all_offers.sort(key=lambda o: o.price_eur)
        return all_offers
