"""
Create a multi-day XAU/USD session research report.

Usage:
    python session_report.py 2024-01-01 2024-01-31
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from candle_filters import is_flat_zero_volume_candle, remove_edge_inactive_placeholders
from session_tools import (
    CandleData,
    SessionStatistics,
    calculate_session_statistics,
    get_session_windows,
)


SYMBOL = "XAUUSD"
TIMEFRAME_LABEL = "1min"
PRICE_SIDE = "BID"

PROJECT_DIR = Path(__file__).resolve().parent
DATA_RAW_DIR = PROJECT_DIR / "data_raw"
REPORTS_DIR = PROJECT_DIR / "reports"

BASE_COLUMNS = [
    "date",
    "weekday",
    "status",
    "daily_open",
    "daily_high",
    "daily_low",
    "daily_close",
    "daily_range",
    "time_of_daily_high_utc",
    "time_of_daily_low_utc",
    "total_csv_rows",
    "active_candle_count",
    "inactive_placeholder_count",
]

SESSION_STAT_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "range",
    "time_of_high_utc",
    "time_of_low_utc",
    "active_candle_count",
]


@dataclass
class DailyReportResult:
    """One processed calendar date and whether it completed."""

    row: dict[str, str]
    completed: bool
    missing_file: bool
    failed: bool


@dataclass
class ReportSummary:
    """Counts printed after a report run finishes."""

    requested_dates: int
    completed_dates: int
    missing_files: int
    no_active_candle_dates: int
    failed_dates: int
    output_path: Path


def parse_day(day_text: str) -> date:
    """Convert text like '2024-01-26' into a Python date."""
    try:
        return datetime.strptime(day_text, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("Please enter dates in YYYY-MM-DD format.") from error


def parse_date_range(arguments: list[str]) -> tuple[date, date]:
    """Read the inclusive report start and end dates from the command line."""
    if len(arguments) != 2:
        raise ValueError("Please enter a start date and end date.")

    start_day = parse_day(arguments[0])
    end_day = parse_day(arguments[1])

    if end_day < start_day:
        raise ValueError("The end date cannot be earlier than the start date.")

    return start_day, end_day


def each_day(start_day: date, end_day: date):
    """Yield every date from start_day to end_day, including both dates."""
    current_day = start_day

    while current_day <= end_day:
        yield current_day
        current_day += timedelta(days=1)


def build_csv_path(day: date) -> Path:
    """Build the expected raw CSV path for one downloaded day."""
    filename = f"{SYMBOL}_{day:%Y-%m-%d}_{TIMEFRAME_LABEL}_{PRICE_SIDE}_UTC.csv"
    return DATA_RAW_DIR / filename


def build_report_path(start_day: date, end_day: date) -> Path:
    """Build the output report path for the requested date range."""
    filename = f"session_report_{start_day:%Y-%m-%d}_to_{end_day:%Y-%m-%d}.csv"
    return REPORTS_DIR / filename


def session_prefix(session_name: str) -> str:
    """Convert a session name into a safe lowercase column prefix."""
    return session_name.lower().replace(" ", "_")


def build_report_columns(sample_day: date) -> list[str]:
    """Build the stable report column order from sessions.json."""
    columns = list(BASE_COLUMNS)

    for session_window in get_session_windows(sample_day):
        prefix = session_prefix(session_window.name)

        for column in SESSION_STAT_COLUMNS:
            columns.append(f"{prefix}_{column}")

    return columns


def empty_report_row(day: date, columns: list[str], status: str) -> dict[str, str]:
    """Create a blank report row with date, weekday, and status filled in."""
    row = {column: "" for column in columns}
    row["date"] = f"{day:%Y-%m-%d}"
    row["weekday"] = day.strftime("%A")
    row["status"] = status
    return row


def load_raw_rows(csv_path: Path) -> list[dict[str, str]]:
    """Load raw CSV rows without modifying the downloaded file."""
    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader)


def is_inactive_placeholder_row(row: dict[str, str]) -> bool:
    """Return True if one raw CSV row is a flat, zero-volume placeholder."""
    return is_flat_zero_volume_candle(
        float(row["open"]),
        float(row["high"]),
        float(row["low"]),
        float(row["close"]),
        float(row["volume"]),
    )


def row_to_candle_data(row: dict[str, str]) -> CandleData:
    """Convert one raw CSV row into the shared session candle shape."""
    return CandleData(
        timestamp=datetime.strptime(row["timestamp_utc"], "%Y-%m-%d %H:%M:%S"),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        volume=float(row["volume"]),
    )


def format_price(value: float | None) -> str:
    """Format a price for the report CSV, leaving missing values blank."""
    if value is None:
        return ""

    return f"{value:.3f}"


def format_time(value: datetime | None) -> str:
    """Format a UTC time for the report CSV, leaving missing values blank."""
    if value is None:
        return ""

    return value.strftime("%H:%M:%S")


def add_daily_statistics(row: dict[str, str], active_candles: list[CandleData]) -> None:
    """Add daily OHLC and range values based on active candles only."""
    first_candle = active_candles[0]
    last_candle = active_candles[-1]
    high_candle = max(active_candles, key=lambda candle: candle.high)
    low_candle = min(active_candles, key=lambda candle: candle.low)

    row["daily_open"] = format_price(first_candle.open)
    row["daily_high"] = format_price(high_candle.high)
    row["daily_low"] = format_price(low_candle.low)
    row["daily_close"] = format_price(last_candle.close)
    row["daily_range"] = format_price(high_candle.high - low_candle.low)
    row["time_of_daily_high_utc"] = format_time(high_candle.timestamp)
    row["time_of_daily_low_utc"] = format_time(low_candle.timestamp)


def add_session_statistics(
    row: dict[str, str],
    session_statistics: SessionStatistics,
) -> None:
    """Add one session's statistics to a report row."""
    prefix = session_prefix(session_statistics.session_name)

    row[f"{prefix}_open"] = format_price(session_statistics.open)
    row[f"{prefix}_high"] = format_price(session_statistics.high)
    row[f"{prefix}_low"] = format_price(session_statistics.low)
    row[f"{prefix}_close"] = format_price(session_statistics.close)
    row[f"{prefix}_range"] = format_price(session_statistics.range_dollars)
    row[f"{prefix}_time_of_high_utc"] = format_time(
        session_statistics.time_of_high_utc
    )
    row[f"{prefix}_time_of_low_utc"] = format_time(
        session_statistics.time_of_low_utc
    )
    row[f"{prefix}_active_candle_count"] = str(
        session_statistics.active_candle_count
    )


