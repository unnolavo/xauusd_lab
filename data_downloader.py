"""
Download XAU/USD 1-minute BID candle data from Dukascopy.

Usage:
    python data_downloader.py 2024-01-02
    python data_downloader.py 2024-01-02 2024-01-31

Each CSV file is saved into the data_raw folder as:
    XAUUSD_2024-01-02_1min_BID_UTC.csv
"""

from __future__ import annotations

import csv
import lzma
import struct
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# Project settings for Version 0.3.
SYMBOL = "XAUUSD"
PRICE_SIDE = "BID"
TIMEFRAME = "min_1"
BASE_URL = "https://datafeed.dukascopy.com/datafeed"

# If Dukascopy is temporarily unavailable, try the same day again before
# giving up. This helps with temporary HTTP 503 errors.
MAX_RETRY_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 5

# Dukascopy stores XAU/USD prices as integers. Dividing by 1000 gives
# normal prices like 2063.625.
PRICE_SCALE = 1000

# One Dukascopy 1-minute candle record is 24 bytes:
# seconds_from_midnight, open, close, low, high, volume.
CANDLE_RECORD_SIZE = 24
CANDLE_RECORD = struct.Struct(">5if")

# Save raw downloaded files next to this script, inside data_raw.
PROJECT_DIR = Path(__file__).resolve().parent
DATA_RAW_DIR = PROJECT_DIR / "data_raw"
LOGS_DIR = PROJECT_DIR / "logs"
FAILED_DOWNLOADS_PATH = LOGS_DIR / "failed_downloads.txt"


def parse_day(day_text: str) -> date:
    """Convert text like '2024-01-02' into a Python date."""
    try:
        return datetime.strptime(day_text, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError("Please enter the date in YYYY-MM-DD format.") from error


def parse_date_arguments(arguments: list[str]) -> tuple[date, date]:
    """Read either one date or a start/end date from the command line."""
    if len(arguments) not in (1, 2):
        raise ValueError("Please enter either one date or a start and end date.")

    start_day = parse_day(arguments[0])

    if len(arguments) == 1:
        end_day = start_day
    else:
        end_day = parse_day(arguments[1])

    if end_day < start_day:
        raise ValueError("The end date must be the same as or after the start date.")

    return start_day, end_day


def each_day(start_day: date, end_day: date):
    """Yield every date from start_day to end_day, including both dates."""
    current_day = start_day

    while current_day <= end_day:
        yield current_day
        current_day += timedelta(days=1)


def build_dukascopy_url(day: date) -> str:
    """Build the Dukascopy URL for one day of 1-minute BID candle data."""
    # Dukascopy uses zero-based months in the URL:
    # January is 00, February is 01, and so on.
    dukascopy_month = day.month - 1

    return (
        f"{BASE_URL}/{SYMBOL}/"
        f"{day.year:04d}/{dukascopy_month:02d}/{day.day:02d}/"
        f"{PRICE_SIDE}_candles_{TIMEFRAME}.bi5"
    )


def build_output_path(day: date) -> Path:
    """Choose the local filename for the downloaded CSV."""
    filename = f"{SYMBOL}_{day:%Y-%m-%d}_1min_{PRICE_SIDE}_UTC.csv"
    return DATA_RAW_DIR / filename


def download_bi5(url: str) -> bytes:
    """Download Dukascopy's compressed .bi5 file and return its bytes."""
    # A user agent helps identify this small research project to the server.
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (XAUUSD-Lab/0.3)"})

    with urlopen(request, timeout=30) as response:
        bi5_data = response.read()

    if not bi5_data:
        raise RuntimeError("Dukascopy returned an empty file.")

    return bi5_data


def price_from_dukascopy(value: int) -> str:
    """Convert a Dukascopy integer price into readable XAU/USD text."""
    return f"{value / PRICE_SCALE:.3f}"


def convert_bi5_to_rows(day: date, bi5_data: bytes) -> list[list[str]]:
    """Convert Dukascopy's compressed candle data into CSV rows."""
    try:
        candle_data = lzma.decompress(bi5_data)
    except lzma.LZMAError as error:
        raise RuntimeError("Dukascopy returned data that could not be decompressed.") from error

    if len(candle_data) % CANDLE_RECORD_SIZE != 0:
        raise RuntimeError("Dukascopy returned candle data in an unexpected format.")

    start_of_day = datetime.combine(day, time.min, tzinfo=timezone.utc)
    rows = []

    for position in range(0, len(candle_data), CANDLE_RECORD_SIZE):
        record = candle_data[position : position + CANDLE_RECORD_SIZE]
        seconds, open_price, close_price, low_price, high_price, volume = (
            CANDLE_RECORD.unpack(record)
        )

        timestamp = start_of_day + timedelta(seconds=seconds)

        rows.append(
            [
                timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                price_from_dukascopy(open_price),
                price_from_dukascopy(high_price),
                price_from_dukascopy(low_price),
                price_from_dukascopy(close_price),
                f"{volume:.8f}",
            ]
        )

    if not rows:
        raise RuntimeError("Dukascopy returned no candle rows for this day.")

    return rows


def save_rows_as_csv(rows: list[list[str]], output_path: Path) -> None:
    """Save candle rows as a CSV file."""
    headers = ["timestamp_utc", "open", "high", "low", "close", "volume"]

    # Write to a temporary file first. If something goes wrong, we avoid
    # leaving a half-written CSV behind.
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")

    with temporary_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)
        writer.writerows(rows)

    temporary_path.replace(output_path)


