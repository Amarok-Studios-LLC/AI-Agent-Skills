"""Exercise portable records and opt-in global installation with real files/CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / 'skills/software-engineering-toolkit/scripts/toolkit.py'


class ToolkitRecordsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / 'project'
        self.project.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def run_tool(self, *args, content=None, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.project), *args],
                                input=content, text=True, encoding='utf-8', capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("can't open file", result.stderr)
        return result

    def publish(self, path, content, expected=None):
        args = ['publish', '--path', path, '--actor', 'developer', '--reason', 'Confirmed project change']
        if expected:
            args += ['--expected', expected]
        return self.run_tool(*args, content=content)

    def test_new_project_context_contains_only_supplied_identity_and_explicit_empty_records(self):
        result = self.run_tool('init', '--name', 'Example Game', '--actor', 'developer')
        context = json.loads((self.project / '.engineering/context.json').read_text())
        self.assertEqual(context['project']['name'], 'Example Game')
        for key in ('completed', 'in_progress', 'constraints', 'decisions', 'open_questions'):
            self.assertEqual(context[key], [])
        self.assertIsNotNone(context['updated_at'])
        self.assertEqual(result['initialized'], True)
        self.assertFalse((self.project / '.engineering/documents/privacy-policy.md').exists())

    def test_reinitialization_does_not_replace_project_identity(self):
        self.run_tool('init', '--name', 'First', '--actor', 'developer')
        self.run_tool('init', '--name', 'Second', '--actor', 'developer', ok=False)
        self.assertEqual(json.loads((self.project / '.engineering/context.json').read_text())['project']['name'], 'First')

    def test_updates_keep_old_content_and_reject_stale_expected_digest(self):
        first = self.publish('docs/product.md', 'First approved scope\n')
        second = self.publish('docs/product.md', 'Second approved scope\n', first['sha256'])
        self.publish_failure('docs/product.md', 'Stale overwrite', first['sha256'])
        self.assertEqual((self.project / 'docs/product.md').read_text(), 'Second approved scope\n')
        records = [json.loads(p.read_text()) for p in (self.project / '.engineering/history').rglob('*.json')]
        self.assertEqual({r['content'] for r in records}, {'First approved scope\n', 'Second approved scope\n'})
        self.assertEqual(second['version'], 2)
        self.assertEqual(records[0]['actor'], 'developer')
        self.assertTrue(all(r['reason'] and r['timestamp'] for r in records))

    def publish_failure(self, path, content, expected=None):
        args = ['publish', '--path', path, '--actor', 'developer', '--reason', 'Update']
        if expected:
            args += ['--expected', expected]
        return self.run_tool(*args, content=content, ok=False)

    def test_identical_content_does_not_create_another_revision(self):
        first = self.publish('docs/product.md', 'Stable\n')
        result = self.publish('docs/product.md', 'Stable\n', first['sha256'])
        self.assertFalse(result['changed'])
        self.assertEqual(len(list((self.project / '.engineering/history').rglob('*.json'))), 1)

    def test_external_edits_must_be_archived_before_overwriting(self):
        first = self.publish('docs/product.md', 'Original\n')
        (self.project / 'docs/product.md').write_bytes(b'Collaborator edit\n')
        self.publish_failure('docs/product.md', 'Overwrite\n', first['sha256'])
        review = self.run_tool('review')
        self.assertIn('docs/product.md', review['changed'])
        tracked = self.run_tool('track', '--path', 'docs/product.md', '--actor', 'collaborator', '--reason', 'Import external edit')
        self.publish('docs/product.md', 'Reconciled\n', tracked['sha256'])
        bodies = {json.loads(p.read_text())['content'] for p in (self.project / '.engineering/history').rglob('*.json')}
        self.assertEqual(bodies, {'Original\n', 'Collaborator edit\n', 'Reconciled\n'})

    def test_existing_untracked_document_is_preserved_until_explicit_adoption(self):
        existing = self.project / 'README.md'
        existing.write_text('Existing documentation\n')
        self.publish_failure('README.md', 'Replacement')
        self.assertEqual(existing.read_text(), 'Existing documentation\n')
        review = self.run_tool('review')
        self.assertIn('README.md', review['untracked_documents'])
        self.run_tool('track', '--path', 'README.md', '--actor', 'developer', '--reason', 'Adopt existing documentation')
        self.assertEqual(existing.read_text(), 'Existing documentation\n')

    def test_review_reports_missing_records_and_merge_conflicts_without_repairing_them(self):
        self.publish('docs/a.md', 'Approved')
        self.publish('docs/b.md', '<<<<<<< ours\nA\n=======\nB\n>>>>>>> theirs\n')
        (self.project / 'docs/a.md').unlink()
        review = self.run_tool('review')
        self.assertIn('docs/a.md', review['missing'])
        self.assertIn('docs/b.md', review['merge_conflicts'])
        self.assertFalse((self.project / 'docs/a.md').exists())
        self.assertTrue(review['semantic_review_required'])

    def test_traversal_and_history_overwrites_are_rejected(self):
        for path in ('../outside.md', '.engineering/manifest.json', '.engineering/history/overwrite.json'):
            with self.subTest(path=path):
                self.publish_failure(path, 'bad')
        self.assertFalse((self.project.parent / 'outside.md').exists())

    def test_symlink_destination_is_not_followed(self):
        outside = self.project.parent / 'outside'
        outside.mkdir()
        try:
            (self.project / 'docs').symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('Host cannot create symlinks')
        self.publish_failure('docs/product.md', 'bad')
        self.assertFalse((outside / 'product.md').exists())

    def test_active_lock_prevents_concurrent_writes(self):
        directory = self.project / '.engineering'
        directory.mkdir()
        (directory / '.lock').write_text('another writer')
        self.publish_failure('docs/product.md', 'bad')
        self.assertEqual((directory / '.lock').read_text(), 'another writer')
        self.assertFalse((self.project / 'docs/product.md').exists())

    def decision(self, identifier, value, supersedes=None):
        payload = {'id': identifier, 'title': 'Cookie use', 'decision': 'Confirmed cookie setting',
                   'rationale': 'Developer confirmed actual behavior', 'source': 'Developer confirmation',
                   'claims': {'uses_cookies': value}, 'supersedes': supersedes or []}
        return self.run_tool('decide', '--actor', 'developer', content=json.dumps(payload))

    def test_conflicting_decisions_are_surfaced_without_newest_wins(self):
        self.decision('D-001', False)
        self.decision('D-002', True)
        review = self.run_tool('review')
        self.assertEqual(review['decision_conflicts'][0]['key'], 'uses_cookies')
        self.assertEqual(set(review['decision_conflicts'][0]['decisions']), {'D-001', 'D-002'})

    def test_explicit_supersession_resolves_conflict_and_retains_prior_decisions(self):
        self.decision('D-001', False)
        self.decision('D-002', True, ['D-001'])
        self.assertEqual(self.run_tool('review')['decision_conflicts'], [])
        decisions = json.loads((self.project / '.engineering/knowledge/decisions.json').read_text())['decisions']
        self.assertEqual([d['id'] for d in decisions], ['D-001', 'D-002'])
        self.assertFalse(decisions[0]['claims']['uses_cookies'])
        self.assertTrue(all(d['timestamp'] and d['actor'] and d['rationale'] for d in decisions))
        self.run_tool('decide', '--actor', 'developer', content=json.dumps(decisions[0]), ok=False)

    def test_unknown_supersession_target_and_missing_rationale_do_not_change_ledger(self):
        self.decision('D-001', False)
        target = self.project / '.engineering/knowledge/decisions.json'
        before = target.read_bytes()
        payload = {'id': 'D-002', 'title': 'X', 'decision': 'X', 'rationale': 'X', 'source': 'Developer', 'supersedes': ['D-404']}
        self.run_tool('decide', '--actor', 'developer', content=json.dumps(payload), ok=False)
        payload['supersedes'] = []
        payload['rationale'] = ''
        self.run_tool('decide', '--actor', 'developer', content=json.dumps(payload), ok=False)
        self.assertEqual(target.read_bytes(), before)

    def test_records_remain_readable_after_project_move_without_absolute_path_dependencies(self):
        self.run_tool('init', '--name', 'Portable', '--actor', 'developer')
        self.decision('D-001', False)
        moved = self.project.with_name('moved')
        self.project.rename(moved)
        self.project = moved
        review = self.run_tool('review')
        self.assertEqual(review['missing'], [])
        self.assertEqual(review['changed'], [])
        self.assertEqual(review['decision_conflicts'], [])
        manifest = (moved / '.engineering/manifest.json').read_text()
        self.assertNotIn(str(Path(self.temp.name)), manifest)

    def test_unicode_content_round_trips_without_encoding_changes(self):
        first = self.publish('docs/product.md', 'Caf\u00e9 \u2014 \u65e5\u672c\u8a9e\n')
        self.assertEqual((self.project / 'docs/product.md').read_text(encoding='utf-8'), 'Caf\u00e9 \u2014 \u65e5\u672c\u8a9e\n')
        self.assertEqual(self.run_tool('review')['changed'], [])
        self.assertTrue(first['sha256'])

    def test_generic_publish_cannot_erase_decision_history(self):
        self.decision('D-001', False)
        path = '.engineering/knowledge/decisions.json'
        review = self.run_tool('review')
        manifest = json.loads((self.project / '.engineering/manifest.json').read_text())
        self.publish_failure(path, '{"schema_version": 1, "decisions": []}', manifest['documents'][path]['sha256'])
        self.assertEqual(self.run_tool('review')['registered'], review['registered'])
        ledger = json.loads((self.project / path).read_text())
        self.assertEqual([entry['id'] for entry in ledger['decisions']], ['D-001'])

    def test_missing_prior_snapshot_blocks_replacement(self):
        first = self.publish('docs/product.md', 'Original\n')
        (self.project / first['snapshot']).unlink()
        self.publish_failure('docs/product.md', 'Replacement\n', first['sha256'])
        self.assertEqual((self.project / 'docs/product.md').read_text(), 'Original\n')
        self.assertEqual(self.run_tool('review')['history_errors'], [first['snapshot']])

    def test_malformed_appended_decision_is_rejected_before_writing(self):
        self.decision('D-001', False)
        path = '.engineering/knowledge/decisions.json'
        target = self.project / path
        before = target.read_bytes()
        ledger = json.loads(before)
        ledger['decisions'].append({'id': 'D-002'})
        manifest = json.loads((self.project / '.engineering/manifest.json').read_text())
        self.publish_failure(path, json.dumps(ledger), manifest['documents'][path]['sha256'])
        self.assertEqual(target.read_bytes(), before)

    def test_reserved_metadata_cannot_be_tracked_using_different_capitalization(self):
        self.run_tool('init', '--name', 'Example', '--actor', 'developer')
        self.run_tool('track', '--path', '.engineering/MANIFEST.json', '--actor', 'developer', '--reason', 'Invalid alias', ok=False)

    def test_supplied_decision_datetime_is_preserved_separately_from_recording_time(self):
        payload = {'id': 'D-001', 'title': 'Scope', 'decision': 'Approved first release',
                   'rationale': 'Confirmed developer scope', 'source': 'Prior developer decision',
                   'timestamp': '2025-04-10T09:30:00-05:00'}
        self.run_tool('decide', '--actor', 'developer', content=json.dumps(payload))
        entry = json.loads((self.project / '.engineering/knowledge/decisions.json').read_text())['decisions'][0]
        self.assertEqual(entry['timestamp'], '2025-04-10T09:30:00-05:00')
        self.assertNotEqual(entry['recorded_at'], entry['timestamp'])


class ToolkitInstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / 'codex home'
        self.home.mkdir()
        self.agents = self.home / 'AGENTS.md'
        self.agents.write_text('# Existing user rules\nKeep existing settings.\n')

    def tearDown(self):
        self.temp.cleanup()

    def install(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(REPO / 'install.py'), '--skill', 'software-engineering-toolkit',
                                 '--codex-home', str(self.home), *args], text=True, encoding='utf-8', capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def test_plain_install_does_not_modify_global_instructions_or_hooks(self):
        self.install()
        self.assertTrue((self.home / 'skills/software-engineering-toolkit/SKILL.md').is_file())
        self.assertEqual(self.agents.read_text(), '# Existing user rules\nKeep existing settings.\n')
        self.assertFalse((self.home / 'hooks.json').exists())

    def test_integration_is_idempotent_preserves_other_rules_and_can_remove_its_own_block(self):
        original = self.agents.read_bytes()
        hooks = self.home / 'hooks.json'
        hooks.write_text('{"hooks": {"Stop": []}}')
        config = self.home / 'config.toml'
        config.write_text('model = "existing-model"\n')
        self.install('--integrate')
        first = self.agents.read_bytes()
        backups = list((self.home / 'skill-integrations/software-engineering-toolkit').rglob('*.md'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.install('--integrate')
        self.assertEqual(self.agents.read_bytes(), first)
        self.assertEqual(len(list((self.home / 'skill-integrations/software-engineering-toolkit').rglob('*.md'))), 1)
        installed = self.home / 'skills/software-engineering-toolkit/scripts/toolkit.py'
        result = subprocess.run([sys.executable, str(installed), '--codex-home', str(self.home), 'remove-integration'],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.agents.read_bytes(), original)
        self.assertEqual(hooks.read_text(), '{"hooks": {"Stop": []}}')
        self.assertEqual(config.read_text(), 'model = "existing-model"\n')

    def test_different_existing_installation_requires_upgrade(self):
        self.install()
        target = self.home / 'skills/software-engineering-toolkit/SKILL.md'
        target.write_text(target.read_text(encoding='utf-8') + '\nLocal customization\n', encoding='utf-8')
        self.install(ok=False)
        self.assertIn('Local customization', target.read_text(encoding='utf-8'))
        self.install('--upgrade')
        self.assertNotIn('Local customization', target.read_text(encoding='utf-8'))

    def test_removal_preserves_unicode_bom_and_original_missing_final_newline(self):
        original = b'\xef\xbb\xbf' + '# Rules: caf\u00e9'.encode('utf-8')
        self.agents.write_bytes(original)
        self.install('--integrate')
        installed = self.home / 'skills/software-engineering-toolkit/scripts/toolkit.py'
        result = subprocess.run([sys.executable, str(installed), '--codex-home', str(self.home), 'remove-integration'],
                                text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.agents.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
