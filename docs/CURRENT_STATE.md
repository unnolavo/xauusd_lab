# Current State

Verified milestone: **v0.10.1**.

XAUUSD Lab is a Python research project for studying XAU/USD, meaning gold priced in US dollars. The current repository focuses on downloading Dukascopy one-minute BID data, exploring daily data, charting candles, applying configurable research-session windows, and producing multi-day session research reports.

## Repository Structure

Current tracked source and documentation files:

```text
AGENTS.md
CHANGELOG.md
README.md
candle_filters.py
chart.py
config.json
data_downloader.py
explorer.py
requirements.txt
session_report.py
session_tools.py
sessions.json
tests/
reports/.gitkeep
docs/
```

Local generated or ignored folders may include:

```text
data_raw/
logs/
reports/
__pycache__/
tests/__pycache__/
```

The local `data_raw/` folder may contain ignored downloaded XAUUSD CSV files on a development machine. Those CSV files are not included in a fresh Git clone, and the automated tests do not require them.

## Python Files

`data_downloader.py` downloads Dukascopy XAU/USD one-minute BID `.bi5` files, decompresses them, converts them into CSV rows, saves them in `data_raw/`, skips existing files, retries temporary failures, and logs failed downloads after all retries fail. It supports command-line date arguments and no-argument config-file mode.

`explorer.py` loads one daily CSV from `data_raw/` and prints daily statistics. With `--sessions`, it also prints Tokyo, London, and New York research-session statistics. It uses active candles only, after excluding leading and trailing inactive placeholder rows.

`chart.py` loads one daily CSV from `data_raw/` and displays a candlestick chart. It supports light mode, `--dark`, `--sessions`, hover OHLC labels, crosshair lines, active-time x-axis limits, and candle-based y-axis scaling.

`candle_filters.py` provides shared logic for detecting flat zero-volume placeholder candles and removing only contiguous inactive placeholder rows at the beginning or end of a candle list.

`session_tools.py` loads session definitions from `sessions.json`, converts local session windows to UTC with `zoneinfo`, selects candles using start-inclusive and end-exclusive windows, and calculates session statistics.

`session_report.py` processes an inclusive date range of downloaded daily CSV files and writes one research-ready CSV row per requested date into `reports/`.

## JSON Configuration

`config.json` controls the downloader's no-argument mode:

```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "symbol": "XAUUSD",
  "price_side": "BID",
  "timeframe": "min_1"
}
```

`sessions.json` defines configurable research-session windows. Current defaults are:

- Tokyo: `Asia/Tokyo`, 09:00-18:00 local time
- London: `Europe/London`, 08:00-17:00 local time
- New York: `America/New_York`, 08:00-17:00 local time

These local times are converted to UTC for the selected date using Python's `zoneinfo` support.

## Supported Commands

Download using `config.json`:

```powershell
python data_downloader.py
```

Download one day:

```powershell
python data_downloader.py 2024-01-02
```

Download a date range, including both dates:

```powershell
python data_downloader.py 2024-01-02 2024-01-31
```

Explore one day:

```powershell
python explorer.py 2024-01-26
```

Explore one day with session statistics:

```powershell
python explorer.py 2024-01-26 --sessions
```

Chart one day:

```powershell
python chart.py 2024-01-26
```

Chart one day in dark mode:

```powershell
python chart.py 2024-01-26 --dark
```

Chart one day with research-session overlays:

```powershell
python chart.py 2024-01-26 --sessions
```

Chart one day with dark mode and research-session overlays:

```powershell
python chart.py 2024-01-26 --dark --sessions
```

Create a multi-day session report:

```powershell
python session_report.py 2024-01-01 2024-01-31
```

Run the full automated test suite:

```powershell
python -m unittest discover -s tests
```

## Dependencies

External dependencies from `requirements.txt`:

- `matplotlib>=3.8,<4`
- `tzdata>=2024.1`

`matplotlib` is used by `chart.py`. `tzdata` provides IANA timezone data on Windows for `zoneinfo`.

## Data, Logs, Reports, And Tests

Raw downloaded CSV files are saved in `data_raw/` with filenames like:

```text
data_raw/XAUUSD_2024-01-26_1min_BID_UTC.csv
```

Raw CSV files are source records. They are not edited by analysis, charting, or reporting tools.

Downloader failures are logged to:

```text
logs/failed_downloads.txt
```

Generated reports are saved in `reports/` with filenames like:

```text
reports/session_report_2024-01-01_to_2024-01-31.csv
```

`reports/.gitkeep` keeps the report folder present in Git. Generated report CSV files are ignored.

Tests live in `tests/`. The automated tests use deterministic synthetic CSV fixtures created in temporary folders, so the suite does not require downloaded raw CSV files in `data_raw/`.

## Git Treatment Of Generated Files

`.gitignore` ignores:

- `data_raw/*.csv`
- `logs/`
- `reports/*`, except `reports/.gitkeep`
- `__pycache__/`
- `*.pyc`

Source code, tests, documentation, JSON configuration, and `requirements.txt` are not ignored.

## Automated Test Status

The current v0.10.1 test suite contains 20 tests and currently passes with:

```powershell
python -m unittest discover -s tests
```

The latest completed application milestone is v0.10.1.

## Recent Manually Verified Behaviour

The January 2024 session report command has been verified locally:

```powershell
python session_report.py 2024-01-01 2024-01-31
```

Observed summary:

```text
Session report complete.
Requested dates: 31
Completed dates: 27
Missing files: 0
No active candle dates: 4
Failed dates: 0
Output path: C:\Users\Lenovo\Documents\XAUUSD_Lab\reports\session_report_2024-01-01_to_2024-01-31.csv
```

## v0.10 Session Report Behaviour

`session_report.py` creates one CSV row per requested calendar date.

Each row includes:

- date, weekday, and status
- daily OHLC, range, and high/low times
- total CSV row count
- active candle count
- inactive placeholder count
- Tokyo, London, and New York session OHLC, range, high/low times, and active candle count

Statuses mean:

- `complete`: the daily CSV exists, active candles were found, and daily/session statistics were calculated.
- `missing_file`: the expected daily CSV file was not found.
- `no_active_candles`: the daily CSV exists, but no active candles remained after removing leading/trailing inactive placeholders.
- `failed`: the file existed but processing failed because of a handled read, parse, data, or file error.

Verified January 2024 result:

- 31 requested dates
- 27 complete dates
- 4 no-active-candle Saturdays
- 0 missing files
- 0 failed dates

## Known Limitations

- The current research data is BID-only and does not include ASK prices or spread.
- The project does not yet model commission, slippage, latency, or execution assumptions.
- There is no backtesting engine yet.
- There is no multi-year downloader orchestration yet.
- `explorer.py`, `chart.py`, and `session_report.py` are currently built around XAUUSD one-minute BID CSV filenames.
- Generated reports are overwritten when the same date range is run again.
- Session windows are configurable research windows, not proof of exchange opening hours.
- The current project is a research platform, not evidence of a profitable trading system.
