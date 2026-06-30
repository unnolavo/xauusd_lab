import csv
import hashlib
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import explorer
import session_report


class SessionReportTest(unittest.TestCase):
    def test_short_january_range_writes_one_row_per_date(self):
        start_day = date(2024, 1, 1)
        end_day = date(2024, 1, 3)

        for day in session_report.each_day(start_day, end_day):
            if not session_report.build_csv_path(day).exists():
                raise unittest.SkipTest("January 2024 CSV files are not available")

        summary = session_report.create_session_report(start_day, end_day)

        with summary.output_path.open("r", newline="", encoding="utf-8") as report_file:
            rows = list(csv.DictReader(report_file))

        self.assertEqual(summary.requested_dates, 3)
        self.assertEqual(len(rows), 3)
        self.assertEqual(summary.completed_dates, 3)
        self.assertEqual(summary.missing_files, 0)
        self.assertEqual(summary.no_active_candle_dates, 0)
        self.assertEqual(summary.failed_dates, 0)
        self.assertEqual([row["status"] for row in rows], ["complete", "complete", "complete"])

    def test_single_day_values_match_existing_calculations(self):
        day = date(2024, 1, 26)
        csv_path = session_report.build_csv_path(day)

        if not csv_path.exists():
            raise unittest.SkipTest("2024-01-26 CSV is not available")

        before_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        summary = session_report.create_session_report(day, day)

        with summary.output_path.open("r", newline="", encoding="utf-8") as report_file:
            report_row = next(csv.DictReader(report_file))

        raw_rows = explorer.load_candles(csv_path)
        daily_statistics = explorer.calculate_daily_statistics(raw_rows)
        session_statistics = {
            statistics.session_name.lower().replace(" ", "_"): statistics
            for statistics in explorer.calculate_session_statistics_for_day(day, raw_rows)
        }

        self.assertEqual(report_row["daily_open"], f"{daily_statistics['open_price']:.3f}")
        self.assertEqual(report_row["daily_high"], f"{daily_statistics['high_price']:.3f}")
        self.assertEqual(report_row["daily_low"], f"{daily_statistics['low_price']:.3f}")
        self.assertEqual(report_row["daily_close"], f"{daily_statistics['close_price']:.3f}")
        self.assertEqual(report_row["daily_range"], f"{daily_statistics['daily_range']:.3f}")
        self.assertEqual(report_row["active_candle_count"], "1320")
        self.assertEqual(report_row["inactive_placeholder_count"], "120")

        tokyo_statistics = session_statistics["tokyo"]
        self.assertEqual(report_row["tokyo_open"], f"{tokyo_statistics.open:.3f}")
        self.assertEqual(report_row["tokyo_high"], f"{tokyo_statistics.high:.3f}")
        self.assertEqual(report_row["tokyo_low"], f"{tokyo_statistics.low:.3f}")
        self.assertEqual(report_row["tokyo_close"], f"{tokyo_statistics.close:.3f}")
        self.assertEqual(report_row["tokyo_range"], f"{tokyo_statistics.range_dollars:.3f}")
        self.assertEqual(report_row["tokyo_active_candle_count"], "540")

        after_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        self.assertEqual(before_hash, after_hash)

    def test_summary_counts_reconcile_to_requested_dates(self):
        start_day = date(2024, 1, 1)
        end_day = date(2024, 1, 31)
        summary = session_report.create_session_report(start_day, end_day)

        counted_dates = (
            summary.completed_dates
            + summary.missing_files
            + summary.no_active_candle_dates
            + summary.failed_dates
        )

        self.assertEqual(summary.requested_dates, 31)
        self.assertEqual(summary.no_active_candle_dates, 4)
        self.assertEqual(counted_dates, summary.requested_dates)

    def test_missing_file_produces_missing_file_status_row(self):
        day = date(2024, 1, 15)
        columns = session_report.build_report_columns(day)
        missing_path = session_report.PROJECT_DIR / "missing_test_file.csv"

        with patch("session_report.build_csv_path", return_value=missing_path):
            result = session_report.process_one_day(day, columns)

        self.assertEqual(result.row["date"], "2024-01-15")
        self.assertEqual(result.row["weekday"], "Monday")
        self.assertEqual(result.row["status"], "missing_file")
        self.assertFalse(result.completed)
        self.assertTrue(result.missing_file)
        self.assertFalse(result.failed)

    def test_report_columns_have_stable_order(self):
        columns = session_report.build_report_columns(date(2024, 1, 1))
        expected_columns = [
            "date",
            "weekday",
            "status",
            "daily_open",
            "daily_high",
            "daily_low",
            "daily_close",
            "daily_range",
            "time_of_daily_high_utc",
            "time_of_daily_low_utc",
            "total_csv_rows",
            "active_candle_count",
            "inactive_placeholder_count",
            "tokyo_open",
            "tokyo_high",
            "tokyo_low",
            "tokyo_close",
            "tokyo_range",
            "tokyo_time_of_high_utc",
            "tokyo_time_of_low_utc",
            "tokyo_active_candle_count",
            "london_open",
            "london_high",
            "london_low",
            "london_close",
            "london_range",
            "london_time_of_high_utc",
            "london_time_of_low_utc",
            "london_active_candle_count",
            "new_york_open",
            "new_york_high",
            "new_york_low",
            "new_york_close",
            "new_york_range",
            "new_york_time_of_high_utc",
            "new_york_time_of_low_utc",
            "new_york_active_candle_count",
        ]

        self.assertEqual(columns, expected_columns)


if __name__ == "__main__":
    unittest.main()
