import os
import unittest


# Use a non-interactive backend so chart tests do not open a window.
os.environ["MPLBACKEND"] = "Agg"

import chart


class TradingSessionOverlayTest(unittest.TestCase):
    def test_january_26_session_windows_convert_to_utc(self):
        day = chart.parse_day("2024-01-26")
        windows = {window.name: window for window in chart.get_session_windows(day)}

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

    def test_chart_accepts_sessions_and_dark_mode_together(self):
        if not chart.check_matplotlib_is_available():
            raise unittest.SkipTest("matplotlib is not installed")

        day = chart.parse_day("2024-01-26")
        csv_path = chart.build_csv_path(day)

        if not csv_path.exists():
            raise unittest.SkipTest("2024-01-26 CSV is not available")

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


if __name__ == "__main__":
    unittest.main()