def log_failed_download(day: date, error_message: str) -> None:
    """Save a failed date and its error message to the log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"{timestamp} | {day:%Y-%m-%d} | {error_message}\n"

    with FAILED_DOWNLOADS_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(log_line)


def explain_download_error(error: Exception) -> str:
    """Turn a Python exception into a clear message for the user and log."""
    if isinstance(error, HTTPError):
        return f"Dukascopy returned HTTP {error.code}"

    if isinstance(error, URLError):
        return f"Network error: {error.reason}"

    if isinstance(error, TimeoutError):
        return "Network error: the download timed out"

    if isinstance(error, OSError):
        return f"File error: {error}"

    return str(error)


def download_one_day(day: date) -> bool:
    """Download one day. Return True if it saved or skipped successfully."""
    output_path = build_output_path(day)

    if output_path.exists():
        print(f"Skipped {day:%Y-%m-%d}: file already exists.")
        print(output_path)
        return True

    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        try:
            url = build_dukascopy_url(day)
            bi5_data = download_bi5(url)
            rows = convert_bi5_to_rows(day, bi5_data)
            save_rows_as_csv(rows, output_path)

            print(f"Saved {day:%Y-%m-%d}: {len(rows)} rows.")
            print(output_path)
            return True

        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError) as error:
            error_message = explain_download_error(error)
            print(
                f"Attempt {attempt}/{MAX_RETRY_ATTEMPTS} failed for "
                f"{day:%Y-%m-%d}: {error_message}"
            )

            # Only wait if there is another retry left.
            if attempt < MAX_RETRY_ATTEMPTS:
                print(f"Waiting {RETRY_WAIT_SECONDS} seconds before retrying...")
                sleep(RETRY_WAIT_SECONDS)
            else:
                print(f"Failed {day:%Y-%m-%d} after {MAX_RETRY_ATTEMPTS} attempts.")
                log_failed_download(day, error_message)
                return False

    return False


def print_usage() -> None:
    """Print command examples for the downloader."""
    print("Usage:")
    print("  python data_downloader.py YYYY-MM-DD")
    print("  python data_downloader.py YYYY-MM-DD YYYY-MM-DD")
    print()
    print("Examples:")
    print("  python data_downloader.py 2024-01-02")
    print("  python data_downloader.py 2024-01-02 2024-01-31")


def main() -> int:
    """Run the downloader from the command line."""
    try:
        start_day, end_day = parse_date_arguments(sys.argv[1:])
    except ValueError as error:
        print(f"Date error: {error}")
        print()
        print_usage()
        return 1

    DATA_RAW_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    FAILED_DOWNLOADS_PATH.touch(exist_ok=True)

    days_to_download = list(each_day(start_day, end_day))
    total_days = len(days_to_download)
    successful_days = 0
    failed_days = 0

    print("XAUUSD Lab - Dukascopy downloader")
    print(f"Instrument: {SYMBOL}")
    print("Timeframe: 1-minute candles")
    print(f"Price side: {PRICE_SIDE}")
    print("Timezone: UTC")
    print(f"Start date: {start_day:%Y-%m-%d}")
    print(f"End date: {end_day:%Y-%m-%d}")
    print(f"Days to process: {total_days}")
    print()

    for index, current_day in enumerate(days_to_download, start=1):
        print(f"Downloading {current_day:%Y-%m-%d} ({index}/{total_days})")

        if download_one_day(current_day):
            successful_days += 1
        else:
            failed_days += 1

        print()

    print("Download run complete.")
    print(f"Successful or skipped days: {successful_days}")
    print(f"Failed days: {failed_days}")

    if failed_days:
        print(f"Failed downloads were logged to: {FAILED_DOWNLOADS_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
