import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/codex-token-steward/scripts'))
from accounting import Store, atomic_json
from hostcheck import fingerprint, health
from integration import hook, hook_command_for, install_integration, powershell_invocation

SCRIPT = Path(__file__).resolve().parents[1]/'skills/codex-token-steward/scripts/steward.py'


class IntegrationHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.codex = self.root/'codex'
        self.codex.mkdir()
        self.store = Store(self.root/'data')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_prepare_does_not_masquerade_as_automatic_hook(self):
        hook(self.store,self.codex,{'hook_event_name':'UserPromptSubmit','session_id':'s'},record=False)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM hook_runs').fetchone()[0],0)
        self.assertFalse(health(self.store,self.codex)['automatic_collection_confirmed'])

    def test_handler_observation_scoped_to_session(self):
        hook(self.store,self.codex,{'hook_event_name':'Stop','session_id':'s','turn_id':'t'})
        self.assertEqual(health(self.store,self.codex,'s')['current_session_handler_events'],{'Stop':1})
        self.assertEqual(health(self.store,self.codex,'other')['current_session_handler_events'],{})
        self.assertFalse(health(self.store,self.codex,'s')['automatic_collection_confirmed'])

    def test_changed_installation_invalidates_host_evidence(self):
        evidence = {'passed':True,'fingerprint':fingerprint(self.codex)}
        atomic_json(self.store.directory/'host-verification.json',evidence)
        self.assertTrue(health(self.store,self.codex)['automatic_collection_confirmed'])
        (self.codex/'hooks.json').write_text('{}')
        self.assertFalse(health(self.store,self.codex)['automatic_collection_confirmed'])

    def test_unrelated_config_changes_do_not_invalidate_hook_evidence(self):
        config = self.codex/'config.toml'
        config.write_text('model="a"\n[hooks.state.one]\ntrusted_hash="first"\n')
        first = fingerprint(self.codex)
        config.write_text('model="b"\n[hooks.state.one]\ntrusted_hash="first"\n')
        self.assertEqual(fingerprint(self.codex),first)
        config.write_text('model="b"\n[hooks.state.one]\ntrusted_hash="second"\n')
        self.assertNotEqual(fingerprint(self.codex),first)

    def test_invalid_hook_input_is_visible_without_blocking(self):
        result = subprocess.run([sys.executable,str(SCRIPT),'--data-dir',str(self.store.directory),'hook'],
                                input='not json',text=True,capture_output=True,check=True)
        self.assertIn('coverage unavailable',json.loads(result.stdout)['systemMessage'])
        self.assertEqual(health(self.store,self.codex)['recent_handler_failures'][0]['error'],'JSONDecodeError')

    def test_only_prompt_hook_has_context_limit(self):
        install_integration(self.codex,SCRIPT,self.store)
        hooks = json.loads((self.codex/'hooks.json').read_text())['hooks']
        self.assertIn('additionalContextLimit',hooks['UserPromptSubmit'][0]['hooks'][0])
        for event in ('Stop','SubagentStop'):
            self.assertNotIn('additionalContextLimit',hooks[event][0]['hooks'][0])

    @unittest.skipUnless(os.name=='nt','Windows shell compatibility')
    def test_hook_command_runs_in_both_windows_shells_with_literal_paths(self):
        target = self.root/"space ' & $ % ! (folder)"/'echo.py'
        target.parent.mkdir()
        target.write_text('import json,sys; print(json.dumps({"argument":sys.argv[1],"stdin":json.load(sys.stdin)}))')
        argument = "literal ' $ & % ! value"
        command = hook_command_for(target,[argument])
        payload = {'message':'do not expand $anything %anything%'}
        invocations = [(command,True)]
        for shell in ('powershell.exe','pwsh'):
            if shutil.which(shell):
                invocations.append(([shell,'-NoProfile','-NonInteractive','-Command',command],False))
                invocations.append(([shell,'-NoProfile','-NonInteractive','-Command',
                                     powershell_invocation(target,[argument])],False))
        for cmd,use_shell in invocations:
            with self.subTest(shell=str(cmd)[:80]):
                result = subprocess.run(cmd,shell=use_shell,input=json.dumps(payload),
                                        text=True,capture_output=True,check=True)
                self.assertEqual(json.loads(result.stdout),{'argument':argument,'stdin':payload})

    def test_status_command_needs_no_session(self):
        result = subprocess.run([sys.executable,str(SCRIPT),'--codex-home',str(self.codex),
                                 '--data-dir',str(self.store.directory),'status'],
                                text=True,capture_output=True,check=True)
        output = json.loads(result.stdout)
        self.assertEqual(output['usage']['model_calls'],0)
        self.assertEqual(output['health']['status'],'configured_unverified')


if __name__=='__main__':
    unittest.main()