def process_one_day(day: date, columns: list[str]) -> DailyReportResult:
    """Process one calendar date into one report CSV row."""
    csv_path = build_csv_path(day)

    if not csv_path.exists():
        return DailyReportResult(
            row=empty_report_row(day, columns, "missing_file"),
            completed=False,
            missing_file=True,
            failed=False,
        )

    try:
        raw_rows = load_raw_rows(csv_path)
        active_result = remove_edge_inactive_placeholders(
            raw_rows,
            is_inactive_placeholder_row,
        )
        active_candles = [
            row_to_candle_data(row)
            for row in active_result.active_rows
        ]

        status = "complete" if active_candles else "no_active_candles"
        row = empty_report_row(day, columns, status)
        row["total_csv_rows"] = str(len(raw_rows))
        row["active_candle_count"] = str(len(active_candles))
        row["inactive_placeholder_count"] = str(active_result.inactive_count)

        if not active_candles:
            return DailyReportResult(
                row=row,
                completed=False,
                missing_file=False,
                failed=False,
            )

        add_daily_statistics(row, active_candles)

        for session_window in get_session_windows(day):
            session_statistics = calculate_session_statistics(
                active_candles,
                session_window,
            )
            add_session_statistics(row, session_statistics)

        return DailyReportResult(
            row=row,
            completed=True,
            missing_file=False,
            failed=False,
        )

    except (ValueError, KeyError, OSError) as error:
        print(f"Failed {day:%Y-%m-%d}: {error}")
        return DailyReportResult(
            row=empty_report_row(day, columns, "failed"),
            completed=False,
            missing_file=False,
            failed=True,
        )


def write_report(rows: list[dict[str, str]], columns: list[str], output_path: Path) -> None:
    """Write the report rows to a CSV file."""
    REPORTS_DIR.mkdir(exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as report_file:
        writer = csv.DictWriter(report_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def create_session_report(start_day: date, end_day: date) -> ReportSummary:
    """Create the full session report for an inclusive date range."""
    days = list(each_day(start_day, end_day))
    columns = build_report_columns(start_day)
    rows = []
    completed_dates = 0
    missing_files = 0
    no_active_candle_dates = 0
    failed_dates = 0

    for day in days:
        result = process_one_day(day, columns)
        rows.append(result.row)

        if result.completed:
            completed_dates += 1

        if result.missing_file:
            missing_files += 1

        if result.row["status"] == "no_active_candles":
            no_active_candle_dates += 1

        if result.failed:
            failed_dates += 1

    output_path = build_report_path(start_day, end_day)
    write_report(rows, columns, output_path)

    return ReportSummary(
        requested_dates=len(days),
        completed_dates=completed_dates,
        missing_files=missing_files,
        no_active_candle_dates=no_active_candle_dates,
        failed_dates=failed_dates,
        output_path=output_path,
    )


def print_summary(summary: ReportSummary) -> None:
    """Print a concise completion summary."""
    print("Session report complete.")
    print(f"Requested dates: {summary.requested_dates}")
    print(f"Completed dates: {summary.completed_dates}")
    print(f"Missing files: {summary.missing_files}")
    print(f"No active candle dates: {summary.no_active_candle_dates}")
    print(f"Failed dates: {summary.failed_dates}")
    print(f"Output path: {summary.output_path}")


def print_usage() -> None:
    """Print the correct command format."""
    print("Usage: python session_report.py YYYY-MM-DD YYYY-MM-DD")
    print("Example: python session_report.py 2024-01-01 2024-01-31")


def main() -> int:
    """Run the session report tool from the command line."""
    try:
        start_day, end_day = parse_date_range(sys.argv[1:])
    except ValueError as error:
        print(f"Input error: {error}")
        print()
        print_usage()
        return 1

    summary = create_session_report(start_day, end_day)
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
