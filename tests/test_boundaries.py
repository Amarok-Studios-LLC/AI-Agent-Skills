import unittest
import test_steward as fixtures
from reports import turn_report, compact


def rate_event(percent,second,total=None,last=None,reset=100,window=10080):
    e=fixtures.token(total,last,second)
    e['payload']['rate_limits']={'limit_id':'codex','primary':{
        'used_percent':percent,'window_minutes':window,'resets_at':reset}}
    return e


class BoundaryTests(fixtures.AccountingTests):
    def test_prior_and_ending_readings_and_token_ledger(self):
        p=self.write('p.jsonl',[fixtures.meta(),fixtures.context('old','old'),rate_event(10,2),
            fixtures.complete('old',3),fixtures.context('t1','t1',5),
            rate_event(12,6,fixtures.usage(200,160,40,20),fixtures.usage()),fixtures.complete('t1',7)])
        self.store.scan([p]);r=self.report();b=r['boundaries']
        self.assertEqual(b['tokens']['start']['total_tokens'],120)
        self.assertEqual(b['tokens']['end']['total_tokens'],240)
        a=b['allowance'][0]
        self.assertEqual(a['start']['used_percent'],10)
        self.assertEqual(a['end']['used_percent'],12)
        self.assertEqual(a['change_percentage_points'],2)
        self.assertEqual(a['start']['age_at_turn_start_seconds'],3)
        self.assertIn('10% used / 90% left -> 12% used / 88% left',compact(r))
        self.assertEqual(b['unavailable_standard_windows_minutes'],[300])

    def test_first_in_turn_reading_not_called_exact_start(self):
        p=self.write('p.jsonl',[fixtures.meta(),fixtures.context(),rate_event(10,2),
                              rate_event(12,3,fixtures.usage(200,160,40,20),fixtures.usage())])
        self.store.scan([p]);a=self.report()['boundaries']['allowance'][0]
        self.assertEqual(a['start_basis'],'first_observed_during_turn_not_actual_start')
        self.assertIn('not a pre-turn reading',compact(self.report()))

    def test_reset_suppresses_misleading_consumption_delta(self):
        p=self.write('p.jsonl',[fixtures.meta(),fixtures.context('old','old'),rate_event(99,2),
            fixtures.context('t1','t1',5),rate_event(1,6,fixtures.usage(200,160,40,20),fixtures.usage(),reset=200)])
        self.store.scan([p]);a=self.report()['boundaries']['allowance'][0]
        self.assertTrue(a['window_changed'])
        self.assertIsNone(a['change_percentage_points'])

    def test_same_window_usage_decrease_not_negative_consumption(self):
        p=self.write('p.jsonl',[fixtures.meta(),fixtures.context(),rate_event(90,2),
                              rate_event(80,3,fixtures.usage(200,160,40,20),fixtures.usage())])
        self.store.scan([p]);a=self.report()['boundaries']['allowance'][0]
        self.assertTrue(a['usage_decreased'])
        self.assertIsNone(a['change_percentage_points'])

    def test_missing_end_not_replaced_by_stale_start(self):
        p=self.write('p.jsonl',[fixtures.meta(),fixtures.context('old','old'),rate_event(10,2),
            fixtures.context('t1','t1',5),fixtures.token(fixtures.usage(200,160,40,20),fixtures.usage(),6)])
        self.store.scan([p]);a=self.report()['boundaries']['allowance'][0]
        self.assertIsNone(a['end'])
        self.assertIsNone(a['change_percentage_points'])

    def test_other_session_readings_do_not_contaminate_boundaries(self):
        p=self.write('p.jsonl',[fixtures.meta(),fixtures.context(),rate_event(10,2)])
        q=self.write('q.jsonl',[fixtures.meta('other'),fixtures.context('other','other'),rate_event(90,3)])
        self.store.scan([p,q]);a=self.report()['boundaries']['allowance'][0]
        self.assertEqual(a['end']['used_percent'],10)

    def test_unchanged_rounded_reading_not_proof_of_free_usage(self):
        p=self.write('p.jsonl',[fixtures.meta(),fixtures.context(),rate_event(10,2),
                              rate_event(10,3,fixtures.usage(200,160,40,20),fixtures.usage())])
        self.store.scan([p]);r=self.report();a=r['boundaries']['allowance'][0]
        self.assertEqual(a['change_percentage_points'],0)
        self.assertGreater(r['usage']['total_tokens'],0)
        self.assertIn('does not mean zero consumption',a['note'])


for name in dir(fixtures.AccountingTests):
    if name.startswith('test_') and name not in BoundaryTests.__dict__:
        setattr(BoundaryTests,name,None)
