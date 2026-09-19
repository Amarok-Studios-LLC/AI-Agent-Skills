import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / 'skills/codex-token-steward/scripts'
sys.path.insert(0, str(SCRIPTS))
from accounting import Store
from reports import turn_report, save_report, estimate_cost
from integration import hook, install_integration, session_paths
from deployment import manifest, plan
from steward import main, record_note, compare, validate_registry


def event(typ, payload, second=1, ordinal=None):
    r = {'timestamp':'2026-09-19T10:00:%02d.000Z' % second,'type':typ,'payload':payload}
    if ordinal is not None:
        r['ordinal'] = ordinal
    return r


def meta(sid='main', second=0, parent=None):
    p = {'id':sid,'timestamp':'2026-09-19T10:00:%02d.000Z' % second,'cwd':'/project'}
    if parent:
        p['parent_thread_id'] = parent
    return event('session_meta',p,second)


def context(sid='t1', root='t1', second=1, model='test-model'):
    return event('turn_context',{'turn_id':sid,'root_turn_id':root,'model':model,'effort':'high','service_tier':'default'},second)


def usage(i=100,c=80,o=20,r=10):
    return {'input_tokens':i,'cached_input_tokens':c,'output_tokens':o,'reasoning_output_tokens':r,'total_tokens':i+o}


def token(total=None, last=None, second=2):
    u = total or usage()
    return event('event_msg',{'type':'token_count','info':{'total_token_usage':u,
                  'last_token_usage':last or u,'model_context_window':200000}},second)


