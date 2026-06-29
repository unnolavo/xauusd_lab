# XAUUSD Lab

XAUUSD Lab is a long-term Python research project for studying XAU/USD, which is Gold priced in US Dollars.

The project will grow step by step into a research platform for downloading historical market data, storing it cleanly, analysing price behaviour, testing trading strategies, and eventually building a desktop research application.

Current version: **v0.3**

## Current Feature

The current tool is a Dukascopy downloader for:

- XAU/USD
- 1-minute candles
- BID prices
- UTC timestamps

It downloads Dukascopy `.bi5` files, converts them into CSV format, and saves the CSV files locally.

## How To Run

Download one day:

```powershell
python data_downloader.py 2024-01-02
```

Download a date range:

```powershell
python data_downloader.py 2024-01-02 2024-01-31
```

The date range includes both the start date and the end date.

## Output Files

Downloaded CSV files are saved in the `data_raw/` folder.

Example:

```text
data_raw/XAUUSD_2024-01-02_1min_BID_UTC.csv
```

If a CSV file already exists, the downloader skips that day instead of downloading it again.

## Failed Downloads

Failed downloads are logged in:

```text
logs/failed_downloads.txt
```

In v0.3, the downloader retries each failed day up to 3 times before writing it to the failed download log.

## Roadmap

- v0.4: Improve downloader configuration and validation.
- Future: Download longer historical periods safely.
- Future: Organise raw data into a clean master dataset.
- Future: Add basic analysis scripts.
- Future: Build and test simple trading strategies.
- Future: Create a desktop research application.
