# XAUUSD Lab

XAUUSD Lab is a long-term Python research project for studying XAU/USD, which is Gold priced in US Dollars.

The project will grow step by step into a research platform for downloading historical market data, storing it cleanly, analysing price behaviour, testing trading strategies, and eventually building a desktop research application.

Current version: **v0.7**

## Current Features

### Downloader

The downloader gets Dukascopy data for:

- XAU/USD
- 1-minute candles
- BID prices
- UTC timestamps

It downloads Dukascopy `.bi5` files, converts them into CSV format, and saves the CSV files locally.

## How To Run

You can run the downloader in two ways.

### Option 1: Use config.json

If you run the script without dates, it reads the date range and market settings from `config.json`:

```powershell
python data_downloader.py
```

The current `config.json` file contains:

```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "symbol": "XAUUSD",
  "price_side": "BID",
  "timeframe": "min_1"
}
```

### Option 2: Type Dates In The Terminal

Download one day:

```powershell
python data_downloader.py 2024-01-02
```

Download a date range:

```powershell
python data_downloader.py 2024-01-02 2024-01-31
```

The date range includes both the start date and the end date.

### Data Explorer

Use `explorer.py` to print basic daily statistics for one downloaded CSV file.

```powershell
python explorer.py 2024-01-26
```

For that command, the explorer loads:

```text
data_raw/XAUUSD_2024-01-26_1min_BID_UTC.csv
```

It prints the open, high, low, close, daily range, time of high, time of low, total candles, and average volume.

### Chart Viewer

Use `chart.py` to display a candlestick chart for one downloaded CSV file.

```powershell
python chart.py 2024-01-26
```

You can also open the chart in dark mode:

```powershell
python chart.py 2024-01-26 --dark
```

For that command, the chart viewer loads:

```text
data_raw/XAUUSD_2024-01-26_1min_BID_UTC.csv
```

The chart shows 1-minute candlesticks with time on the x-axis and price on the y-axis. Hover near a candle to see its timestamp, open, high, low, and close values.

The chart viewer uses `matplotlib`. If needed, install it with:

```powershell
python -m pip install matplotlib
```

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

The downloader retries each failed day up to 3 times before writing it to the failed download log.

## Roadmap

- Future: Improve downloader configuration and validation.
- Future: Download longer historical periods safely.
- Future: Organise raw data into a clean master dataset.
- Future: Add more analysis, exploration, and charting tools.
- Future: Build and test simple trading strategies.
- Future: Create a desktop research application.
