"""SQLite price history store."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "prices.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            price_eur REAL NOT NULL,
            departure_date TEXT NOT NULL,
            return_date TEXT,
            airline TEXT,
            url TEXT,
            source TEXT NOT NULL,
            scraped_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts_sent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_key TEXT NOT NULL,
            price_eur REAL NOT NULL,
            sent_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    return conn


def insert_price(
    origin: str,
    destination: str,
    price_eur: float,
    departure_date: str,
    return_date: str | None = None,
    airline: str | None = None,
    url: str | None = None,
    source: str = "flightapi",
) -> None:
    conn = _get_conn()
    conn.execute(
        """INSERT INTO prices (origin, destination, price_eur, departure_date,
           return_date, airline, url, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (origin, destination, price_eur, departure_date, return_date, airline, url, source),
    )
    conn.commit()
    conn.close()


def get_median_price(origin: str, destination: str, days: int = 90) -> float | None:
    """Get median price for route over the last N days."""
    conn = _get_conn()
    row = conn.execute(
        """SELECT price_eur FROM prices
           WHERE origin = ? AND destination = ?
             AND scraped_at >= datetime('now', ?)
           ORDER BY price_eur""",
        (origin, destination, f"-{days} days"),
    ).fetchall()
    conn.close()
    if not row:
        return None
    prices = [r[0] for r in row]
    n = len(prices)
    if n % 2 == 1:
        return prices[n // 2]
    return (prices[n // 2 - 1] + prices[n // 2]) / 2


def was_alerted_recently(route_key: str, cooldown_hours: int) -> bool:
    """Check if we alerted for this route within the cooldown window."""
    conn = _get_conn()
    row = conn.execute(
        """SELECT 1 FROM alerts_sent
           WHERE route_key = ?
             AND sent_at >= datetime('now', ?)""",
        (route_key, f"-{cooldown_hours} hours"),
    ).fetchone()
    conn.close()
    return row is not None


def record_alert(route_key: str, price_eur: float) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT INTO alerts_sent (route_key, price_eur) VALUES (?, ?)",
        (route_key, price_eur),
    )
    conn.commit()
    conn.close()


def get_history(limit: int = 20) -> list[tuple]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT origin, destination, price_eur, departure_date, scraped_at, source "
        "FROM prices ORDER BY scraped_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return rows
