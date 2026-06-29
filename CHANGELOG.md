# Changelog

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
