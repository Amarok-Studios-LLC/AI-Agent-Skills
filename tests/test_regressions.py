import json
import os
import pathlib
import subprocess
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone

from test_steward import AccountingTests, meta, context, token, usage, complete, event, SCRIPTS
from reports import turn_report, estimate_cost
from steward import validate_registry
from integration import hook


class RegressionTests(AccountingTests):
    # Override inherited test discovery below to avoid executing base cases twice.
    def test_child_report_excludes_ancestors_and_siblings(self):
        p=self.write('p.jsonl',[meta(),context(),token()])
        c=self.write('c.jsonl',[meta('child',5,'main'),context('ct','t1',6),token(usage(200,100,20,0),second=7)])
        s=self.write('s.jsonl',[meta('sibling',5,'main'),context('st','t1',6),token(usage(300,100,20,0),second=8)])
        self.store.scan([p,c,s])
        child=turn_report(self.store,'child','ct')
        self.assertEqual(child['usage']['input_tokens'],200)
        self.assertEqual(child['linked_subagent_usage']['model_calls'],0)
        self.assertEqual(turn_report(self.store,'main','t1')['usage']['input_tokens'],600)

    def test_multiple_billing_units_stay_separate(self):
        checked=datetime.now(timezone.utc).date().isoformat()
        base={'model':'test-model','service_tier':'default','input':1,'cached':0.1,'output':2,
              'effective_from':'2020-01-01','checked_at':checked,'source':'https://learn.chatgpt.com/docs/pricing'}
        catalog={'schema_version':1,'models':[], 'rates':[dict(base,unit='USD'),dict(base,unit='credits',input=5)]}
        validate_registry(catalog)
        (self.root/'data/models.json').write_text(json.dumps(catalog))
        p=self.write('p.jsonl',[meta(),context(),token()]);self.store.scan([p])
        r=self.report()['cost']
        self.assertEqual(set(r['estimated_by_unit']),{'USD','credits'})
        self.assertTrue(r['complete'])

    def test_unknown_tier_does_not_inherit_default_price(self):
        p=self.write('p.jsonl',[meta(),event('turn_context',{'turn_id':'t1','model':'test-model'}),token()])
        self.store.scan([p])
        self.assertIn('test-model/unknown',self.report()['cost']['unpriced_model_service_pairs'])

    def test_partial_billing_units_not_reported_complete(self):
        checked=datetime.now(timezone.utc).date().isoformat()
        base={'service_tier':'default','input':1,'cached':0.1,'output':2,'effective_from':'2020-01-01',
              'checked_at':checked,'source':'https://learn.chatgpt.com/docs/pricing'}
        rates=[dict(base,model='a',unit='USD'),dict(base,model='b',unit='credits')]
        (self.root/'data/models.json').write_text(json.dumps({'schema_version':1,'models':[],'rates':rates}))
        p=self.write('p.jsonl',[meta(),context(model='a'),token(),context(second=3,model='b'),
                               token(usage(200,160,40,20),usage(),4)])
        self.store.scan([p])
        r=self.report()['cost']
        self.assertFalse(r['complete'])
        self.assertEqual(r['complete_by_unit'],{'USD':False,'credits':False})

    def test_rate_limit_updates_not_new_model_calls(self):
        a=token();b=token(second=3)
        for e,percent,reset in [(a,99,100),(b,0,200)]:
            e['payload']['rate_limits']={'limit_id':'codex','primary':{'used_percent':percent,'window_minutes':10080,'resets_at':reset}}
        p=self.write('p.jsonl',[meta(),context(),a,b]);self.store.scan([p])
        self.assertEqual(self.report()['usage']['model_calls'],1)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM limits').fetchone()[0],2)

    def test_doctor_does_not_claim_manual_hook_proves_automation(self):
        hook(self.store,self.codex,{'hook_event_name':'Stop','session_id':'not-present','turn_id':'t'})
        r=subprocess.run([sys.executable,str(SCRIPTS/'steward.py'),'--codex-home',str(self.codex),
                          '--data-dir',str(self.root/'data'),'doctor'],text=True,capture_output=True,check=True)
        self.assertFalse(json.loads(r.stdout)['automatic_collection_confirmed'])

    def test_observe_policy_is_respected_in_hook_advice(self):
        (self.root/'data/policy.json').write_text(json.dumps({'mode':'observe'}))
        r=hook(self.store,self.codex,{'hook_event_name':'UserPromptSubmit','session_id':'main'})
        self.assertIn('Observe/report only',r['hookSpecificOutput']['additionalContext'])

    def test_disabled_reporting_works_without_session_environment(self):
        (self.root/'data/policy.json').write_text(json.dumps({'report_every_message':False}))
        r=subprocess.run([sys.executable,str(SCRIPTS/'steward.py'),'--data-dir',str(self.root/'data'),
                          'report','--current','--respect-policy'],text=True,capture_output=True,check=True)
        self.assertIn('disabled',r.stdout)


# Share fixture helpers without registering all base test methods a second time.
for name in dir(AccountingTests):
    if name.startswith('test_') and name not in RegressionTests.__dict__:
        setattr(RegressionTests,name,None)
del AccountingTests


class InstallTests(unittest.TestCase):
    def test_public_installer_and_idempotent_integration(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory)/'codex space'
            install=SCRIPTS.parents[2]/'install.py'
            command=[sys.executable,str(install),'--codex-home',str(root),'--integrate']
            subprocess.run(command,check=True,capture_output=True,text=True)
            subprocess.run(command,check=True,capture_output=True,text=True)
            self.assertTrue((root/'skills/codex-token-steward/SKILL.md').exists())
            hooks=json.loads((root/'hooks.json').read_text())
            self.assertEqual(len(hooks['hooks']['Stop']),1)
            # Exercise the exact generated shell command with spaces, not only the function.
            handler=hooks['hooks']['Stop'][0]['hooks'][0]['command']
            p=subprocess.run(handler,input=json.dumps({'hook_event_name':'Stop','session_id':'test','turn_id':'test'}),
                             shell=True,text=True,capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('systemMessage',json.loads(p.stdout))
            if os.name == 'nt':
                shell=shutil.which('pwsh') or shutil.which('powershell')
                if shell:
                    text=(root/'AGENTS.md').read_text()
                    command=text.split('Windows PowerShell command:\n',1)[1].splitlines()[0]
                    env=dict(os.environ,CODEX_THREAD_ID='test')
                    result=subprocess.run([shell,'-NoProfile','-Command',command],env=env,text=True,capture_output=True)
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertIn('Usage:',result.stdout)
