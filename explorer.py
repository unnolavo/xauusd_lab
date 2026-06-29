"""
Explore one downloaded XAU/USD CSV file and print basic daily statistics.

Usage:
    python explorer.py 2024-01-26
"""

from __future__ import annotations

import csv
import sys
from datetime import date, datetime
from pathlib import Path

from candle_filters import is_flat_zero_volume_candle, remove_edge_inactive_placeholders


SYMBOL = "XAUUSD"
TIMEFRAME_LABEL = "1min"
PRICE_SIDE = "BID"

PROJECT_DIR = Path(__file__).resolve().parent
DATA_RAW_DIR = PROJECT_DIR / "data_raw"


def parse_day(day_text: str) -> date:
    """Convert text like '2024-01-26' into a Python date."""
    try:
        return datetime.strptime(day_text, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("Please enter the date in YYYY-MM-DD format.") from error


def build_csv_path(day: date) -> Path:
    """Build the expected CSV path for one downloaded day."""
    filename = f"{SYMBOL}_{day:%Y-%m-%d}_{TIMEFRAME_LABEL}_{PRICE_SIDE}_UTC.csv"
    return DATA_RAW_DIR / filename


def load_candles(csv_path: Path) -> list[dict[str, str]]:
    """Load candle rows from a CSV file."""
    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader)


def is_inactive_placeholder_row(candle: dict[str, str]) -> bool:
    """Return True if a CSV row is a flat, zero-volume placeholder row."""
    return is_flat_zero_volume_candle(
        float(candle["open"]),
        float(candle["high"]),
        float(candle["low"]),
        float(candle["close"]),
        float(candle["volume"]),
    )


def time_from_timestamp(timestamp: str) -> str:
    """Get only the HH:MM:SS part from a timestamp."""
    # The downloader writes timestamps like "2024-01-26 13:45:00".
    return timestamp.split(" ")[1]


def calculate_daily_statistics(candles: list[dict[str, str]]) -> dict[str, float | int | str]:
    """Calculate basic daily statistics from the candle rows."""
    if not candles:
        raise ValueError("The CSV file does not contain any candle rows.")

    active_result = remove_edge_inactive_placeholders(
        candles,
        is_inactive_placeholder_row,
    )
    active_candles = active_result.active_rows

    if not active_candles:
        raise ValueError("The CSV file does not contain any active candle rows.")

    first_candle = active_candles[0]
    last_candle = active_candles[-1]

    open_price = float(first_candle["open"])
    close_price = float(last_candle["close"])

    high_price = float(first_candle["high"])
    low_price = float(first_candle["low"])
    time_of_high = time_from_timestamp(first_candle["timestamp_utc"])
    time_of_low = time_from_timestamp(first_candle["timestamp_utc"])

    total_volume = 0.0

    for candle in active_candles:
        candle_high = float(candle["high"])
        candle_low = float(candle["low"])
        candle_volume = float(candle["volume"])

        total_volume += candle_volume

        if candle_high > high_price:
            high_price = candle_high
            time_of_high = time_from_timestamp(candle["timestamp_utc"])

        if candle_low < low_price:
            low_price = candle_low
            time_of_low = time_from_timestamp(candle["timestamp_utc"])

    active_candles_count = len(active_candles)
    average_volume = total_volume / active_candles_count
    daily_range = high_price - low_price

    return {
        "total_csv_rows": len(candles),
        "active_candles": active_candles_count,
        "inactive_placeholder_rows": active_result.inactive_count,
        "open_price": open_price,
        "high_price": high_price,
        "low_price": low_price,
        "close_price": close_price,
        "daily_range": daily_range,
        "time_of_high": time_of_high,
        "time_of_low": time_of_low,
        "average_volume": average_volume,
    }


def print_statistics(day: date, csv_path: Path, statistics: dict[str, float | int | str]) -> None:
    """Print the daily statistics in a clear format."""
    print("XAUUSD Lab - Data Explorer")
    print(f"Date: {day:%Y-%m-%d}")
    print(f"File: {csv_path}")
    print()
    print(f"Open price: {statistics['open_price']:.3f}")
    print(f"High price: {statistics['high_price']:.3f}")
    print(f"Low price: {statistics['low_price']:.3f}")
    print(f"Close price: {statistics['close_price']:.3f}")
    print(f"Daily range: ${statistics['daily_range']:.3f}")
    print(f"Time of high: {statistics['time_of_high']} UTC")
    print(f"Time of low: {statistics['time_of_low']} UTC")
    print(f"Total CSV rows: {statistics['total_csv_rows']}")
    print(f"Active candles: {statistics['active_candles']}")
    print(
        "Inactive market-closed placeholder rows: "
        f"{statistics['inactive_placeholder_rows']}"
    )
    print(f"Average volume (active candles): {statistics['average_volume']:.8f}")


def print_usage() -> None:
    """Print the correct command format."""
    print("Usage: python explorer.py YYYY-MM-DD")
    print("Example: python explorer.py 2024-01-26")


def main() -> int:
    """Run the explorer from the command line."""
    if len(sys.argv) != 2:
        print_usage()
        return 1

    try:
        requested_day = parse_day(sys.argv[1])
        csv_path = build_csv_path(requested_day)

        if not csv_path.exists():
            print(f"No downloaded CSV was found for {requested_day:%Y-%m-%d}.")
            print(f"Expected file: {csv_path}")
            print("Download that day first, then run the explorer again.")
            return 1

        candles = load_candles(csv_path)
        statistics = calculate_daily_statistics(candles)
        print_statistics(requested_day, csv_path, statistics)
        return 0

    except ValueError as error:
        print(f"Input error: {error}")
        return 1
    except KeyError as error:
        print(f"CSV error: missing expected column {error}.")
        return 1
    except OSError as error:
        print(f"File error: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
