"""Portable UTF-8 project records. No network, model calls, or automatic deletion."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import uuid


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def digest(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + '\n'


def validate_ledger(ledger):
    if not isinstance(ledger, dict) or ledger.get('schema_version') != 1 or not isinstance(ledger.get('decisions'), list):
        raise ValueError('Unsupported decision ledger')
    identifiers = set()
    for entry in ledger['decisions']:
        if not isinstance(entry, dict):
            raise ValueError('Each decision must be an object')
        for key in ('id', 'title', 'decision', 'rationale', 'source', 'timestamp', 'actor'):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ValueError('Decision requires nonempty ' + key)
        if entry['id'] in identifiers or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', entry['id']):
            raise ValueError('Decision identifiers must be valid and unique')
        for key in ('timestamp', 'recorded_at'):
            if key in entry and datetime.fromisoformat(entry[key].replace('Z', '+00:00')).utcoffset() is None:
                raise ValueError('Decision datetimes require an explicit timezone offset')
        supersedes = entry.get('supersedes', [])
        if not isinstance(entry.get('claims', {}), dict) or not isinstance(supersedes, list) or not all(isinstance(x, str) for x in supersedes):
            raise ValueError('claims must be an object and supersedes a list of identifiers')
        if not set(supersedes) <= identifiers:
            raise ValueError('Supersession must reference earlier existing decisions')
        identifiers.add(entry['id'])


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.toolkit-', dir=str(path.parent))
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Records:
    def __init__(self, project):
        self.project = Path(project).expanduser().resolve()
        if not self.project.is_dir():
            raise ValueError('Project directory must already exist')
        self.directory = self.project / '.engineering'

    def safe_path(self, relative, reserved=False):
        if not isinstance(relative, str) or not relative:
            raise ValueError('A project-relative path is required')
        if '\\' in relative or ':' in relative:
            raise ValueError('Use portable relative paths with forward slashes')
        parts = PurePosixPath(relative).parts
        if not parts or relative.startswith('/') or any(p in ('', '.', '..') for p in relative.split('/')):
            raise ValueError('Path must stay inside the project')
        folded = relative.casefold()
        if parts[0].casefold() == '.engineering' and parts[0] != '.engineering':
            raise ValueError('Use canonical .engineering record paths')
        if folded == '.engineering/knowledge/decisions.json' and relative != '.engineering/knowledge/decisions.json':
            raise ValueError('Use the canonical decision ledger path')
        if not reserved and (folded in ('.engineering/manifest.json', '.engineering/.lock') or
                             folded.startswith('.engineering/history/')):
            raise ValueError('Reserved record metadata cannot be published')
        target = self.project.joinpath(*parts)
        current = self.project
        for part in parts:
            current = current / part
            if current.is_symlink():
                raise ValueError('Record paths cannot traverse symlinks')
        if self.project not in target.resolve().parents:
            raise ValueError('Path escapes the project')
        return target

    def read(self, path):
        return path.read_bytes().decode('utf-8')

    def manifest(self):
        path = self.safe_path('.engineering/manifest.json', reserved=True)
        if not path.exists():
            return {'schema_version': 1, 'documents': {}}
        data = json.loads(self.read(path))
        if data.get('schema_version') != 1 or not isinstance(data.get('documents'), dict):
            raise ValueError('Unsupported record manifest; preserve it and inspect manually')
        return data

    @contextmanager
    def locked(self):
        lock = self.safe_path('.engineering/.lock', reserved=True)
        lock.parent.mkdir(parents=True, exist_ok=True)
        try:
            stream = lock.open('x', encoding='utf-8')
        except FileExistsError:
            raise ValueError('Another writer or interrupted operation owns .engineering/.lock; inspect before recovery')
        try:
            with stream:
                stream.write(encoded({'pid': os.getpid(), 'timestamp': timestamp()}))
            yield
        finally:
            lock.unlink()

    def _publish(self, relative, content, actor, reason, expected=None, adopting=False):
        if not isinstance(content, str) or not actor.strip() or not reason.strip():
            raise ValueError('Content, actor, and a nonempty change reason are required')
        target = self.safe_path(relative)
        if target.suffix.lower() not in ('.md', '.json', '.txt', '.rst', '.yaml', '.yml'):
            raise ValueError('Helper supports UTF-8 documentation/records, not executable or binary files')
        manifest = self.manifest()
        if any(key.casefold() == relative.casefold() and key != relative for key in manifest['documents']):
            raise ValueError('Use the registered path spelling; case aliases are not portable')
        previous = manifest['documents'].get(relative)
        existing = self.read(target) if target.is_file() else None
        prior_snapshot = None
        if previous:
            snapshot_path = self.safe_path(previous['snapshot'], reserved=True)
            if not snapshot_path.is_file():
                raise ValueError('Prior snapshot is missing; recover history before replacing current content')
            prior_snapshot = json.loads(self.read(snapshot_path))
            if digest(prior_snapshot['content']) != previous['sha256']:
                raise ValueError('Prior snapshot integrity failed; inspect history before replacing current content')
        if relative == '.engineering/knowledge/decisions.json':
            ledger = json.loads(content)
            validate_ledger(ledger)
            if prior_snapshot:
                old_entries = json.loads(prior_snapshot['content'])['decisions']
                if ledger['decisions'][:len(old_entries)] != old_entries:
                    raise ValueError('Existing decisions are immutable; append an explicit superseding decision')
        if previous and not adopting:
            if existing is None or digest(existing) != previous['sha256']:
                raise ValueError('Current file differs from its recorded revision; track external edits or resolve missing content first')
            if expected != previous['sha256']:
                raise ValueError('Expected digest is stale or missing; review current records before updating')
        elif not previous and existing is not None and not adopting:
            raise ValueError('Existing document is untracked; track its original content before replacing it')
        elif not previous and expected is not None and not adopting:
            raise ValueError('Expected an existing revision, but document is untracked')
        sha = digest(content)
        if previous and previous['sha256'] == sha:
            return dict(previous, path=relative, changed=False)
        version = previous['version'] + 1 if previous else 1
        key = hashlib.sha256(relative.encode('utf-8')).hexdigest()
        archive = '.engineering/history/' + key + '/%06d-%s.json' % (version, uuid.uuid4().hex)
        snapshot = {'schema_version': 1, 'path': relative, 'version': version, 'timestamp': timestamp(),
                    'actor': actor, 'reason': reason, 'sha256': sha, 'content': content,
                    'previous_snapshot': previous['snapshot'] if previous else None}
        archive_path = self.safe_path(archive, reserved=True)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with archive_path.open('x', encoding='utf-8', newline='') as stream:
            stream.write(encoded(snapshot))
            stream.flush()
            os.fsync(stream.fileno())
        # Archive first. An interrupted later write leaves evidence rather than deleting history.
        if not adopting:
            atomic_write(target, content)
        record = {k: snapshot[k] for k in ('version', 'timestamp', 'actor', 'reason', 'sha256')}
        record['snapshot'] = archive
        manifest['documents'][relative] = record
        atomic_write(self.safe_path('.engineering/manifest.json', reserved=True), encoded(manifest))
        return dict(record, path=relative, changed=True)

    def publish(self, relative, content, actor, reason, expected=None):
        with self.locked():
            return self._publish(relative, content, actor, reason, expected)

    def track(self, relative, actor, reason):
        with self.locked():
            target = self.safe_path(relative)
            if not target.is_file():
                raise ValueError('Only existing files can be tracked')
            return self._publish(relative, self.read(target), actor, reason, adopting=True)

    def initialize(self, name, actor):
        if not name.strip() or not actor.strip():
            raise ValueError('Confirmed project name and actor are required')
        with self.locked():
            context_path = '.engineering/context.json'
            decisions_path = '.engineering/knowledge/decisions.json'
            if self.safe_path(context_path).exists() or self.safe_path(decisions_path).exists():
                raise ValueError('Project records already exist; read and reconcile them instead of reinitializing')
            context = {'schema_version': 1, 'project': {'name': name}, 'updated_at': timestamp(),
                       'completed': [], 'in_progress': [], 'constraints': [], 'decisions': [],
                       'open_questions': [], 'documents': [], 'verification': [], 'next_steps': []}
            self._publish(context_path, encoded(context), actor, 'Initialize confirmed project identity')
            self._publish(decisions_path, encoded({'schema_version': 1, 'decisions': []}), actor,
                          'Initialize append-only decision ledger')
            return {'initialized': True, 'context': context_path, 'decisions': decisions_path}

    def decide(self, payload, actor):
        if not isinstance(payload, dict):
            raise ValueError('Decision input must be a JSON object')
        for key in ('id', 'title', 'decision', 'rationale', 'source'):
            if not isinstance(payload.get(key), str) or not payload[key].strip():
                raise ValueError('Decision requires nonempty ' + key)
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', payload['id']):
            raise ValueError('Use a portable decision identifier')
        claims = payload.get('claims', {})
        supersedes = payload.get('supersedes', [])
        if not isinstance(claims, dict) or not isinstance(supersedes, list) or not all(isinstance(x, str) for x in supersedes):
            raise ValueError('claims must be an object and supersedes a list of decision identifiers')
        with self.locked():
            relative = '.engineering/knowledge/decisions.json'
            target = self.safe_path(relative)
            ledger = json.loads(self.read(target)) if target.exists() else {'schema_version': 1, 'decisions': []}
            entries = ledger['decisions']
            identifiers = {d['id'] for d in entries}
            if payload['id'] in identifiers:
                raise ValueError('Decision identifiers are immutable; add a new decision instead')
            if not set(supersedes) <= identifiers:
                raise ValueError('Supersession must reference existing decisions')
            entry = {k: payload[k] for k in ('id', 'title', 'decision', 'rationale', 'source')}
            recorded = timestamp()
            entry.update({'timestamp': payload.get('timestamp', recorded), 'recorded_at': recorded,
                          'actor': actor, 'claims': claims, 'supersedes': supersedes})
            entries.append(entry)
            previous = self.manifest()['documents'].get(relative)
            result = self._publish(relative, encoded(ledger), actor, 'Record decision ' + payload['id'],
                                   previous['sha256'] if previous else None)
            return dict(result, decision_id=payload['id'])

    def review(self, verify_history=False):
        manifest = self.manifest()
        result = {'schema_version': 1, 'reviewed_at': timestamp(), 'registered': sorted(manifest['documents']),
                  'changed': [], 'missing': [], 'merge_conflicts': [], 'history_errors': [],
                  'decision_conflicts': [], 'untracked_documents': [], 'semantic_review_required': True,
                  'note': 'Hashes and explicit decision claims assist review; an agent must reconcile meaning across all project documents.'}
        for relative, record in manifest['documents'].items():
            path = self.safe_path(relative)
            if not path.is_file():
                result['missing'].append(relative)
            else:
                content = self.read(path)
                if digest(content) != record['sha256']:
                    result['changed'].append(relative)
                if re.search(r'^(<<<<<<<|=======|>>>>>>>)', content, re.MULTILINE):
                    result['merge_conflicts'].append(relative)
            snapshot = self.safe_path(record['snapshot'], reserved=True)
            if not snapshot.is_file():
                result['history_errors'].append(record['snapshot'])
        if verify_history:
            history = self.safe_path('.engineering/history', reserved=True)
            if history.exists():
                for path in sorted(history.rglob('*.json')):
                    relative = path.relative_to(self.project).as_posix()
                    self.safe_path(relative, reserved=True)
                    try:
                        entry = json.loads(self.read(path))
                        if digest(entry['content']) != entry['sha256']:
                            result['history_errors'].append(relative)
                    except (ValueError, KeyError):
                        result['history_errors'].append(relative)
        candidates = list(self.project.glob('*.md'))
        for directory in ('docs', 'documentation', '.engineering/documents', '.engineering/knowledge'):
            base = self.safe_path(directory)
            if base.exists():
                candidates.extend(base.rglob('*.md'))
        for path in sorted(set(candidates)):
            relative = path.relative_to(self.project).as_posix()
            self.safe_path(relative)
            if path.is_file() and relative not in manifest['documents']:
                result['untracked_documents'].append(relative)
        ledger = self.safe_path('.engineering/knowledge/decisions.json')
        if ledger.exists():
            entries = json.loads(self.read(ledger))['decisions']
            superseded = {identifier for entry in entries for identifier in entry.get('supersedes', [])}
            claims = {}
            for entry in entries:
                if entry['id'] not in superseded:
                    for key, value in entry.get('claims', {}).items():
                        claims.setdefault(key, []).append((entry['id'], value))
            for key, values in sorted(claims.items()):
                if len({json.dumps(value, sort_keys=True) for _, value in values}) > 1:
                    result['decision_conflicts'].append({'key': key, 'decisions': [identifier for identifier, _ in values],
                                                        'values': [value for _, value in values]})
        return result
