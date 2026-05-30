"""Tests for flight_deal_finder.db — SQLite price store and alert tracking."""

from __future__ import annotations

import sqlite3


class TestSchemaCreation:
    def test_tables_created_on_first_connect(self, tmp_db: sqlite3.Connection):
        tables = tmp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = {row[0] for row in tables}
        assert "prices" in table_names
        assert "alerts_sent" in table_names

    def test_connect_is_idempotent(self, tmp_db: sqlite3.Connection):
        import flight_deal_finder.db as db_mod
        conn2 = db_mod._get_conn()
        conn2.close()
        tables = tmp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        assert len(tables) == 2


class TestInsertPrice:
    def test_insert_with_all_fields(self, tmp_db: sqlite3.Connection):
        import flight_deal_finder.db as db_mod
        db_mod.insert_price(
            origin="AMS", destination="JFK", price_eur=300.0,
            departure_date="2026-08-15", return_date="2026-08-30",
            airline="KLM", url="https://example.com", source="flightapi",
        )
        row = tmp_db.execute(
            "SELECT origin, destination, price_eur, departure_date, return_date, "
            "airline, url, source FROM prices"
        ).fetchone()
        assert row == ("AMS", "JFK", 300.0, "2026-08-15", "2026-08-30",
                       "KLM", "https://example.com", "flightapi")

    def test_insert_minimal_fields(self, tmp_db: sqlite3.Connection):
        import flight_deal_finder.db as db_mod
        db_mod.insert_price(origin="AMS", destination="JFK", price_eur=200.0,
                            departure_date="2026-08-15", source="flightapi")
        row = tmp_db.execute(
            "SELECT origin, destination, price_eur, return_date, airline FROM prices"
        ).fetchone()
        assert row == ("AMS", "JFK", 200.0, None, None)


class TestGetMedianPrice:
    def test_empty_returns_none(self, tmp_db: sqlite3.Connection):
        import flight_deal_finder.db as db_mod
        assert db_mod.get_median_price("AMS", "JFK") is None

    def test_single_price_returns_itself(self, tmp_db: sqlite3.Connection):
        import flight_deal_finder.db as db_mod
        db_mod.insert_price("AMS", "JFK", 300.0, "2026-08-15", source="flightapi")
        assert db_mod.get_median_price("AMS", "JFK") == 300.0

    def test_odd_count_returns_middle(self, tmp_db: sqlite3.Connection):
        import flight_deal_finder.db as db_mod
        for price in [100.0, 300.0, 200.0]:
            db_mod.insert_price("AMS", "JFK", price, "2026-08-01", source="flightapi")
        assert db_mod.get_median_price("AMS", "JFK") == 200.0

    def test_even_count_returns_average_of_middle_two(self, tmp_db: sqlite3.Connection):
        import flight_deal_finder.db as db_mod
        for price in [100.0, 400.0, 300.0, 200.0]:
            db_mod.insert_price("AMS", "JFK", price, "2026-08-01", source="flightapi")
        assert db_mod.get_median_price("AMS", "JFK") == 250.0

    def test_median_only_considers_requested_route(self, tmp_db: sqlite3.Connection):
        import flight_deal_finder.db as db_mod
        db_mod.insert_price("AMS", "JFK", 300.0, "2026-08-01", source="flightapi")
        db_mod.insert_price("AMS", "SOF", 100.0, "2026-08-01", source="flightapi")
        assert db_mod.get_median_price("AMS", "JFK") == 300.0


class TestAlertsSent:
    def test_was_alerted_recently_false_when_empty(self, tmp_db: sqlite3.Connection):
        import flight_deal_finder.db as db_mod
        assert not db_mod.was_alerted_recently("AMS:JFK:2026-08-15", 168)

    def test_was_alerted_recently_true_within_window(self, tmp_db: sqlite3.Connection):
        import flight_deal_finder.db as db_mod
        db_mod.record_alert("AMS:JFK:2026-08-15", 250.0)
        assert db_mod.was_alerted_recently("AMS:JFK:2026-08-15", 9999)

    def test_record_alert_writes_row(self, tmp_db: sqlite3.Connection):
        import flight_deal_finder.db as db_mod
        db_mod.record_alert("AMS:JFK:2026-08-15", 250.0)
        row = tmp_db.execute(
            "SELECT route_key, price_eur FROM alerts_sent"
        ).fetchone()
        assert row[0] == "AMS:JFK:2026-08-15"
        assert row[1] == 250.0

    def test_was_alerted_allows_zero_cooldown(self, tmp_db: sqlite3.Connection):
        """With cooldown=0 and a record, should still find it (datetime >= now - 0)."""
        import flight_deal_finder.db as db_mod
        db_mod.record_alert("AMS:JFK:2026-08-15", 250.0)
        assert db_mod.was_alerted_recently("AMS:JFK:2026-08-15", 0)


class TestGetHistory:
    def test_empty_history(self, tmp_db):
        import flight_deal_finder.db as db_mod
        rows = db_mod.get_history()
        assert rows == []

    def test_returns_ordered_by_scraped_at_desc(self, tmp_db: sqlite3.Connection):
        import flight_deal_finder.db as db_mod
        db_mod.insert_price("AMS", "JFK", 300.0, "2026-08-15", source="flightapi")
        db_mod.insert_price("AMS", "SOF", 150.0, "2026-08-16", source="flightapi")
        rows = db_mod.get_history()
        assert len(rows) == 2
        assert rows[0][4] >= rows[1][4]  # scraped_at descending

    def test_respects_limit(self, tmp_db: sqlite3.Connection):
        import flight_deal_finder.db as db_mod
        for i in range(5):
            db_mod.insert_price("AMS", "JFK", 100.0 + i, "2026-08-01", source="flightapi")
        rows = db_mod.get_history(limit=3)
        assert len(rows) == 3
