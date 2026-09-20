import sys
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/codex-token-steward/scripts'))
from accounting import Store
from pace import weekly_pace, compact_pace, stamp, DAY, WEEK
from reports import turn_report, compact


class PaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name))
        self.start = datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp()
        self.reset = self.start + WEEK
        self.n = 0

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def sample(self, day, used, session='s', reset=None, bucket='codex:primary'):
        self.n += 1
        self.store.db.execute('INSERT INTO limits VALUES(?,?,?,?,?,?,?)',
            (str(self.n), stamp(self.start + day * DAY), session, bucket, 10080,
             self.reset if reset is None else reset, used))
        self.store.db.commit()

    def pace(self, day=2, session='s'):
        return weekly_pace(self.store, session, stamp(self.start + day * DAY))

    def test_target_and_forecast_exceeding_pace(self):
        self.sample(1, 20); self.sample(2, 40)
        p = self.pace()[0]
        self.assertEqual(p['reset_at'], stamp(self.reset))
        self.assertEqual(p['suggested_percentage_points_per_day'], 12)
        self.assertEqual(p['recent_percentage_points_per_day'], 20)
        self.assertAlmostEqual(p['pace_ratio_to_suggested'], 20 / 12)
        self.assertEqual(p['projected_exhaustion_at'], stamp(self.start + 5 * DAY))
        self.assertFalse(p['projected_to_last_until_reset'])

    def test_slow_pace_lasts(self):
        self.sample(1, 5); self.sample(2, 10)
        self.assertTrue(self.pace()[0]['projected_to_last_until_reset'])
        self.assertIn('lasts until reset', compact_pace(self.pace()))

    def test_single_sample_and_short_burst_never_forecast(self):
        self.sample(1.99, 10); self.sample(2, 20)
        p = self.pace()[0]
        self.assertIsNone(p['projected_exhaustion_at'])
        self.assertEqual(p['cycle_average_percentage_points_per_day'], 10)
        self.assertIsNone(self.pace(session='missing') or None)

    def test_unchanged_rounding_is_not_zero_rate(self):
        self.sample(1, 10); self.sample(2, 10)
        self.assertIsNone(self.pace()[0]['recent_percentage_points_per_day'])
        self.assertIsNone(self.pace()[0]['projected_to_last_until_reset'])

    def test_decrease_disables_forecast(self):
        self.sample(1, 30); self.sample(1.5, 10); self.sample(2, 40)
        self.assertEqual(self.pace()[0]['status'], 'usage_adjustment')
        self.assertIsNone(self.pace()[0]['projected_exhaustion_at'])

    def test_no_cross_session_mix(self):
        self.sample(1, 10, session='other'); self.sample(2, 40)
        self.assertIsNone(self.pace()[0]['recent_percentage_points_per_day'])

    def test_stale_and_expired(self):
        self.sample(1, 20); self.sample(2, 40)
        self.assertEqual(self.pace(3)[0]['status'], 'stale')
        self.assertIsNone(self.pace(3)[0]['suggested_percentage_points_per_day'])
        self.assertIsNone(self.pace(3)[0]['projected_exhaustion_at'])
        self.assertEqual(self.pace(8)[0]['status'], 'expired')

    def test_reset_separates_samples(self):
        self.sample(6, 90); self.sample(7.1, 2, reset=self.reset + WEEK)
        self.assertIsNone(self.pace(7.1)[0]['recent_percentage_points_per_day'])

    def test_invalid_reset_and_future_reading(self):
        self.sample(1, 10, reset='bad'); self.sample(3, 30)
        self.assertEqual(self.pace(), [])

    def test_exhausted_allowance(self):
        self.sample(1, 80); self.sample(2, 100)
        p = self.pace()[0]
        self.assertEqual(p['remaining_percent'], 0)
        self.assertEqual(p['suggested_percentage_points_per_day'], 0)
        self.assertIsNone(p['pace_ratio_to_suggested'])

    def test_no_model_tokens_does_not_hide_reset(self):
        self.sample(1, 10)
        report = turn_report(self.store, 's')
        self.assertIn('Weekly reset:', compact(report))
        self.assertIn('unavailable for this turn', compact(report))


if __name__ == '__main__':
    unittest.main()
