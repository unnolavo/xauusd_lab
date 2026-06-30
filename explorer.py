"""
Explore one downloaded XAU/USD CSV file and print basic daily statistics.

Usage:
    python explorer.py 2024-01-26
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from candle_filters import is_flat_zero_volume_candle, remove_edge_inactive_placeholders
from session_tools import CandleData, calculate_session_statistics, get_session_windows


SYMBOL = "XAUUSD"
TIMEFRAME_LABEL = "1min"
PRICE_SIDE = "BID"

PROJECT_DIR = Path(__file__).resolve().parent
DATA_RAW_DIR = PROJECT_DIR / "data_raw"


@dataclass
class ExplorerArguments:
    """Command-line options for the data explorer."""

    day: date
    show_sessions: bool


def parse_day(day_text: str) -> date:
    """Convert text like '2024-01-26' into a Python date."""
    try:
        return datetime.strptime(day_text, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("Please enter the date in YYYY-MM-DD format.") from error


def parse_arguments(arguments: list[str]) -> ExplorerArguments:
    """Read the date and optional --sessions flag from the command line."""
    if len(arguments) not in (1, 2):
        raise ValueError("Please enter one date, with optional --sessions.")

    flags = arguments[1:]

    if flags and flags[0] != "--sessions":
        raise ValueError("The only optional explorer flag is --sessions.")

    return ExplorerArguments(day=parse_day(arguments[0]), show_sessions="--sessions" in flags)


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


def get_active_rows(candles: list[dict[str, str]]):
    """Remove only leading/trailing inactive placeholder rows."""
    return remove_edge_inactive_placeholders(
        candles,
        is_inactive_placeholder_row,
    )


def row_to_candle_data(candle: dict[str, str]) -> CandleData:
    """Convert one CSV row into the simple candle shape used by sessions."""
    return CandleData(
        timestamp=datetime.strptime(candle["timestamp_utc"], "%Y-%m-%d %H:%M:%S"),
        open=float(candle["open"]),
        high=float(candle["high"]),
        low=float(candle["low"]),
        close=float(candle["close"]),
        volume=float(candle["volume"]),
    )


def time_from_timestamp(timestamp: str) -> str:
    """Get only the HH:MM:SS part from a timestamp."""
    # The downloader writes timestamps like "2024-01-26 13:45:00".
    return timestamp.split(" ")[1]


def calculate_daily_statistics(candles: list[dict[str, str]]) -> dict[str, float | int | str]:
    """Calculate basic daily statistics from the candle rows."""
    if not candles:
        raise ValueError("The CSV file does not contain any candle rows.")

    active_result = get_active_rows(candles)
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


def calculate_session_statistics_for_day(day: date, candles: list[dict[str, str]]):
    """Calculate statistics for each configured research session."""
    active_result = get_active_rows(candles)
    active_candles = [row_to_candle_data(candle) for candle in active_result.active_rows]
    session_windows = get_session_windows(day)

    return [
        calculate_session_statistics(active_candles, session_window)
        for session_window in session_windows
    ]


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


def print_session_statistics(session_statistics) -> None:
    """Print one session's statistics in a clear format."""
    print()
    print(f"{session_statistics.session_name} session")
    print(
        "Local window: "
        f"{session_statistics.local_start:%H:%M}-"
        f"{session_statistics.local_end:%H:%M} "
        f"{session_statistics.timezone_name}"
    )
    print(
        "UTC window: "
        f"{session_statistics.start_utc:%H:%M}-"
        f"{session_statistics.end_utc:%H:%M} UTC"
    )

    if not session_statistics.has_active_candles:
        print("No active candles in this session.")
        return

    print(f"Open: {session_statistics.open:.3f}")
    print(f"High: {session_statistics.high:.3f}")
    print(f"Low: {session_statistics.low:.3f}")
    print(f"Close: {session_statistics.close:.3f}")
    print(f"Range: ${session_statistics.range_dollars:.3f}")
    print(
        "Time of high: "
        f"{session_statistics.time_of_high_utc:%H:%M:%S} UTC / "
        f"{session_statistics.time_of_high_local:%H:%M:%S %Z}"
    )
    print(
        "Time of low: "
        f"{session_statistics.time_of_low_utc:%H:%M:%S} UTC / "
        f"{session_statistics.time_of_low_local:%H:%M:%S %Z}"
    )
    print(f"Active candle count: {session_statistics.active_candle_count}")


def print_all_session_statistics(session_statistics_list) -> None:
    """Print statistics for every configured research session."""
    print()
    print("Session statistics")

    for session_statistics in session_statistics_list:
        print_session_statistics(session_statistics)


def print_usage() -> None:
    """Print the correct command format."""
    print("Usage: python explorer.py YYYY-MM-DD [--sessions]")
    print("Example: python explorer.py 2024-01-26")
    print("Example: python explorer.py 2024-01-26 --sessions")


def main() -> int:
    """Run the explorer from the command line."""
    if len(sys.argv) not in (2, 3):
        print_usage()
        return 1

    try:
        explorer_arguments = parse_arguments(sys.argv[1:])
        requested_day = explorer_arguments.day
        csv_path = build_csv_path(requested_day)

        if not csv_path.exists():
            print(f"No downloaded CSV was found for {requested_day:%Y-%m-%d}.")
            print(f"Expected file: {csv_path}")
            print("Download that day first, then run the explorer again.")
            return 1

        candles = load_candles(csv_path)
        statistics = calculate_daily_statistics(candles)
        print_statistics(requested_day, csv_path, statistics)

        if explorer_arguments.show_sessions:
            session_statistics = calculate_session_statistics_for_day(
                requested_day,
                candles,
            )
            print_all_session_statistics(session_statistics)

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
