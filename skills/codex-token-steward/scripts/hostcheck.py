"""Optional host lifecycle verification using a loopback canned response, never AI inference.

Uses the installed Codex app-server protocol. Never writes hook trust or user
configuration. Only explicitly trusted hooks can run. No prompt/history is saved
by this verifier, and the test session is ephemeral.
"""
import hashlib
import json
import queue
import subprocess
import tempfile
import threading
import time
from contextlib import nullcontext
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from accounting import atomic_json, now


def fingerprint(codex_home):
    h = hashlib.sha256()
    paths = [Path(codex_home) / 'hooks.json'] + sorted(Path(__file__).parent.glob('*.py'))
    for path in paths:
        h.update(path.name.encode())
        h.update(path.read_bytes() if path.exists() else b'missing')
    # Hash only relevant sections: the app routinely rewrites unrelated model,
    # project and UI settings. This is change detection, not a TOML/trust parser.
    config = Path(codex_home)/'config.toml'
    selected = []
    relevant = False
    if config.exists():
        for line in config.read_text(encoding='utf-8-sig').splitlines():
            stripped = line.strip()
            if stripped.startswith('['):
                relevant = (stripped.startswith('[hooks') or stripped.startswith('[[hooks') or
                            stripped.startswith('[features]'))
            if relevant or stripped.startswith('allow_managed_hooks_only'):
                selected.append(line.rstrip())
    h.update('\n'.join(selected).encode())
    return h.hexdigest()


def health(store, codex_home, session=None):
    counts = {r['event']:r['n'] for r in store.db.execute(
        'SELECT event,COUNT(*) n FROM hook_runs WHERE ok=1 GROUP BY event')}
    failures = [dict(r) for r in store.db.execute(
        'SELECT event,timestamp,error FROM hook_runs WHERE ok=0 ORDER BY id DESC LIMIT 3')]
    current = {r['event']:r['n'] for r in store.db.execute(
        'SELECT event,COUNT(*) n FROM hook_runs WHERE ok=1 AND session=? GROUP BY event', (session,))} if session else {}
    evidence_file = store.directory / 'host-verification.json'
    evidence = json.loads(evidence_file.read_text(encoding='utf-8')) if evidence_file.exists() else None
    fresh = bool(evidence and evidence.get('fingerprint') == fingerprint(codex_home))
    verified = bool(fresh and evidence.get('passed'))
    return {'hooks_config_exists':(Path(codex_home)/'hooks.json').exists(),
            'successful_hook_events':counts, 'recent_handler_failures':failures,
            'current_session_handler_events':current,
            'automatic_collection_confirmed':verified,
            'verification_scope':'Isolated host probe only; current desktop session activation is separate.',
            'host_verification':evidence, 'verification_matches_installed_files':fresh,
            'status':('verified_host_dispatch' if verified else
                      'handler_observed_unverified_host' if counts else 'configured_unverified'),
            'next_step':('Use prepare fallback if this task has no hook guidance; reload/start a task to load changed hooks.'
                         if verified else 'Review/trust hooks in Codex, then run verify-host --codex-exe <path>.')}


