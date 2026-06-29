"""
Helpers for separating active candles from market-closed placeholder rows.

Dukascopy can include flat, zero-volume rows when the market is closed. We keep
those rows in the raw CSV files, but analysis tools should ignore contiguous
placeholder rows at the beginning or end of the file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class ActiveCandleResult:
    """The result of removing only edge placeholder rows from a candle list."""

    active_rows: list
    leading_inactive_count: int
    trailing_inactive_count: int

    @property
    def active_count(self) -> int:
        """How many rows remain after edge placeholders are removed."""
        return len(self.active_rows)

    @property
    def inactive_count(self) -> int:
        """How many leading/trailing placeholder rows were found."""
        return self.leading_inactive_count + self.trailing_inactive_count


def is_flat_zero_volume_candle(
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: float,
) -> bool:
    """Return True when one row looks like a market-closed placeholder."""
    return (
        volume == 0
        and open_price == high_price
        and open_price == low_price
        and open_price == close_price
    )


def remove_edge_inactive_placeholders(
    rows: list,
    is_placeholder: Callable[[object], bool],
) -> ActiveCandleResult:
    """Remove contiguous placeholder rows only from the start and end.

    This intentionally does not remove matching rows from the middle of a file.
    An isolated flat, zero-volume candle can happen during active trading, so we
    only treat edge groups as inactive market-closed placeholders.
    """
    first_active_index = 0
    last_active_index = len(rows)

    while first_active_index < last_active_index and is_placeholder(
        rows[first_active_index]
    ):
        first_active_index += 1

    while last_active_index > first_active_index and is_placeholder(
        rows[last_active_index - 1]
    ):
        last_active_index -= 1

    return ActiveCandleResult(
        active_rows=rows[first_active_index:last_active_index],
        leading_inactive_count=first_active_index,
        trailing_inactive_count=len(rows) - last_active_index,
    )
