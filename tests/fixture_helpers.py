"""Deterministic synthetic CSV fixtures for tests.

These helpers create production-shaped raw CSV files in temporary directories.
They intentionally do not use or modify the repository's ignored data_raw CSVs.
"""

from __future__ import annotations

import csv
from datetime import date, datetime, time, timedelta
from pathlib import Path


CSV_HEADERS = ["timestamp_utc", "open", "high", "low", "close", "volume"]


def production_csv_filename(day: date) -> str:
    """Return the production raw CSV filename for one XAUUSD BID day."""
    return f"XAUUSD_{day:%Y-%m-%d}_1min_BID_UTC.csv"


def production_csv_path(directory: Path, day: date) -> Path:
    """Return the production raw CSV path inside a chosen directory."""
    return directory / production_csv_filename(day)


def _time_range(day: date, start_time: time, end_time: time):
    """Yield one-minute UTC timestamps from start_time up to end_time."""
    start_timestamp = datetime.combine(day, start_time)
    end_timestamp = datetime.combine(day, end_time)

    if end_timestamp <= start_timestamp:
        end_timestamp += timedelta(days=1)

    current_timestamp = start_timestamp

    while current_timestamp < end_timestamp:
        yield current_timestamp
        current_timestamp += timedelta(minutes=1)


def _format_row(
    timestamp: datetime,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: float,
) -> dict[str, str]:
    """Format one candle row exactly like the downloader's CSV output."""
    return {
        "timestamp_utc": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "open": f"{open_price:.3f}",
        "high": f"{high_price:.3f}",
        "low": f"{low_price:.3f}",
        "close": f"{close_price:.3f}",
        "volume": f"{volume:.8f}",
    }


def make_active_rows(
    day: date,
    start_time: time = time(0, 0),
    end_time: time = time(22, 0),
    base_price: float = 2000.0,
) -> list[dict[str, str]]:
    """Create deterministic active candles for a configurable UTC time range."""
    day_start = datetime.combine(day, time.min)
    rows = []

    for timestamp in _time_range(day, start_time, end_time):
        minute_index = int((timestamp - day_start).total_seconds() // 60)
        open_price = base_price + (minute_index * 0.01)
        close_price = open_price + (0.05 if minute_index % 2 == 0 else -0.03)
        high_price = max(open_price, close_price) + 0.10 + ((minute_index % 5) * 0.01)
        low_price = min(open_price, close_price) - 0.10 - ((minute_index % 7) * 0.01)
        volume = 1.0 + ((minute_index % 11) * 0.25)

        rows.append(
            _format_row(
                timestamp,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
            )
        )

    return rows


def make_placeholder_rows(
    day: date,
    start_time: time,
    end_time: time,
    flat_price: float = 2000.0,
) -> list[dict[str, str]]:
    """Create flat zero-volume placeholder rows for one UTC time range."""
    return [
        _format_row(
            timestamp,
            flat_price,
            flat_price,
            flat_price,
            flat_price,
            0.0,
        )
        for timestamp in _time_range(day, start_time, end_time)
    ]


def make_friday_rows_active_until_22_utc(day: date) -> list[dict[str, str]]:
    """Create a Friday-style day with active rows until 22:00 UTC."""
    active_rows = make_active_rows(day, time(0, 0), time(22, 0))
    trailing_placeholders = make_placeholder_rows(day, time(22, 0), time(0, 0))
    return active_rows + trailing_placeholders


def make_placeholder_only_day(day: date) -> list[dict[str, str]]:
    """Create a full UTC day made only of inactive placeholder rows."""
    return make_placeholder_rows(day, time(0, 0), time(0, 0))


def write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    """Write production-shaped rows to a CSV path."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    return path


def write_daily_csv(
    directory: Path,
    day: date,
    rows: list[dict[str, str]],
) -> Path:
    """Write rows using the production raw CSV filename for the date."""
    return write_csv(production_csv_path(directory, day), rows)


def write_invalid_daily_csv(directory: Path, day: date) -> Path:
    """Write a CSV that deterministically fails the current numeric parser."""
    invalid_row = {
        "timestamp_utc": f"{day:%Y-%m-%d} 00:00:00",
        "open": "not-a-number",
        "high": "2000.000",
        "low": "1999.500",
        "close": "1999.750",
        "volume": "1.00000000",
    }
    return write_daily_csv(directory, day, [invalid_row])
