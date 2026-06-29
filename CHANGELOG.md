# Changelog

## v0.7

- Added optional dark mode to `chart.py` with `--dark`.
- Added hover cursor information for candlestick timestamp, open, high, low, and close values.
- Improved chart spacing, gridlines, and candle colour readability.

## v0.6

- Added `chart.py` for basic candlestick chart viewing.
- Added 1-minute candlesticks with time on the x-axis and price on the y-axis.
- Updated documentation with chart viewer usage.

## v0.5

- Added `explorer.py` for basic daily CSV exploration.
- Added open, high, low, close, daily range, high/low time, candle count, and average volume output.
- Updated documentation with explorer usage.

## v0.4

- Added `config.json` for default downloader settings.
- Added no-argument mode: `python data_downloader.py`.
- Kept command-line date mode working as before.
- Updated documentation for config-file and command-line usage.

## v0.3

- Added retry logic for temporary Dukascopy failures such as HTTP 503.
- The downloader retries each day up to 3 times before marking it as failed.
- Failed dates are logged only after all retry attempts fail.

## v0.2

- Added date range support.
- Added skip-existing-file behaviour.
- Added failed download logging to `logs/failed_downloads.txt`.
- Continued to the next date if one date failed.

## v0.1

- Added one-day Dukascopy downloader.
- Downloaded XAU/USD 1-minute BID candle data.
- Converted Dukascopy `.bi5` data into CSV.
- Saved CSV files into `data_raw/`.
