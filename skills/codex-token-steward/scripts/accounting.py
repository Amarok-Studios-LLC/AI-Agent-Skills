"""Read-only Codex rollout adapter; only derived metadata is persisted.

No network, credentials, transcript text, tool arguments, or model requests.
The rollout schema is private: coverage warnings are part of every report.
"""
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

TOKEN_KEYS = ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def home():
    return Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')).expanduser().resolve()


def safe_id(value):
    return re.sub(r'[^a-zA-Z0-9_.:/-]', '_', str(value or 'unknown'))[:180]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + secrets.token_hex(6) + '.tmp')
    try:
        with tmp.open('w', encoding='utf-8', newline='\n') as f:
            json.dump(value, f, indent=2, ensure_ascii=True, allow_nan=False)
            f.write('\n')
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


class Store:
    def __init__(self, directory):
        self.directory = Path(directory).expanduser().resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            self.directory.chmod(0o700)
        except OSError:
            pass
        self.db = sqlite3.connect(str(self.directory / 'usage.sqlite3'), timeout=20)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY,offset INTEGER,size INTEGER,
          mtime INTEGER,head TEXT,state TEXT,errors INTEGER DEFAULT 0,pending INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,parent TEXT,born TEXT,
          project TEXT,source TEXT);
        CREATE TABLE IF NOT EXISTS turns(session TEXT,id TEXT,root TEXT,start TEXT,end TEXT,
          status TEXT DEFAULT 'observed',PRIMARY KEY(session,id));
        CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY,session TEXT,turn TEXT,root TEXT,
          timestamp TEXT,model TEXT,effort TEXT,service TEXT,input INTEGER,cached INTEGER,
          output INTEGER,reasoning INTEGER,context_window INTEGER,quality TEXT);
        CREATE INDEX IF NOT EXISTS calls_turn ON calls(session,turn);
        CREATE INDEX IF NOT EXISTS calls_time ON calls(timestamp);
        CREATE TABLE IF NOT EXISTS tools(id TEXT PRIMARY KEY,session TEXT,turn TEXT,
          timestamp TEXT,name TEXT,signature TEXT,output_bytes INTEGER DEFAULT 0,
          failed INTEGER DEFAULT 0,steward INTEGER DEFAULT 0);
        CREATE INDEX IF NOT EXISTS tools_turn ON tools(session,turn);
        CREATE TABLE IF NOT EXISTS limits(id TEXT PRIMARY KEY,timestamp TEXT,session TEXT,
          bucket TEXT,window INTEGER,reset INTEGER,used REAL);
        CREATE INDEX IF NOT EXISTS limits_session_time ON limits(session,timestamp);
        CREATE TABLE IF NOT EXISTS notes(id TEXT PRIMARY KEY,kind TEXT,project TEXT,
          timestamp TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS hook_runs(id INTEGER PRIMARY KEY,event TEXT,
          timestamp TEXT,elapsed_ms REAL,ok INTEGER);
        ''')
        # Additive migration: old handler counts remain valid, but cannot be
        # correlated with a particular host session until new observations arrive.
        self.db.execute('BEGIN IMMEDIATE')
        columns = {r[1] for r in self.db.execute('PRAGMA table_info(hook_runs)')}
        for column in ('session', 'turn', 'error'):
            if column not in columns:
                self.db.execute('ALTER TABLE hook_runs ADD COLUMN ' + column + ' TEXT')
        self.db.execute("INSERT OR IGNORE INTO kv VALUES('salt',?)", (secrets.token_hex(32),))
        self.db.execute("INSERT OR IGNORE INTO kv VALUES('schema','1')")
        self.db.commit()
        if self.get('schema') != '1':
            raise ValueError('Unsupported steward database schema; preserve it and upgrade the collector.')
        self.salt = self.get('salt').encode()

    def close(self):
        self.db.close()

    def get(self, key, default=None):
        row = self.db.execute('SELECT value FROM kv WHERE key=?', (key,)).fetchone()
        return row[0] if row else default

    def set(self, key, value):
        self.db.execute('INSERT OR REPLACE INTO kv VALUES(?,?)', (key, str(value)))

    def private_hash(self, value):
        return hmac.new(self.salt, str(value).encode('utf-8'), hashlib.sha256).hexdigest()

    def project(self, cwd):
        # Keep project paths out of reports/DB; stable within this local installation.
        return self.private_hash(os.path.normcase(os.path.abspath(cwd)))[:16] if cwd else 'unknown'

    def discover(self, codex_home, days=30):
        cutoff = time.time() - days * 86400
        paths = set()
        for subdir in ('sessions', 'archived_sessions'):
            directory = Path(codex_home) / subdir
            if directory.exists():
                for p in directory.rglob('*.jsonl'):
                    try:
                        if p.stat().st_mtime >= cutoff:
                            paths.add(p.resolve())
                    except OSError:
                        continue
        # Discovery covers historical files modified recently, including older long-lived tasks.
        return sorted(paths, key=lambda p: p.name)

    def scan(self, paths, max_bytes=None):
        started = time.monotonic()
        result = {'files': 0, 'bytes_read': 0, 'errors': 0, 'deferred': 0}
        # Serialize cursor advancement and inserts across concurrent hooks.
        self.db.execute('BEGIN IMMEDIATE')
        try:
            for path in paths:
                remaining = None if max_bytes is None else max_bytes - result['bytes_read']
                if remaining is not None and remaining <= 0:
                    result['deferred'] += 1
                    continue
                try:
                    read, errors, deferred = self._scan_file(Path(path), remaining)
                    result['files'] += 1
                    result['bytes_read'] += read
                    result['errors'] += errors
                    result['deferred'] += deferred
                except (OSError, ValueError) as exc:
                    result['errors'] += 1
                    # Exception type only: no file contents, credentials, or paths in diagnostics.
                    self.set('last_scan_error', type(exc).__name__)
            result['elapsed_ms'] = round((time.monotonic() - started) * 1000, 2)
            self.set('last_scan', json.dumps(result))
            self.set('last_scan_at', now())
            self.db.commit()
            return result
        except BaseException:
            self.db.rollback()
            raise

    def _scan_file(self, path, budget):
        stat = path.stat()
        row = self.db.execute('SELECT * FROM files WHERE path=?', (str(path.resolve()),)).fetchone()
        with path.open('rb') as f:
            head = hashlib.sha256(f.readline()).hexdigest()
            if row and stat.st_size == row['size'] and stat.st_mtime_ns == row['mtime'] and not row['pending']:
                return 0, 0, 0
            replaced = row and (stat.st_size < row['offset'] or head != row['head'] or
                                (stat.st_size == row['size'] and stat.st_mtime_ns != row['mtime']))
            state = json.loads(row['state']) if row and not replaced else {}
            offset = row['offset'] if row and not replaced else 0
            errors = row['errors'] if row and not replaced else 0
            new_errors = 0
            if replaced:
                self.set('rewritten_source_seen', 'true')
            f.seek(offset)
            read = 0
            while budget is None or read < budget:
                before = f.tell()
                line = f.readline()
                if not line:
                    break
                if not line.endswith(b'\n'):
                    f.seek(before)  # A writer may finish this line later.
                    break
                read += len(line)
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict):
                        raise ValueError('Invalid event')
                    self._event(event, state)
                except (ValueError, TypeError, KeyError, OverflowError):
                    errors += 1
                    new_errors += 1
            offset = f.tell()
        pending = int(offset < stat.st_size)
        self.db.execute('INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?,?,?)',
                        (str(path.resolve()), offset, stat.st_size, stat.st_mtime_ns, head,
                         json.dumps(state), errors, pending))
        return read, new_errors, pending

    def _turn(self, state, timestamp):
        sid = state['sid']
        turn = state.get('turn') or 'unattributed'
        root = state.get('root') or turn
        self.db.execute('INSERT OR IGNORE INTO turns(session,id,root,start) VALUES(?,?,?,?)',
                        (sid, turn, root, timestamp))
        if root not in ('unknown', 'unattributed'):
            self.db.execute('UPDATE turns SET root=? WHERE session=? AND id=?', (root, sid, turn))
        return sid, turn, root

    def _event(self, x, s):
        typ, v, timestamp = x.get('type'), x.get('payload', {}), x.get('timestamp', '')
        if not isinstance(v, dict):
            return
        if typ == 'session_meta':
            # Forks contain copied parent metadata. Only the first session header owns the file.
            if 'sid' not in s:
                sid = safe_id(v.get('id') or v.get('session_id'))
                source = v.get('source', {})
                spawn = source.get('subagent', {}).get('thread_spawn', {}) if isinstance(source, dict) else {}
                parent = v.get('parent_thread_id') or spawn.get('parent_thread_id')
                s.update(sid=sid, born=v.get('timestamp', timestamp), parent=safe_id(parent) if parent else None,
                         ordinal=v.get('subagent_history_start_ordinal'), project=self.project(v.get('cwd')))
                self.db.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?,?,?)',
                                (sid, s['parent'], s['born'], s['project'], 'subagent' if parent else 'main'))
            return
        if 'sid' not in s:
            if typ == 'event_msg' and v.get('type') == 'token_count':
                raise ValueError('Token event without session metadata')
            return
        inherited = (timestamp and timestamp < s.get('born', '')) or (
            s.get('ordinal') is not None and x.get('ordinal') is not None and x['ordinal'] < s['ordinal'])
        if inherited:
            return
        if typ == 'turn_context':
            s.update(turn=safe_id(v.get('turn_id') or s.get('turn')),
                     root=safe_id(v.get('root_turn_id') or v.get('turn_id') or s.get('turn')),
                     model=safe_id(v.get('model')), effort=safe_id(v.get('effort') or v.get('reasoning_effort')),
                     service=safe_id(v.get('service_tier')))
            self._turn(s, timestamp)
        if typ == 'event_msg':
            event = v.get('type')
            if event in ('task_started', 'task_complete', 'task_aborted'):
                if event == 'task_started':
                    s['turn'] = safe_id(v.get('turn_id') or s.get('turn'))
                    s['root'] = safe_id(v.get('root_turn_id') or s['turn'])
                sid, turn, root = self._turn(s, timestamp)
                if event != 'task_started':
                    turn = safe_id(v.get('turn_id') or turn)
                    self.db.execute('UPDATE turns SET end=?,status=? WHERE session=? AND id=?',
                                    (timestamp, 'complete' if event == 'task_complete' else 'interrupted', sid, turn))
            elif event == 'token_count':
                self._tokens(v, s, timestamp)
        if typ == 'response_item':
            sid, turn, _ = self._turn(s, timestamp)
            kind = v.get('type')
            if kind in ('function_call', 'custom_tool_call'):
                call_id = str(v.get('call_id') or v.get('id') or digest([timestamp, v]))
                name = safe_id((str(v.get('namespace')) + '.' if v.get('namespace') else '') + str(v.get('name', 'unknown')))
                args = v.get('arguments', v.get('input', ''))
                args_str = args if isinstance(args, str) else json.dumps(args, sort_keys=True)
                signature = self.private_hash(name + '\n' + args_str)
                self.db.execute('INSERT OR IGNORE INTO tools(id,session,turn,timestamp,name,signature,steward) VALUES(?,?,?,?,?,?,?)',
                                (self.private_hash(sid + call_id), sid, turn, timestamp, name, signature,
                                 int('steward.py' in args_str or 'codex-token-steward' in args_str)))
            elif kind in ('function_call_output', 'custom_tool_call_output'):
                out = v.get('output', '')
                text = out if isinstance(out, str) else json.dumps(out)
                failed = bool(isinstance(out, dict) and (out.get('isError') or
                              (isinstance(out.get('exit_code'), int) and out['exit_code'] != 0)))
                # Conservative exact exit-code markers; don't infer errors from arbitrary prose.
                failed = failed or bool(re.search(r'"exit_code"\s*:\s*-[1-9]|"exit_code"\s*:\s*[1-9]', text))
                self.db.execute('UPDATE tools SET output_bytes=?,failed=? WHERE id=?',
                                (len(text.encode('utf-8')), int(failed), self.private_hash(sid + str(v.get('call_id')))))

    def _tokens(self, v, s, timestamp):
        rates = v.get('rate_limits') or {}
        if isinstance(rates, dict):
            for bucket in ('primary', 'secondary'):
                r = rates.get(bucket)
                if (isinstance(r, dict) and isinstance(r.get('used_percent'), (int, float)) and
                        math.isfinite(r['used_percent']) and 0 <= r['used_percent'] <= 100):
                    self.db.execute('INSERT OR IGNORE INTO limits VALUES(?,?,?,?,?,?,?)',
                                    (digest([timestamp, rates.get('limit_id'), bucket, r]), timestamp, s['sid'],
                                     safe_id(rates.get('limit_id', 'codex')) + ':' + bucket,
                                     r.get('window_minutes'), r.get('resets_at'), r['used_percent']))
        info = v.get('info') or {}
        total, last = info.get('total_token_usage'), info.get('last_token_usage')
        if not isinstance(total, dict):
            if last:
                self.set('unsupported_last_only', 'true')
            return
        if total == s.get('total'):
            return  # Rate-only / duplicate accounting update.
        previous = s.get('total')
        s['total'] = total
        quality = 'reported_last_call'
        if isinstance(last, dict):
            usage = last
            if previous:
                delta = {k:total.get(k,0)-previous.get(k,0) for k in TOKEN_KEYS}
                if all(n>=0 for n in delta.values()) and any(delta[k]>last.get(k,0) for k in ('input_tokens','output_tokens')):
                    self.set('counter_gaps', 'true')
        elif previous and all(total.get(k, 0) >= previous.get(k, 0) for k in TOKEN_KEYS):
            usage = {k: total.get(k, 0) - previous.get(k, 0) for k in TOKEN_KEYS}
            quality = 'aggregate_delta_not_exact_call'
        else:
            self.set('unattributed_initial_totals', 'true')
            return  # Never label an inherited session total as one new call.
        values = [usage.get(k, 0) for k in TOKEN_KEYS]
        if any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in values):
            raise ValueError('Invalid token counters')
        i, c, o, r = values
        if c > i or r > o:
            raise ValueError('Invalid token subsets')
        sid, turn, root = self._turn(s, timestamp)
        # Same event copied into another transcript must not count twice.
        identity = digest([sid, timestamp, total, last])
        self.db.execute('INSERT OR IGNORE INTO calls VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (identity, sid, turn, root, timestamp, s.get('model', 'unknown'),
                         s.get('effort', 'unknown'), s.get('service', 'unknown'), i, c, o, r,
                         info.get('model_context_window'), quality))
