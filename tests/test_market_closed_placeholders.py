import hashlib
import os
import unittest


# Use a non-interactive backend so chart tests do not open a window.
os.environ["MPLBACKEND"] = "Agg"

import chart
import explorer
from candle_filters import remove_edge_inactive_placeholders


class MarketClosedPlaceholderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.day = chart.parse_day("2024-01-26")
        cls.csv_path = chart.build_csv_path(cls.day)

        if not cls.csv_path.exists():
            raise unittest.SkipTest("2024-01-26 CSV is not available")

        cls.chart_candles = chart.load_candles(cls.csv_path)
        cls.explorer_rows = explorer.load_candles(cls.csv_path)

    def test_january_26_trailing_placeholders_are_detected(self):
        active_result = chart.get_active_candle_result(self.chart_candles)

        self.assertEqual(len(self.chart_candles), 1440)
        self.assertEqual(active_result.leading_inactive_count, 0)
        self.assertEqual(active_result.trailing_inactive_count, 120)
        self.assertEqual(active_result.active_count, 1320)
        self.assertEqual(active_result.inactive_count, 120)

        self.assertEqual(
            active_result.active_rows[-1].timestamp.strftime("%H:%M"),
            "21:59",
        )
        self.assertEqual(self.chart_candles[1320].timestamp.strftime("%H:%M"), "22:00")
        self.assertEqual(self.chart_candles[-1].timestamp.strftime("%H:%M"), "23:59")

        for candle in self.chart_candles[1320:]:
            self.assertTrue(chart.is_inactive_placeholder_candle(candle))

    def test_explorer_reports_raw_and_active_counts(self):
        statistics = explorer.calculate_daily_statistics(self.explorer_rows)

        self.assertEqual(statistics["total_csv_rows"], 1440)
        self.assertEqual(statistics["active_candles"], 1320)
        self.assertEqual(statistics["inactive_placeholder_rows"], 120)
        self.assertEqual(statistics["time_of_low"], "16:14:00")

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
        before_hash = hashlib.sha256(self.csv_path.read_bytes()).hexdigest()

        explorer.calculate_daily_statistics(explorer.load_candles(self.csv_path))

        if not chart.check_matplotlib_is_available():
            raise unittest.SkipTest("matplotlib is not installed")

        candles = chart.load_candles(self.csv_path)
        fig, _ax = chart.create_chart_figure(self.day, candles, dark_mode=True)
        chart.plt.close(fig)

        after_hash = hashlib.sha256(self.csv_path.read_bytes()).hexdigest()
        self.assertEqual(before_hash, after_hash)


if __name__ == "__main__":
    unittest.main()