def complete(turn='t1',second=4):
    return event('event_msg',{'type':'task_complete','turn_id':turn},second)


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.codex = self.root/'codex'
        (self.codex/'sessions').mkdir(parents=True)
        self.store = Store(self.root/'data')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def write(self, name, events, append=False):
        p = self.codex/'sessions'/name
        with p.open('a' if append else 'w',encoding='utf-8') as f:
            for e in events:
                f.write(json.dumps(e)+'\n')
        return p

    def report(self, session='main',turn='t1'):
        return turn_report(self.store,session,turn)

    def test_counter_subsets_and_duplicate_updates(self):
        p = self.write('main.jsonl',[meta(),context(),token(),token(second=3),complete()])
        self.store.scan([p])
        r = self.report()
        self.assertEqual(r['usage']['model_calls'],1)
        self.assertEqual(r['usage']['total_tokens'],120)
        self.assertEqual(r['usage']['uncached_input_tokens'],20)
        self.assertEqual(r['usage']['reasoning_output_tokens'],10)
        self.assertEqual(r['status'],'complete')
        self.assertEqual(self.store.scan([p])['bytes_read'],0)

    def test_partial_line_retried_once(self):
        p = self.write('main.jsonl',[meta(),context()])
        line = json.dumps(token())
        with p.open('a',encoding='utf-8') as f:f.write(line[:20])
        first = self.store.scan([p])
        self.assertEqual(first['deferred'],1)
        self.assertEqual(self.report()['usage']['model_calls'],0)
        with p.open('a',encoding='utf-8') as f:f.write(line[20:]+'\n')
        self.store.scan([p])
        self.assertEqual(self.report()['usage']['model_calls'],1)

    def test_append_and_distinct_turns(self):
        p = self.write('main.jsonl',[meta(),context(),token(),complete()])
        self.store.scan([p])
        self.write('main.jsonl',[context('t2','t2',5),token(usage(200,160,40,20),usage(),6)],True)
        self.store.scan([p])
        self.assertEqual(self.report(turn='t2')['usage']['total_tokens'],120)
        self.assertEqual(self.report()['usage']['model_calls'],1)

    def test_child_history_and_root_rollup(self):
        original = [meta(),context(),token()]
        p = self.write('main.jsonl',original)
        c = self.write('child.jsonl',[meta('child',5,'main')]+original+[
            context('ct','t1',6),token(usage(150,100,40,20),usage(50,20,20,10),7)])
        self.store.scan([c,p])  # Child discovered first must not contaminate ownership.
        r = self.report()
        self.assertEqual(r['usage']['model_calls'],2)
        self.assertEqual(r['linked_subagent_usage']['total_tokens'],70)
        self.assertEqual(r['usage']['total_tokens'],190)

    def test_duplicate_transcript_and_rewrite(self):
        events = [meta(),context(),token()]
        p = self.write('a.jsonl',events)
        q = self.write('b.jsonl',events)
        self.store.scan([p,q])
        self.assertEqual(self.report()['usage']['model_calls'],1)
        self.write('a.jsonl',events+[complete()])
        self.store.scan([p])
        self.assertEqual(self.report()['usage']['model_calls'],1)

    def test_reset_uses_last_call_not_negative_delta(self):
        p=self.write('main.jsonl',[meta(),context(),token(usage(900,800,100,50)),token(usage(50,20,10,5),second=3)])
        self.store.scan([p])
        self.assertEqual(self.report()['usage']['total_tokens'],1060)

    def test_invalid_counts_are_coverage_errors(self):
        bad = token(usage(20,30,10,5))
        p = self.write('main.jsonl',[meta(),context(),bad])
        self.store.scan([p])
        self.assertEqual(self.report()['usage']['model_calls'],0)
        self.assertEqual(self.report()['coverage']['parse_errors'],1)

    def test_missing_initial_last_not_counted(self):
        e = token()
        del e['payload']['info']['last_token_usage']
        p = self.write('main.jsonl',[meta(),context(),e])
        self.store.scan([p])
        self.assertEqual(self.report()['usage']['model_calls'],0)
        self.assertTrue(any('Initial cumulative' in w for w in self.report()['coverage']['warnings']))

    def test_delta_without_last_marked_aggregate(self):
        e = token(usage(200,160,40,20),second=3)
        del e['payload']['info']['last_token_usage']
        p=self.write('main.jsonl',[meta(),context(),token(),e])
        self.store.scan([p])
        self.assertEqual(self.report()['calls'][-1]['quality'],'aggregate_delta_not_exact_call')

    def test_no_unknown_root_cross_attribution(self):
        p=self.write('main.jsonl',[meta(),token()])
        q=self.write('other.jsonl',[meta('other'),token()])
        self.store.scan([p,q])
        self.assertEqual(self.report(turn='unattributed')['usage']['model_calls'],1)

    def test_raw_sensitive_content_not_persisted(self):
        secret='SENSITIVE_SENTINEL_91844'
        calls=[event('response_item',{'type':'function_call','call_id':str(n),'name':'read_file',
               'arguments':json.dumps({'path':secret})},3+n) for n in range(3)]
        p=self.write('main.jsonl',[meta(),context(),token()]+calls)
        self.store.scan([p])
        r=self.report()
        self.assertTrue(any(x['code']=='repeated_tool_inputs' for x in r['analysis']))
        self.assertNotIn(secret,json.dumps(r))
        for table in ('tools','calls','files','sessions','turns'):
            self.assertNotIn(secret,str([tuple(x) for x in self.store.db.execute('SELECT * FROM '+table)]))

    def test_steward_calls_not_flagged_as_repeat_waste(self):
        calls=[event('response_item',{'type':'custom_tool_call','call_id':str(n),'name':'exec',
                'input':'python steward.py report --current'},3+n) for n in range(4)]
        p=self.write('main.jsonl',[meta(),context(),token()]+calls)
        self.store.scan([p])
        r=self.report()
        self.assertEqual(r['tools']['steward_calls_identified'],4)
        self.assertFalse(any(x['code']=='repeated_tool_inputs' for x in r['analysis']))

    def test_unknown_model_and_cost_not_fabricated(self):
        p=self.write('main.jsonl',[meta(),context(model='future-model'),token()])
        self.store.scan([p])
        self.assertFalse(self.report()['cost']['complete'])
        self.assertEqual(self.report()['cost']['estimated_by_unit'],{})

    def test_hook_never_continues_or_blocks(self):
        p=self.write('main.jsonl',[meta(),context(),token(),complete()])
        for name in ('Stop','UserPromptSubmit','SubagentStop'):
            r=hook(self.store,self.codex,{'hook_event_name':name,'session_id':'main','turn_id':'t1','transcript_path':str(p)})
            self.assertNotIn('decision',r)
            self.assertNotIn('continue',r)
        self.assertTrue((self.root/'data/reports/main/t1.json').exists())

    def test_hook_does_not_read_arbitrary_supplied_file(self):
        outside=self.root/'outside.jsonl'
        outside.write_text('\n'.join(json.dumps(x) for x in [meta(),context(),token()])+'\n')
        hook(self.store,self.codex,{'hook_event_name':'Stop','session_id':'main','turn_id':'t1','transcript_path':str(outside)})
        self.assertEqual(self.report()['usage']['model_calls'],0)

    def test_integration_preserves_existing_and_is_idempotent(self):
        existing={'hooks':{'Stop':[{'hooks':[{'type':'command','command':'echo other','statusMessage':'other'}]}]}}
        (self.codex/'hooks.json').write_text(json.dumps(existing))
        (self.codex/'AGENTS.md').write_text('Existing user instructions.\n')
        script=SCRIPTS/'steward.py'
        install_integration(self.codex,script,self.store)
        install_integration(self.codex,script,self.store)
        h=json.loads((self.codex/'hooks.json').read_text())
        self.assertEqual(len(h['hooks']['Stop']),2)
        self.assertEqual((self.codex/'AGENTS.md').read_text().count('<!-- codex-token-steward:start -->'),1)
        install_integration(self.codex,script,self.store,True)
        self.assertEqual(json.loads((self.codex/'hooks.json').read_text())['hooks']['Stop'],existing['hooks']['Stop'])
        self.assertEqual((self.codex/'AGENTS.md').read_text().strip(),'Existing user instructions.')

    def test_explicit_outcomes_required_for_comparison(self):
        p=self.write('main.jsonl',[meta(),context(),token(),complete()])
        self.store.scan([p])
        for name,acceptance in [('a','accepted'),('b','unknown')]:
            record_note(self.store,'/project','outcome',{'id':name,'session':'main','turn':'t1',
                        'workload':'coding','scope':'same','acceptance':acceptance,'evidence':'test results'})
        r=compare(self.store,'a','b')
        self.assertFalse(r['both_explicitly_accepted'])
        self.assertFalse(r['causal_savings_proven'])

    def test_current_requires_identity(self):
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'','CODEX_SESSION_ID':''}),contextlib.redirect_stderr(io.StringIO()):
            result=main(['--codex-home',str(self.codex),'--data-dir',str(self.root/'other'),'report','--current'])
        self.assertEqual(result,1)

    def test_saved_report_contains_per_call_analysis(self):
        p=self.write('main.jsonl',[meta(),context(),token()])
        self.store.scan([p])
        target=save_report(self.store,self.report())
        self.assertIn('analysis',json.loads(target.read_text())['calls'][0])
        self.assertTrue(target.with_suffix('.md').exists())

    def test_scan_budget_is_resumable(self):
        p=self.write('main.jsonl',[meta(),context(),token(),complete()])
        first=self.store.scan([p],max_bytes=10)
        self.assertEqual(first['deferred'],1)
        self.store.scan([p])
        self.assertEqual(self.report()['usage']['model_calls'],1)

    def test_manifest_delta_and_no_mutations(self):
        art=self.root/'artifact';art.mkdir()
        (art/'a.txt').write_text('old')
        (art/'.env').write_text('SECRET')
        before=manifest(art)
        self.assertNotIn('.env',before['files'])
        (art/'a.txt').write_text('new')
        (art/'b.txt').write_text('add')
        after=manifest(art)
        result=plan(before,after,True)
        self.assertEqual(result['upload_candidates'],['a.txt','b.txt'])
        self.assertFalse(result['ready_to_execute'])
        self.assertEqual((art/'a.txt').read_text(),'new')

    def test_manifest_traversal_rejected(self):
        bad={'schema_version':1,'files':{'../outside':{'sha256':'a'*64,'bytes':0}}}
        with self.assertRaises(ValueError):plan(bad,bad)

    def test_rate_registry_rejects_untrusted_source(self):
        rate={'model':'x','service_tier':'default','unit':'USD','input':1,'cached':0.1,'output':2,
              'effective_from':'2026-01-01','checked_at':'2026-09-19','source':'https://example.com'}
        with self.assertRaises(ValueError):validate_registry({'schema_version':1,'rates':[rate]})

    def test_cli_smoke(self):
        result=subprocess.run([sys.executable,str(SCRIPTS/'steward.py'),'--codex-home',str(self.codex),
               '--data-dir',str(self.root/'cli'),'doctor'],text=True,capture_output=True,check=True)
        self.assertFalse(json.loads(result.stdout)['hard_spend_enforcement'])


if __name__=='__main__':
    unittest.main()
