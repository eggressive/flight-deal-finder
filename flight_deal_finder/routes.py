"""Route model and validation for watchlist entries."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Route:
    """A validated watchlist route entry."""

    name: str
    origin: str
    destination: str
    max_price: float
    date_from: str
    date_to: str
    min_stay: int = 7
    max_stay: int = 14
    enabled: bool = True
    check_interval_h: int = 24
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def date_window(self) -> tuple[str, str]:
        return (self.date_from, self.date_to)


_REQUIRED_FIELDS = ("name", "origin", "destination", "max_price", "date_window")


def validate_route(raw: dict[str, Any], index: int = 0) -> Route | None:
    """Validate a raw watchlist route dict. Returns Route on success, None on failure.

    Logs a warning for each validation failure and skips the route entirely.
    """
    errors: list[str] = []

    # Check required fields exist
    for req_field in _REQUIRED_FIELDS:
        if req_field not in raw:
            errors.append(f"missing required field '{req_field}'")

    # date_window shape
    date_window = raw.get("date_window")
    if date_window is not None:
        if not isinstance(date_window, list) or len(date_window) != 2:
            errors.append(
                f"'date_window' must be two date strings, "
                f"got {type(date_window).__name__}"
            )
        elif not all(isinstance(d, str) for d in date_window):
            errors.append("'date_window' must contain string values")

    # max_price type
    max_price = raw.get("max_price")
    if max_price is None:
        errors.append("'max_price' must be numeric, got None")
    else:
        try:
            float(max_price)
        except (TypeError, ValueError):
            errors.append(f"'max_price' must be numeric, got {max_price!r}")

    if errors:
        logger.warning(
            "Route #%d skipped — %s (raw: %s)",
            index,
            "; ".join(errors),
            raw.get("name", "<unnamed>"),
        )
        return None

    # Safe extraction after validation
    date_from, date_to = date_window  # type: ignore[misc]
    return Route(
        name=raw["name"],
        origin=raw["origin"],
        destination=raw["destination"],
        max_price=float(max_price),  # type: ignore[arg-type]
        date_from=date_from,
        date_to=date_to,
        min_stay=int(raw.get("min_stay", 7)),
        max_stay=int(raw.get("max_stay", 14)),
        enabled=bool(raw.get("enabled", True)),
        check_interval_h=int(raw.get("check_interval_h", 24)),
        extra={k: v for k, v in raw.items() if k not in {
            "name", "origin", "destination", "max_price", "date_window",
            "min_stay", "max_stay", "enabled", "check_interval_h",
        }},
    )
