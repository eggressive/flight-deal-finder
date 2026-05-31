"""Tests for route validation."""

import logging

from flight_deal_finder.routes import Route, validate_route


class TestValidateRoute:
    """Route validation — required fields, type checks, defaults."""

    _valid = {
        "name": "AMS→HND",
        "origin": "AMS",
        "destination": "HND",
        "max_price": 700,
        "date_window": ["2026-09-01", "2026-09-15"],
    }

    def test_valid_minimal(self) -> None:
        route = validate_route(self._valid)
        assert route is not None
        assert isinstance(route, Route)
        assert route.name == "AMS→HND"
        assert route.origin == "AMS"
        assert route.destination == "HND"
        assert route.max_price == 700.0
        assert route.date_from == "2026-09-01"
        assert route.date_to == "2026-09-15"
        assert route.date_window == ("2026-09-01", "2026-09-15")
        assert route.min_stay == 7
        assert route.max_stay == 14
        assert route.enabled is True
        assert route.extra == {}

    def test_valid_with_optionals(self) -> None:
        raw = {
            **self._valid,
            "min_stay": 4,
            "max_stay": 10,
            "enabled": False,
            "notes": "direct only",
        }
        route = validate_route(raw)
        assert route is not None
        assert route.min_stay == 4
        assert route.max_stay == 10
        assert route.enabled is False
        assert route.extra == {"notes": "direct only"}

    # ── Missing fields ──────────────────────────────────────────

    def test_missing_name(self) -> None:
        raw = {**self._valid, "name": None}
        del raw["name"]
        assert validate_route(raw) is None

    def test_missing_origin(self) -> None:
        raw = {**self._valid, "origin": None}
        del raw["origin"]
        assert validate_route(raw) is None

    def test_missing_destination(self) -> None:
        raw = {**self._valid, "destination": None}
        del raw["destination"]
        assert validate_route(raw) is None

    def test_missing_max_price(self) -> None:
        raw = {**self._valid, "max_price": None}
        del raw["max_price"]
        assert validate_route(raw) is None

    def test_missing_date_window(self) -> None:
        raw = {**self._valid, "date_window": None}
        del raw["date_window"]
        assert validate_route(raw) is None

    def test_multiple_missing(self) -> None:
        raw = {"name": "lone"}
        assert validate_route(raw) is None

    # ── Type / shape errors ─────────────────────────────────────

    def test_date_window_not_list(self) -> None:
        raw = {**self._valid, "date_window": "2026-09-01"}
        assert validate_route(raw) is None

    def test_date_window_one_element(self) -> None:
        raw = {**self._valid, "date_window": ["2026-09-01"]}
        assert validate_route(raw) is None

    def test_date_window_three_elements(self) -> None:
        raw = {**self._valid, "date_window": ["2026-09-01", "2026-09-15", "2026-10-01"]}
        assert validate_route(raw) is None

    def test_date_window_non_strings(self) -> None:
        raw = {**self._valid, "date_window": [20260901, 20260915]}
        assert validate_route(raw) is None

    def test_max_price_not_numeric(self) -> None:
        raw = {**self._valid, "max_price": "expensive"}
        assert validate_route(raw) is None

    def test_max_price_none(self) -> None:
        raw = {**self._valid, "max_price": None}
        assert validate_route(raw) is None

    # ── Optional numeric field validation ────────────────────────

    def test_min_stay_non_numeric(self) -> None:
        raw = {**self._valid, "min_stay": "seven"}
        assert validate_route(raw) is None

    def test_max_stay_non_numeric(self) -> None:
        raw = {**self._valid, "max_stay": "ten"}
        assert validate_route(raw) is None

    def test_optional_numeric_combined(self, caplog) -> None:
        raw = {**self._valid, "min_stay": "bad", "max_stay": [1, 2]}
        result = validate_route(raw, index=1)
        assert result is None
        warnings = [r[2] for r in caplog.record_tuples if r[1] == logging.WARNING]
        assert len(warnings) >= 1
        combined = " ".join(warnings)
        assert "min_stay" in combined
        assert "max_stay" in combined

    # ── Edge cases ──────────────────────────────────────────────

    def test_empty_dict(self) -> None:
        assert validate_route({}) is None

    def test_missing_and_malformed_combined(self, caplog) -> None:
        raw = {"name": "Broken", "date_window": "bad", "max_price": "nope"}
        result = validate_route(raw, index=5)
        assert result is None
        # Warning should mention both issues
        assert caplog.record_tuples
        warnings = [r[2] for r in caplog.record_tuples if r[1] == logging.WARNING]
        assert len(warnings) >= 1
        combined = " ".join(warnings)
        assert "Route #5" in combined
        assert "max_price" in combined
        assert "date_window" in combined

    def test_index_appears_in_warning(self, caplog) -> None:
        raw = {"name": "Missing Fields"}
        validate_route(raw, index=3)
        assert any("Route #3" in r[2] for r in caplog.record_tuples if r[1] == logging.WARNING)

    def test_unnamed_route_warning(self, caplog) -> None:
        validate_route({}, index=0)
        assert any("<unnamed>" in r[2] for r in caplog.record_tuples if r[1] == logging.WARNING)

    # ── Non-mapping guard ───────────────────────────────────────

    def test_non_mapping_string(self, caplog) -> None:
        result = validate_route("not a dict", index=7)
        assert result is None
        assert any("not a mapping" in r[2] for r in caplog.record_tuples if r[1] == logging.WARNING)

    def test_non_mapping_none(self, caplog) -> None:
        result = validate_route(None, index=3)
        assert result is None
        assert any("not a mapping" in r[2] for r in caplog.record_tuples if r[1] == logging.WARNING)

    def test_non_mapping_int(self) -> None:
        result = validate_route(42, index=0)
        assert result is None

    # ── enabled bool guard ──────────────────────────────────────

    def test_enabled_string_false(self) -> None:
        raw = {**self._valid, "enabled": "false"}
        assert validate_route(raw) is None

    def test_enabled_null(self) -> None:
        raw = {**self._valid, "enabled": None}
        assert validate_route(raw) is None

    # ── is_roundtrip bool guard ──────────────────────────────────

    def test_is_roundtrip_string_rejected(self) -> None:
        raw = {**self._valid, "is_roundtrip": "true"}
        assert validate_route(raw) is None

    def test_is_roundtrip_null_rejected(self) -> None:
        raw = {**self._valid, "is_roundtrip": None}
        assert validate_route(raw) is None

    def test_is_roundtrip_default_false(self) -> None:
        route = validate_route(self._valid)
        assert route is not None
        assert route.is_roundtrip is False

    def test_is_roundtrip_true(self) -> None:
        raw = {**self._valid, "is_roundtrip": True}
        route = validate_route(raw)
        assert route is not None
        assert route.is_roundtrip is True

    # ── return_date_window validation ────────────────────────────

    def test_return_date_window_valid(self) -> None:
        raw = {
            **self._valid,
            "is_roundtrip": True,
            "return_date_window": ["2026-09-10", "2026-09-20"],
        }
        route = validate_route(raw)
        assert route is not None
        assert route.return_date_from == "2026-09-10"
        assert route.return_date_to == "2026-09-20"
        assert route.return_date_window == ("2026-09-10", "2026-09-20")

    def test_return_date_window_missing_ok(self) -> None:
        raw = {**self._valid, "is_roundtrip": True}
        route = validate_route(raw)
        assert route is not None
        assert route.return_date_from == ""
        assert route.return_date_to == ""

    def test_return_date_window_not_list(self) -> None:
        raw = {**self._valid, "return_date_window": "2026-09-10"}
        assert validate_route(raw) is None

    def test_return_date_window_one_element(self) -> None:
        raw = {**self._valid, "return_date_window": ["2026-09-10"]}
        assert validate_route(raw) is None

    def test_return_date_window_non_strings(self) -> None:
        raw = {**self._valid, "return_date_window": [20260910, 20260920]}
        assert validate_route(raw) is None
