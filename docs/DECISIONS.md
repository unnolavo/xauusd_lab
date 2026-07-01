# Durable Decisions

This document records architectural and research decisions that should be preserved unless the user explicitly approves a change.

## Data Source And Time

- The current market data source is Dukascopy XAU/USD one-minute BID data.
- Timestamps are stored and processed internally in UTC.
- Local timezones are used only when explicitly displaying or defining session windows.
- Python `zoneinfo` is used for timezone conversion, with local timezone definitions rather than fixed UTC offsets.

## Raw Data

- Raw downloaded CSV files are immutable source records.
- Do not edit raw CSV files in `data_raw/`.
- Cleaning, filtering, transformation, and derived calculations happen outside the raw layer.
- Inactive leading and trailing market-closed placeholder candles are excluded in analysis and display rather than deleted from raw files.
- Do not classify every isolated flat zero-volume candle as market closed.
- Do not interpolate genuine market closures.
- Do not splice unrelated providers' prices into Dukascopy closures.

## Session Research

- Session definitions come from `sessions.json`.
- Tokyo, London, and New York sessions are configurable research windows rather than universal exchange sessions.
- Daylight-saving conversion must use `zoneinfo` and the configured local timezone definitions.
- Session candle selection is start-inclusive and end-exclusive.
- Session windows can overlap, so one candle may belong to more than one session.
- Because sessions overlap, future claims such as "one session broke another session's range" require a precise, non-ambiguous definition before implementation.

## Shared Logic

- Shared filtering logic belongs in `candle_filters.py`.
- Shared session loading, timezone conversion, selection, and statistics logic belongs in `session_tools.py`.
- Tools should reuse shared modules instead of duplicating calculations.
- Python should stay readable and beginner-friendly.

## Generated Files

- Generated reports are ignored by Git.
- Downloaded raw CSV files, logs, caches, and temporary artifacts should not be committed.

## Research And Trading Claims

- Current BID-only research is not sufficient for realistic strategy profitability claims.
- Future execution-aware testing must account for ASK data, spread, commission, slippage, latency, and execution assumptions.
- Findings should eventually be validated against another suitable data source and the intended live broker.
- The project is a research platform, not evidence of a profitable trading system.

