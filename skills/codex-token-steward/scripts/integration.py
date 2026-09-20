"""Opt-in host integration. Never changes hook trust or starts model turns."""
import json
import base64
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

from accounting import atomic_json, now
from reports import compact, policy, save_report, turn_report

MARKER = 'codex-token-steward'
BEGIN = '<!-- codex-token-steward:start -->'
END = '<!-- codex-token-steward:end -->'


def session_paths(codex_home, session=None):
    paths = []
    for part in ('sessions', 'archived_sessions'):
        base = Path(codex_home) / part
        if base.exists():
            paths.extend(base.rglob('*.jsonl'))
    if session is None:
        return sorted(paths)
    # Read only the first metadata record; no state database or transcript search needed.
    headers = []
    for path in paths:
        try:
            with path.open('rb') as f:
                first = json.loads(f.readline(2 * 1024 * 1024))
            v = first.get('payload', {})
            sid = v.get('id') or v.get('session_id')
            source = v.get('source')
            parent = v.get('parent_thread_id')
            if not parent and isinstance(source, dict):
                parent = source.get('subagent', {}).get('thread_spawn', {}).get('parent_thread_id')
            headers.append((path, sid, parent))
        except (OSError, ValueError, AttributeError):
            continue
    selected = {session}
    while True:
        more = {sid for _, sid, parent in headers if parent in selected and sid}
        if more <= selected:
            break
        selected.update(more)
    return sorted((p for p,sid,_ in headers if sid in selected), key=lambda p:p.name)


def hook(store, codex_home, payload, record=True):
    started = time.monotonic()
    event = payload.get('hook_event_name', '')
    sid = payload.get('session_id')
    if not isinstance(sid, str) or not sid:
        raise ValueError('Hook event requires session_id')
    p = policy(store)
    if event not in ('UserPromptSubmit', 'Stop', 'SubagentStop'):
        return {}
    paths = session_paths(codex_home, sid)
    # Child hook session_id belongs to parent. Select child's own transcript for collection.
    supplied = payload.get('agent_transcript_path') if event == 'SubagentStop' else payload.get('transcript_path')
    if supplied:
        candidate = Path(supplied).expanduser().resolve()
        allowed = [Path(codex_home).resolve() / name for name in ('sessions', 'archived_sessions')]
        if any(candidate == b or b in candidate.parents for b in allowed) and candidate.is_file():
            if candidate not in paths:
                paths.append(candidate)
    scan = store.scan(paths, max_bytes=12 * 1024 * 1024)
    output = {}
    if event == 'UserPromptSubmit':
        # Reconcile previous finalized response after the previous Stop timing window.
        previous = store.db.execute("SELECT id FROM turns WHERE session=? AND status='complete' ORDER BY start DESC LIMIT 1", (sid,)).fetchone()
        report = turn_report(store, sid, previous[0]) if previous else None
        if report:
            save_report(store, report)
        instructions = ('Token Steward policy: '+p['mode']+'. '
                        'Preserve requirements, required checks, model choice and authorization. '
                        'Reuse still-valid evidence; no extra turns for accounting. ')
        if p['mode'] == 'observe':
            instructions += 'Observe/report only; do not apply optimizations under this policy. '
        if report:
            instructions += 'Previous completed turn: ' + compact(report) + ' '
            for finding in report['analysis'][:p['max_advice_items']]:
                instructions += finding['code'] + ': ' + finding['suggested_action'] + ' '
        if scan['deferred']:
            instructions += 'Historical indexing is incomplete; do not interpret missing usage as zero. '
        if payload.get('cwd'):
            notes = store.db.execute("SELECT kind,payload FROM notes WHERE project=? AND kind IN ('fact','intervention') ORDER BY timestamp DESC LIMIT 3",
                                     (store.project(payload['cwd']),)).fetchall()
            if notes:
                instructions += 'Project notes exist; consult `notes --project <cwd>` only if relevant. Validate their evidence/valid_when before reuse. '
        instructions += 'Append a compact measured pre-final usage snapshot when requested; final-answer usage is reconciled afterward.'
        output = {'hookSpecificOutput': {'hookEventName':event, 'additionalContext':instructions[:2600]}}
    else:
        report = turn_report(store, sid, payload.get('turn_id'))
        target = save_report(store, report)
        if event == 'Stop' and p['report_every_message']:
            output = {'systemMessage':compact(report) + ' Recorded-through snapshot; report: ' + str(target)}
    if record:
        store.db.execute('INSERT INTO hook_runs(event,timestamp,elapsed_ms,ok,session,turn) VALUES(?,?,?,1,?,?)',
                         (event, now(), (time.monotonic()-started)*1000, sid, payload.get('turn_id')))
        store.db.commit()
    # Never decision:block, continue:false, permission decisions, or another model call.
    return output


def command_for(script, arguments, windows=None):
    values = [sys.executable, str(Path(script).resolve())] + list(arguments)
    windows = os.name == 'nt' if windows is None else windows
    if windows:
        # Codex Windows command hooks use a command string. Quote native executable/path arguments.
        return subprocess.list2cmdline(values)
    return shlex.join(values)


