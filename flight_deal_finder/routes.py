"""Route model and validation for watchlist entries."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_REQUIRED_STRINGS = ("name", "origin", "destination")
_OPTIONAL_INTS = ("min_stay", "max_stay", "check_interval_h")


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
    is_roundtrip: bool = False
    return_date_from: str = ""
    return_date_to: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def date_window(self) -> tuple[str, str]:
        return (self.date_from, self.date_to)

    @property
    def return_date_window(self) -> tuple[str, str]:
        return (self.return_date_from, self.return_date_to)


def validate_route(raw: Any, index: int = 0) -> Route | None:
    """Validate a raw watchlist route dict. Returns Route on success, None on failure.

    Logs a warning for each validation failure and skips the route entirely.
    """
    if not isinstance(raw, dict):
        logger.warning(
            "Route #%d skipped — not a mapping (got %s)", index, type(raw).__name__
        )
        return None

    errors: list[str] = []

    # Required string fields — must be present and non-empty strings
    for req_str in _REQUIRED_STRINGS:
        val = raw.get(req_str)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"required field '{req_str}' must be a non-empty string")

    # date_window shape
    date_window = raw.get("date_window")
    if date_window is None:
        errors.append("missing required field 'date_window'")
    elif not isinstance(date_window, list) or len(date_window) != 2:
        errors.append(
            f"'date_window' must be two date strings, "
            f"got {type(date_window).__name__}"
        )
    elif not all(isinstance(d, str) for d in date_window):
        errors.append("'date_window' must contain string values")

    # max_price type
    max_price = raw.get("max_price")
    if max_price is None:
        errors.append("missing required field 'max_price'")
    else:
        try:
            float(max_price)
        except (TypeError, ValueError):
            errors.append(f"'max_price' must be numeric, got {max_price!r}")

    # Optional integer fields — reject non-numeric and explicit None
    for fname in _OPTIONAL_INTS:
        if fname not in raw:
            continue
        val = raw[fname]
        try:
            int(val)
        except (TypeError, ValueError):
            errors.append(f"'{fname}' must be an integer, got {val!r}")

    # enabled must be a real bool (bool("false") is True, so reject str values)
    if "enabled" in raw:
        enabled_val = raw["enabled"]
        if not isinstance(enabled_val, bool):
            errors.append(f"'enabled' must be a boolean, got {enabled_val!r}")

    # is_roundtrip must be a real bool if present
    if "is_roundtrip" in raw:
        rt_val = raw["is_roundtrip"]
        if not isinstance(rt_val, bool):
            errors.append(f"'is_roundtrip' must be a boolean, got {rt_val!r}")

    # return_date_window shape (optional — only used when is_roundtrip is True)
    return_date_window = raw.get("return_date_window")
    if return_date_window is not None:
        if not isinstance(return_date_window, list) or len(return_date_window) != 2:
            errors.append(
                f"'return_date_window' must be two date strings, "
                f"got {type(return_date_window).__name__}"
            )
        elif not all(isinstance(d, str) for d in return_date_window):
            errors.append("'return_date_window' must contain string values")

    if errors:
        logger.warning(
            "Route #%d skipped — %s (name: %s)",
            index,
            "; ".join(errors),
            raw.get("name", "<unnamed>"),
        )
        return None

    # Safe extraction after validation
    date_from, date_to = date_window  # type: ignore[misc]
    return_date_from = ""
    return_date_to = ""
    if return_date_window is not None:
        return_date_from, return_date_to = return_date_window
    return Route(
        name=raw["name"],  # type: ignore[arg-type]
        origin=raw["origin"],  # type: ignore[arg-type]
        destination=raw["destination"],  # type: ignore[arg-type]
        max_price=float(max_price),  # type: ignore[arg-type]
        date_from=date_from,
        date_to=date_to,
        min_stay=int(raw["min_stay"]) if "min_stay" in raw else 7,
        max_stay=int(raw["max_stay"]) if "max_stay" in raw else 14,
        enabled=raw.get("enabled", True),
        check_interval_h=int(raw["check_interval_h"])
        if "check_interval_h" in raw
        else 24,
        is_roundtrip=raw.get("is_roundtrip", False),
        return_date_from=return_date_from,
        return_date_to=return_date_to,
        extra={k: v for k, v in raw.items() if k not in {
            "name", "origin", "destination", "max_price", "date_window",
            "min_stay", "max_stay", "enabled", "check_interval_h",
            "is_roundtrip", "return_date_window",
        }},
    )
