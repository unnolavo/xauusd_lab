import os
import unittest


# Use a non-interactive backend so tests do not open a chart window.
os.environ["MPLBACKEND"] = "Agg"

from matplotlib.backend_bases import MouseEvent

import chart


class ChartAutoscaleRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not chart.check_matplotlib_is_available():
            raise unittest.SkipTest("matplotlib is not installed")

        day = chart.parse_day("2024-01-26")
        csv_path = chart.build_csv_path(day)

        if not csv_path.exists():
            raise unittest.SkipTest("2024-01-26 CSV is not available")

        cls.day = day
        cls.candles = chart.load_candles(csv_path)

    def test_initial_y_axis_uses_candle_prices_only(self):
        active_result = chart.get_active_candle_result(self.candles)
        actual_low = min(candle.low for candle in active_result.active_rows)
        actual_high = max(candle.high for candle in active_result.active_rows)
        actual_range = actual_high - actual_low

        for dark_mode in (False, True):
            fig, ax = chart.create_chart_figure(self.day, self.candles, dark_mode)
            y_min, y_max = ax.get_ylim()

            self.assertLess(y_min, actual_low)
            self.assertGreater(y_max, actual_high)
            self.assertGreater(y_min, 0)

            chart_range = y_max - y_min
            self.assertLess(chart_range, actual_range * 1.25)

            chart.plt.close(fig)

    def test_session_overlays_do_not_change_y_axis_scaling(self):
        active_result = chart.get_active_candle_result(self.candles)
        actual_low = min(candle.low for candle in active_result.active_rows)
        actual_high = max(candle.high for candle in active_result.active_rows)
        actual_range = actual_high - actual_low

        for dark_mode in (False, True):
            fig, ax = chart.create_chart_figure(
                self.day,
                self.candles,
                dark_mode=dark_mode,
                show_sessions=True,
            )
            y_min, y_max = ax.get_ylim()
            chart_range = y_max - y_min

            self.assertLess(y_min, actual_low)
            self.assertGreater(y_max, actual_high)
            self.assertGreater(y_min, 0)
            self.assertLess(chart_range, actual_range * 1.25)

            chart.plt.close(fig)

    def test_hover_does_not_reset_manual_zoom(self):
        fig, ax = chart.create_chart_figure(self.day, self.candles, dark_mode=False)

        manual_y_limits = (2018.0, 2024.0)
        ax.set_ylim(*manual_y_limits)

        target_candle = self.candles[100]
        target_x = chart.mdates.date2num(target_candle.timestamp)
        target_y = (target_candle.open + target_candle.close) / 2
        pixel_x, pixel_y = ax.transData.transform((target_x, target_y))

        event = MouseEvent("motion_notify_event", fig.canvas, pixel_x, pixel_y)
        fig.canvas.callbacks.process("motion_notify_event", event)

        self.assertEqual(ax.get_ylim(), manual_y_limits)
        chart.plt.close(fig)

    def test_chart_uses_active_time_window(self):
        fig, ax = chart.create_chart_figure(self.day, self.candles, dark_mode=False)

        x_min, x_max = ax.get_xlim()
        start_time = chart.mdates.num2date(x_min).replace(tzinfo=None)
        end_time = chart.mdates.num2date(x_max).replace(tzinfo=None)

        self.assertEqual(start_time.strftime("%H:%M"), "00:00")
        self.assertEqual(end_time.strftime("%H:%M"), "22:00")
        chart.plt.close(fig)


if __name__ == "__main__":
    unittest.main()
