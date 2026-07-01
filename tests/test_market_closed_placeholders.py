import hashlib
import os
import unittest
from datetime import time
from pathlib import Path
from tempfile import TemporaryDirectory


# Use a non-interactive backend so chart tests do not open a window.
os.environ["MPLBACKEND"] = "Agg"

import chart
import explorer
from candle_filters import remove_edge_inactive_placeholders
from fixture_helpers import make_active_rows, make_placeholder_rows, write_daily_csv


class MarketClosedPlaceholderTest(unittest.TestCase):
    def setUp(self):
        self.day = chart.parse_day("2024-01-26")

    def make_rows_with_edge_placeholders(self):
        return (
            make_placeholder_rows(self.day, time(0, 0), time(0, 2))
            + make_active_rows(self.day, time(0, 2), time(0, 6), base_price=2010.0)
            + make_placeholder_rows(self.day, time(0, 6), time(0, 9))
        )

    def test_leading_and_trailing_placeholders_are_detected(self):
        with TemporaryDirectory() as temp_root:
            csv_path = write_daily_csv(
                Path(temp_root),
                self.day,
                self.make_rows_with_edge_placeholders(),
            )
            chart_candles = chart.load_candles(csv_path)

        active_result = chart.get_active_candle_result(chart_candles)

        self.assertEqual(len(chart_candles), 9)
        self.assertEqual(active_result.leading_inactive_count, 2)
        self.assertEqual(active_result.trailing_inactive_count, 3)
        self.assertEqual(active_result.active_count, 4)
        self.assertEqual(active_result.inactive_count, 5)

        self.assertEqual(
            active_result.active_rows[0].timestamp.strftime("%H:%M"),
            "00:02",
        )
        self.assertEqual(
            active_result.active_rows[-1].timestamp.strftime("%H:%M"),
            "00:05",
        )

        for candle in chart_candles[:2] + chart_candles[6:]:
            self.assertTrue(chart.is_inactive_placeholder_candle(candle))

    def test_explorer_reports_raw_and_active_counts(self):
        explorer_rows = self.make_rows_with_edge_placeholders()
        active_rows = explorer.get_active_rows(explorer_rows).active_rows
        expected_low_row = min(active_rows, key=lambda row: float(row["low"]))

        statistics = explorer.calculate_daily_statistics(explorer_rows)

        self.assertEqual(statistics["total_csv_rows"], 9)
        self.assertEqual(statistics["active_candles"], 4)
        self.assertEqual(statistics["inactive_placeholder_rows"], 5)
        self.assertEqual(
            statistics["time_of_low"],
            expected_low_row["timestamp_utc"].split(" ")[1],
        )

    def test_middle_placeholder_like_rows_are_not_removed(self):
        rows = [
            {"name": "leading-placeholder"},
            {"name": "active-1"},
            {"name": "middle-placeholder-like"},
            {"name": "active-2"},
            {"name": "trailing-placeholder"},
        ]
        placeholder_names = {"leading-placeholder", "middle-placeholder-like", "trailing-placeholder"}

        result = remove_edge_inactive_placeholders(
            rows,
            lambda row: row["name"] in placeholder_names,
        )

        self.assertEqual(result.leading_inactive_count, 1)
        self.assertEqual(result.trailing_inactive_count, 1)
        self.assertEqual([row["name"] for row in result.active_rows], [
            "active-1",
            "middle-placeholder-like",
            "active-2",
        ])

    def test_raw_csv_is_not_edited_by_tools(self):
        with TemporaryDirectory() as temp_root:
            csv_path = write_daily_csv(
                Path(temp_root),
                self.day,
                self.make_rows_with_edge_placeholders(),
            )
            before_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()

            explorer.calculate_daily_statistics(explorer.load_candles(csv_path))

            if not chart.check_matplotlib_is_available():
                raise unittest.SkipTest("matplotlib is not installed")

            candles = chart.load_candles(csv_path)
            fig, _ax = chart.create_chart_figure(self.day, candles, dark_mode=True)
            chart.plt.close(fig)

            after_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()

        self.assertEqual(before_hash, after_hash)


if __name__ == "__main__":
    unittest.main()