def powershell_invocation(script, arguments):
    values = [sys.executable, str(Path(script).resolve())] + list(arguments)
    return '& ' + ' '.join("'" + v.replace("'", "''") + "'" for v in values)


def hook_command_for(script, arguments, windows=None):
    """A Windows host may dispatch through cmd.exe or PowerShell. Support both.

    Encode only the invocation, never credentials or input. Quoted native argv alone
    is not executable PowerShell; shell metacharacters in paths must stay literal.
    """
    windows = os.name == 'nt' if windows is None else windows
    if not windows:
        return command_for(script, arguments, windows=False)
    invocation = powershell_invocation(script, arguments) + '; exit $LASTEXITCODE'
    encoded = base64.b64encode(invocation.encode('utf-16-le')).decode('ascii')
    return 'powershell.exe -NoLogo -NoProfile -NonInteractive -EncodedCommand ' + encoded


def install_integration(codex_home, script, store, remove=False):
    codex_home = Path(codex_home).resolve()
    hooks_path = codex_home / 'hooks.json'
    agents_path = codex_home / 'AGENTS.md'
    hooks = json.loads(hooks_path.read_text(encoding='utf-8-sig')) if hooks_path.exists() else {'hooks':{}}
    if not isinstance(hooks, dict) or not isinstance(hooks.get('hooks', {}), dict):
        raise ValueError('Existing hooks.json is not a supported object; refusing to overwrite it.')
    for path in (hooks_path, agents_path):
        backup = store.directory / ('original-' + path.name)
        if path.exists() and not backup.exists():
            backup.write_bytes(path.read_bytes())
    events = hooks.setdefault('hooks', {})
    # Remove only our exact status marker; preserve all unrelated handlers and groups.
    for event, groups in list(events.items()):
        updated = []
        for group in groups:
            group = dict(group)
            group['hooks'] = [h for h in group.get('hooks', []) if h.get('statusMessage') != MARKER]
            if group['hooks']:
                updated.append(group)
        events[event] = updated
    if not remove:
        for event in ('UserPromptSubmit','Stop','SubagentStop'):
            args = ['--codex-home', str(codex_home), '--data-dir', str(store.directory), 'hook']
            handler = {'type':'command', 'command':hook_command_for(script,args), 'timeout':20,
                       'statusMessage':MARKER}
            if event == 'UserPromptSubmit':
                handler['additionalContextLimit'] = 750
            events.setdefault(event, []).append({'hooks':[handler]})
    atomic_json(hooks_path, hooks)
    old = agents_path.read_text(encoding='utf-8-sig') if agents_path.exists() else ''
    if BEGIN in old and END in old:
        a,b = old.index(BEGIN), old.index(END)+len(END)
        old = old[:a] + old[b:]
    if not remove:
        args = ['--codex-home',str(codex_home),'--data-dir',str(store.directory),
                'report','--current','--refresh','--compact','--respect-policy']
        cmd = powershell_invocation(script,args) if os.name == 'nt' else command_for(script,args)
        block = ('\n' + BEGIN + '\n'
                 'Use the globally installed codex-token-steward skill for usage reporting and efficient execution. '
                 'Preserve the user\'s selected model, required outcome, and necessary verification. '
                 'Before each final response, run the following command once (no retry loop) and append its compact '
                 'usage snapshot plus one relevant optimization observation when reporting is enabled. If the command says '
                 'reporting is disabled, omit the footer. The snapshot excludes the forthcoming '
                 'final response; Stop hooks/next collection reconcile it. If usage is unavailable, say so; never invent totals. '
                 'For optimization decisions read the skill when needed; do not load all references or audit all history each turn.\n\n'
                 + ('Windows PowerShell command:\n' if os.name == 'nt' else '') + cmd + '\n\n'
                 'Review observed findings and improve execution within existing authorization. '
                 'Do not reduce quality, skip necessary checks, switch models, spawn agents, or alter configuration '
                 'merely to save tokens. Do not start extra turns solely for reporting. '
                 'For substantive work, if no Token Steward hook guidance arrived this turn, run the same script with '
                 '`prepare --current` instead of the report arguments, once alongside the first necessary tool call. '
                 'This supplies prior findings without relying on hook support. Simple conversation needs no preparation '
                 'or repository exploration. Do not claim zero-token AI replies or silently route messages to another product.\n' + END + '\n')
        old = old.rstrip() + '\n' + block
    agents_path.write_text(old, encoding='utf-8')
    launcher = None
    if not remove and os.name == 'nt':
        launcher = store.directory / 'Token Steward Status.cmd'
        launcher.write_text('@echo off\n' + hook_command_for(script,
            ['--codex-home',str(codex_home),'--data-dir',str(store.directory),'status','--refresh'])
            + '\npause\n',encoding='ascii')
    return {'installed':not remove, 'hooks_file':str(hooks_path), 'global_instructions':str(agents_path),
            'local_status_launcher':str(launcher) if launcher else None,
            'hook_trust':'Not modified. Review and trust definitions using the host hook controls (/hooks in CLI).',
            'activation':'Start a new task/reload configuration. Global instructions provide a fallback where hooks do not run.'}
