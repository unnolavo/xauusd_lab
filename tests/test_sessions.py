import os
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory


# Use a non-interactive backend so chart tests do not open a window.
os.environ["MPLBACKEND"] = "Agg"

import chart
import explorer
from fixture_helpers import make_friday_rows_active_until_22_utc, write_daily_csv
from session_tools import get_session_windows


class TradingSessionOverlayTest(unittest.TestCase):
    def test_january_26_session_windows_convert_to_utc(self):
        day = chart.parse_day("2024-01-26")
        windows = {window.name: window for window in get_session_windows(day)}

        self.assertEqual(
            windows["Tokyo"].start_utc.strftime("%H:%M"),
            "00:00",
        )
        self.assertEqual(
            windows["Tokyo"].end_utc.strftime("%H:%M"),
            "09:00",
        )

        self.assertEqual(
            windows["London"].start_utc.strftime("%H:%M"),
            "08:00",
        )
        self.assertEqual(
            windows["London"].end_utc.strftime("%H:%M"),
            "17:00",
        )

        self.assertEqual(
            windows["New York"].start_utc.strftime("%H:%M"),
            "13:00",
        )
        self.assertEqual(
            windows["New York"].end_utc.strftime("%H:%M"),
            "22:00",
        )

    def test_july_1_session_windows_convert_to_dst_utc(self):
        day = chart.parse_day("2024-07-01")
        windows = {window.name: window for window in get_session_windows(day)}

        self.assertEqual(
            windows["Tokyo"].start_utc.strftime("%H:%M"),
            "00:00",
        )
        self.assertEqual(
            windows["Tokyo"].end_utc.strftime("%H:%M"),
            "09:00",
        )

        self.assertEqual(
            windows["London"].start_utc.strftime("%H:%M"),
            "07:00",
        )
        self.assertEqual(
            windows["London"].end_utc.strftime("%H:%M"),
            "16:00",
        )

        self.assertEqual(
            windows["New York"].start_utc.strftime("%H:%M"),
            "12:00",
        )
        self.assertEqual(
            windows["New York"].end_utc.strftime("%H:%M"),
            "21:00",
        )

    def test_chart_accepts_sessions_and_dark_mode_together(self):
        if not chart.check_matplotlib_is_available():
            raise unittest.SkipTest("matplotlib is not installed")

        day = chart.parse_day("2024-01-26")

        with TemporaryDirectory() as temp_root:
            csv_path = write_daily_csv(
                Path(temp_root),
                day,
                make_friday_rows_active_until_22_utc(day),
            )
            candles = chart.load_candles(csv_path)

            fig, ax = chart.create_chart_figure(
                day,
                candles,
                dark_mode=True,
                show_sessions=True,
            )

        y_min, _y_max = ax.get_ylim()
        self.assertGreater(y_min, 0)
        chart.plt.close(fig)

    def test_session_statistics_match_synthetic_csv_data(self):
        day = chart.parse_day("2024-01-26")
        rows = make_friday_rows_active_until_22_utc(day)
        active_rows = explorer.get_active_rows(rows).active_rows
        statistics_by_name = {
            statistics.session_name: statistics
            for statistics in explorer.calculate_session_statistics_for_day(day, rows)
        }

        for session_name, statistics in statistics_by_name.items():
            selected_rows = [
                row
                for row in active_rows
                if (
                    statistics.start_utc
                    <= datetime.strptime(row["timestamp_utc"], "%Y-%m-%d %H:%M:%S")
                    < statistics.end_utc
                )
            ]

            self.assertEqual(
                statistics.active_candle_count,
                540,
                f"{session_name} should contain 540 active one-minute candles",
            )
            self.assertEqual(len(selected_rows), 540)

            expected_high = max(float(row["high"]) for row in selected_rows)
            expected_low = min(float(row["low"]) for row in selected_rows)

            self.assertEqual(statistics.open, float(selected_rows[0]["open"]))
            self.assertEqual(statistics.close, float(selected_rows[-1]["close"]))
            self.assertEqual(statistics.high, expected_high)
            self.assertEqual(statistics.low, expected_low)
            self.assertAlmostEqual(
                statistics.range_dollars,
                expected_high - expected_low,
                places=6,
            )

    def test_overlapping_session_windows_can_share_candles(self):
        day = chart.parse_day("2024-01-26")
        rows = make_friday_rows_active_until_22_utc(day)
        active_rows = explorer.get_active_rows(rows).active_rows
        windows = {window.name: window for window in get_session_windows(day)}

        def selected_timestamps(session_name):
            window = windows[session_name]
            return {
                row["timestamp_utc"]
                for row in active_rows
                if (
                    window.start_utc
                    <= datetime.strptime(row["timestamp_utc"], "%Y-%m-%d %H:%M:%S")
                    < window.end_utc
                )
            }

        london_timestamps = selected_timestamps("London")
        new_york_timestamps = selected_timestamps("New York")
        shared_timestamps = london_timestamps & new_york_timestamps

        self.assertEqual(len(shared_timestamps), 240)
        self.assertIn("2024-01-26 13:00:00", shared_timestamps)
        self.assertIn("2024-01-26 16:59:00", shared_timestamps)


if __name__ == "__main__":
    unittest.main()
