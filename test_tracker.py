import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TRACKER = Path(__file__).resolve().parents[1] / "tracker.py"
DAY = "2026-01-15"


class TrackerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.database = Path(temp.name) / "test.sqlite3"

    def run_tracker(self, *args, expected_status=0):
        result = subprocess.run(
            [sys.executable, str(TRACKER), "--db", str(self.database), *args],
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, expected_status, result.stderr)
        return result

    def report(self, day=DAY):
        return self.run_tracker("summary", "--date", day).stdout

    def assert_metric(self, report, label, values):
        row = next(line for line in report.splitlines() if line.startswith(label))
        self.assertEqual(row[len(label):].split(), [str(value) for value in values])

    def test_meals_persist_and_summary_tracks_edits_and_deletes(self):
        self.run_tracker("goal", "--date", DAY, "--kcal", "2000", "--protein", "130", "--fat", "60", "--carbs", "235")
        self.run_tracker("add", "Rice bowl", "--date", DAY, "--kcal", "600", "--protein", "40", "--fat", "20", "--carbs", "65")
        self.run_tracker("add", "Yogurt", "--date", DAY, "--kcal", "200", "--protein", "15", "--fat", "4", "--carbs", "26")
        report = self.report()
        self.assert_metric(report, "Energy (kcal)", [2000, 800, 1200])
        self.assert_metric(report, "Protein (g)", [130, 55, 75])
        self.assert_metric(report, "Fat (g)", [60, 24, 36])
        self.assert_metric(report, "Carbs (g)", [235, 91, 144])

        self.run_tracker("edit", "1", "Half rice bowl", "--kcal", "300", "--protein", "20", "--fat", "10", "--carbs", "33")
        self.assert_metric(self.report(), "Energy (kcal)", [2000, 500, 1500])
        self.run_tracker("delete", "2")
        report = self.report()
        self.assert_metric(report, "Energy (kcal)", [2000, 300, 1700])
        self.assertIn("Half rice bowl", report)
        self.assertNotIn("Yogurt", report)

    def test_dates_are_isolated_and_overages_are_visible(self):
        self.run_tracker("goal", "--date", DAY, "--kcal", "300", "--protein", "25", "--fat", "10", "--carbs", "30")
        self.run_tracker("add", "Dinner", "--date", DAY, "--kcal", "400", "--protein", "35", "--fat", "12", "--carbs", "38")
        self.assert_metric(self.report(), "Energy (kcal)", [300, 400, -100])
        tomorrow = self.report("2026-01-16")
        self.assert_metric(tomorrow, "Energy (kcal)", ["—", 0, "—"])
        self.assertNotIn("Dinner", tomorrow)

    def test_bad_inputs_and_missing_meals_are_reported(self):
        result = self.run_tracker("summary", "--date", "2026-02-30", expected_status=2)
        self.assertIn("valid date", result.stderr)
        result = self.run_tracker("add", "Lunch", "--kcal", "-1", "--protein", "0", "--fat", "0", "--carbs", "0", expected_status=2)
        self.assertIn("nonnegative", result.stderr)
        result = self.run_tracker("delete", "1", expected_status=1)
        self.assertIn("Meal #1 was not found", result.stderr)

    def test_demo_does_not_create_or_write_to_the_local_database(self):
        demo = self.run_tracker("demo").stdout
        self.assertIn("Chicken rice bowl", demo)
        self.assert_metric(demo, "Energy (kcal)", [2000, 1000, 1000])
        self.assertFalse(self.database.exists())