def verify(store, codex_home, executable):
    executable = Path(executable).expanduser().resolve()
    if not executable.is_file():
        raise ValueError('Codex executable not found; provide a verified absolute path')
    # Refuse to invoke a host against another home than the hooks we are checking.
    import os
    env = dict(os.environ, CODEX_HOME=str(Path(codex_home).resolve()))
    try:
        version = subprocess.run([str(executable),'--version'],capture_output=True,text=True,
                                 timeout=10,env=env,check=True).stdout.strip()
    except (OSError,subprocess.SubprocessError) as exc:
        raise ValueError('Cannot run the selected Codex executable: '+type(exc).__name__) from exc
    requests_seen = []
    fixture = 'Token Steward lifecycle fixture complete.'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            body = b'{"models":[]}'
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            # Consume, but never retain or inspect model context.
            length = int(self.headers.get('Content-Length','0'))
            if length > 32*1024*1024 or len(requests_seen) >= 1:
                self.send_error(400)
                return
            remaining = length
            while remaining:
                chunk = self.rfile.read(min(65536,remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
            requests_seen.append(self.path)
            message = {'id':'msg_fixture','type':'message','role':'assistant','status':'completed',
                       'content':[{'type':'output_text','text':fixture,'annotations':[]}]}
            events = [
                ('response.created',{'response':{'id':'resp_fixture','status':'in_progress','output':[]}}),
                ('response.output_item.added',{'output_index':0,'item':dict(message,status='in_progress',content=[])}),
                ('response.output_text.delta',{'item_id':'msg_fixture','output_index':0,'content_index':0,'delta':fixture}),
                ('response.output_item.done',{'output_index':0,'item':message}),
                ('response.completed',{'response':{'id':'resp_fixture','status':'completed','output':[message]}})]
            body = ''.join('event: '+kind+'\ndata: '+json.dumps(dict(type=kind,**data))+'\n\n'
                           for kind,data in events).encode()
            self.send_response(200)
            self.send_header('Content-Type','text/event-stream')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever,daemon=True).start()
    command = [str(executable),'app-server','--listen','stdio://',
               '-c','model_provider="steward_fixture"',
               '-c','model_providers.steward_fixture.name="Local lifecycle fixture"',
               '-c','model_providers.steward_fixture.base_url="http://127.0.0.1:%d/v1"'%server.server_port,
               '-c','model_providers.steward_fixture.wire_api="responses"',
               '-c','model_providers.steward_fixture.requires_openai_auth=false']
    process = None
    probe_cwd = Path(tempfile.mkdtemp(prefix='steward-verification-')).resolve()
    evidence = {'checked_at':now(), 'host_version':version, 'host_executable':str(executable),
                'fingerprint':fingerprint(codex_home), 'passed':False,
                'scope':'UserPromptSubmit and Stop through an ephemeral app-server session.',
                'model_inference_calls':0, 'subagent_dispatch_tested':False,
                'hook_results':[]}
    try:
        process = subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL,text=True,encoding='utf-8',env=env)
        inbox = queue.Queue()
        def reader():
            for line in process.stdout:
                try:
                    inbox.put(json.loads(line))
                except ValueError:
                    continue
            inbox.put({'transport_closed':True})
        threading.Thread(target=reader,daemon=True).start()
        deadline = time.monotonic()+40
        def receive():
            result = inbox.get(timeout=max(.01,deadline-time.monotonic()))
            if result.get('transport_closed'):
                raise ValueError('Host closed the protocol transport')
            if result.get('method')=='hook/completed':
                p = result.get('params',{})
                r = p.get('run',{})
                if r.get('statusMessage')=='codex-token-steward':
                    evidence['hook_results'].append({'event':r.get('eventName'),
                        'status':r.get('status'),'duration_ms':r.get('durationMs'),
                        'session':p.get('threadId'),'turn':p.get('turnId')})
            return result
        def request(number, method, params):
            process.stdin.write(json.dumps({'id':number,'method':method,'params':params})+'\n')
            process.stdin.flush()
            while True:
                r = receive()
                if r.get('id')==number:
                    if 'error' in r:
                        raise ValueError('Host rejected '+method)
                    return r['result']
        request(1,'initialize',{'clientInfo':{'name':'token_steward_verifier','version':'1'},
                                'capabilities':{'experimentalApi':True}})
        process.stdin.write('{"method":"initialized"}\n');process.stdin.flush()
        with nullcontext(str(probe_cwd)) as cwd:
            listing = request(2,'hooks/list',{'cwds':[cwd]})
            hooks = [h for d in listing['data'] for h in d.get('hooks',[])
                     if h.get('statusMessage')=='codex-token-steward']
            evidence['configured_hooks'] = [{'event':h['eventName'],'enabled':h['enabled'],
                                             'trust':h['trustStatus']} for h in hooks]
            if len(hooks)!=3 or any(not h['enabled'] or h['trustStatus']!='trusted' for h in hooks):
                raise ValueError('The three steward hooks must be enabled and trusted first')
            session = request(3,'thread/start',{'cwd':cwd,'ephemeral':True})['thread']['id']
            evidence['session'] = session
            request(4,'turn/start',{'threadId':session,'input':[{'type':'text','text':fixture}]})
            while True:
                item = receive()
                if item.get('method')=='turn/completed':
                    break
        observed = {r['event']:r['status'] for r in evidence['hook_results']}
        recorded = {r['event'] for r in store.db.execute(
            'SELECT event FROM hook_runs WHERE ok=1 AND session=?',(session,))}
        evidence['handler_events'] = sorted(recorded)
        evidence['passed'] = (observed.get('userPromptSubmit')=='completed' and
                              observed.get('stop')=='completed' and
                              {'UserPromptSubmit','Stop'} <= recorded)
    except (ValueError,OSError,queue.Empty,subprocess.SubprocessError) as exc:
        evidence['failure_type'] = type(exc).__name__
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=5)
        server.shutdown();server.server_close()
        # The host holds its cwd open on Windows. Clean up only after it exits;
        # rmdir deliberately removes only the empty directory we just created.
        try:
            probe_cwd.rmdir()
        except OSError:
            evidence['temporary_directory_retained'] = True
    evidence['local_fixture_requests'] = len(requests_seen)
    atomic_json(store.directory/'host-verification.json',evidence)
    return evidence
