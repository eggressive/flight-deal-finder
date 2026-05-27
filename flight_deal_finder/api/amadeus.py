"""Amadeus Self-Service Flight Offers Search API client.

Ref: https://developers.amadeus.com/self-service
⚠️  Shutting down July 17, 2026 — migrate to Duffel or Google Flights scraper after.
"""

from __future__ import annotations

import dataclasses
import logging

import httpx

logger = logging.getLogger(__name__)

TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"


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


class AmadeusClient:
    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self._token: str | None = None
        self._client = httpx.Client(timeout=30)

    def _authenticate(self) -> str:
        if self._token:
            return self._token
        logger.info("Authenticating with Amadeus...")
        resp = self._client.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_secret,
            },
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def search(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str | None = None,
        adults: int = 1,
        max_results: int = 10,
        nonstop: bool = False,
    ) -> list[FlightOffer]:
        """Search flight offers. Returns up to max_results, sorted cheapest first."""
        token = self._authenticate()
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "max": max_results,
            "currencyCode": "EUR",
        }
        if return_date:
            params["returnDate"] = return_date
        if nonstop:
            params["nonStop"] = "true"

        logger.info("Searching %s→%s for %s", origin, destination, departure_date)
        resp = self._client.get(
            SEARCH_URL,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )

        if resp.status_code == 429:
            logger.warning("Amadeus rate-limited. Skipping this check.")
            return []

        resp.raise_for_status()
        data = resp.json()

        offers = []
        for item in data.get("data", []):
            price = float(item["price"]["grandTotal"])
            itinerary = item["itineraries"][0]
            first_segment = itinerary["segments"][0]
            depart = first_segment["departure"]["at"][:10]
            airline = first_segment["carrierCode"]
            stops = len(itinerary["segments"]) - 1

            ret_date = None
            if len(item["itineraries"]) > 1:
                ret_seg = item["itineraries"][1]["segments"]
                ret_date = ret_seg[-1]["arrival"]["at"][:10]

            offers.append(
                FlightOffer(
                    origin=origin,
                    destination=destination,
                    price_eur=price,
                    departure_date=depart,
                    return_date=ret_date,
                    airline=airline,
                    stops=stops,
                    deep_link=item.get("dictionaries", {}).get("deepLink", ""),
                )
            )

        # Already sorted by Amadeus
        return offers[:max_results]

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
        """Search across a date window — checks departure dates within the range.

        For each departure date, fetches one-way results. This is the simplest
        approach that stays within free-tier limits (~2,000 calls/mo).
        """
        from datetime import datetime, timedelta

        d_start = datetime.strptime(date_from, "%Y-%m-%d")
        d_end = datetime.strptime(date_to, "%Y-%m-%d")
        delta = d_end - d_start

        all_offers: list[FlightOffer] = []

        # Sample: check every 3rd day + weekends if window is large
        step = 3 if delta.days > 14 else 1
        current = d_start
        while current <= d_end:
            dep_str = current.strftime("%Y-%m-%d")
            try:
                offers = self.search(origin, destination, dep_str, max_results=5)
                for o in offers:
                    if max_price and o.price_eur > max_price:
                        continue
                    all_offers.append(o)
            except httpx.HTTPError as e:
                logger.error("API error for %s: %s", dep_str, e)
            current += timedelta(days=step)

        # Sort cheapest first
        all_offers.sort(key=lambda o: o.price_eur)
        return all_offers
