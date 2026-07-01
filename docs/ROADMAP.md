# Roadmap

Current confirmed milestone: **v0.10**.

Completed milestones are reconstructed from `CHANGELOG.md`, the current repository, and Git history.

## Completed Milestones

### v0.1

- Added a one-day Dukascopy downloader.
- Downloaded XAU/USD one-minute BID candle data.
- Converted Dukascopy `.bi5` data into CSV.
- Saved CSV files into `data_raw/`.

### v0.2

- Added date range support.
- Added skip-existing-file behaviour.
- Added failed download logging to `logs/failed_downloads.txt`.
- Continued to the next date if one date failed.

### v0.3

- Added retry logic for temporary Dukascopy failures such as HTTP 503.
- Retried each day up to three times before marking it as failed.
- Logged failed dates only after all retry attempts failed.

### v0.4

- Added `config.json` for default downloader settings.
- Added no-argument downloader mode: `python data_downloader.py`.
- Kept command-line date mode working.
- Updated documentation for config-file and command-line usage.

### v0.5

- Added `explorer.py` for basic daily CSV exploration.
- Printed open, high, low, close, daily range, high/low time, candle count, and average volume.
- Updated documentation with explorer usage.

### v0.6

- Added `chart.py` for basic candlestick chart viewing.
- Added one-minute candlesticks with time on the x-axis and price on the y-axis.
- Updated documentation with chart viewer usage.

### v0.7

- Added optional dark mode to `chart.py` with `--dark`.
- Added hover cursor information for candlestick timestamp, open, high, low, and close values.
- Improved chart spacing, gridlines, and candle colour readability.

### v0.7.1

- Added shared detection for leading and trailing market-closed placeholder rows.
- Updated `chart.py` to skip edge placeholder candles without editing raw CSV files.
- Updated `explorer.py` to report total rows, active candles, and inactive placeholder rows.
- Added regression tests for January 26, 2024 market-close placeholders and chart autoscaling.

### v0.8

- Added optional Tokyo, London, and New York research-session overlays to `chart.py`.
- Added `sessions.json` for configurable local-time session definitions.
- Converted session windows to UTC with Python `zoneinfo`, including daylight-saving support.
- Added tests for January 26, 2024 session UTC windows and chart scaling with overlays.

### v0.9

- Added `session_tools.py` for shared session loading, timezone conversion, candle selection, and session statistics.
- Added `python explorer.py YYYY-MM-DD --sessions` for Tokyo, London, and New York session statistics.
- Kept chart session overlays working through shared session tools.
- Added `requirements.txt` with `matplotlib` and `tzdata`.
- Added tests for January 26, 2024 session statistics and July 1, 2024 daylight-saving conversions.

### v0.10

- Added `session_report.py` for multi-day session research reports.
- Added one output row per requested date with daily and configured-session statistics.
- Added report statuses for complete, missing file, no active candles, and failed dates.
- Added `reports/.gitkeep` and ignored generated report CSV files.
- Added tests for report row counts, missing files, stable column order, and single-day value matching.
- Current repository behaviour also prints no-active-candle dates in the session-report completion summary.

## Proposed Future Work

Everything in this section is proposed only. It is not approved or implemented unless a future user request explicitly says so.

- Aggregate multi-day session analysis.
- Weekday and distribution analysis.
- Carefully defined range and breakout relationships.
- Expanded data validation.
- ASK data and spread data.
- Execution-cost modelling.
- Chart interaction and annotation.
- Replay tools.
- Journaling tools.
- Support and resistance research.
- Hypothesis testing.
- Strategy testing and backtesting.

Do not invent future version numbers unless the repository already contains an approved version plan.
