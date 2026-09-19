"""Small deterministic reports and explainable personalization signals."""
import collections
import json
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

from accounting import atomic_json, now, safe_id

DEFAULT_POLICY = {
    'mode': 'preserve-capability', 'report_every_message': True,
    'allow_model_change': False, 'allow_subagents': False,
    'soft_turn_tokens': None, 'min_baseline_turns': 8,
    'large_context_tokens': 100000, 'repeat_tool_threshold': 3,
    'max_advice_items': 3, 'discovery_days': 30,
}


def policy(store):
    p = store.directory / 'policy.json'
    value = DEFAULT_POLICY.copy()
    if p.exists():
        incoming = json.loads(p.read_text(encoding='utf-8'))
        if not isinstance(incoming, dict):
            raise ValueError('Policy must be an object')
        value.update(incoming)
    return value


def totals(rows):
    a = {'model_calls': len(rows), 'input_tokens': 0, 'cached_input_tokens': 0,
         'uncached_input_tokens': 0, 'output_tokens': 0, 'reasoning_output_tokens': 0}
    for r in rows:
        for dest, src in [('input_tokens','input'), ('cached_input_tokens','cached'),
                          ('output_tokens','output'), ('reasoning_output_tokens','reasoning')]:
            a[dest] += r[src]
    a['uncached_input_tokens'] = a['input_tokens'] - a['cached_input_tokens']
    a['total_tokens'] = a['input_tokens'] + a['output_tokens']
    a['cached_input_pct'] = round(100 * a['cached_input_tokens'] / a['input_tokens'], 2) if a['input_tokens'] else None
    a['median_input_per_call'] = statistics.median(r['input'] for r in rows) if rows else None
    return a


def coverage(store):
    rows = store.db.execute('SELECT COALESCE(SUM(errors),0),COALESCE(SUM(pending),0),COUNT(*) FROM files').fetchone()
    warnings = ['Local recorded sessions only; other devices/cloud and unrecorded activity may be missing.',
                'Tokens, subscription allowance and purchased credits are distinct; no invoice is reconstructed.',
                'Raw input includes cached input; output includes reasoning. Do not sum subsets again.']
    if rows[0]:
        warnings.append('%s malformed or unsupported records were skipped.' % rows[0])
    if rows[1]:
        warnings.append('%s files have unconsumed bytes or an unfinished final line.' % rows[1])
    for key, message in (
        ('rewritten_source_seen', 'A source was rewritten; stable events deduplicated, but historical coverage needs review.'),
        ('unsupported_last_only', 'Last-only token events lack stable cumulative identity and were excluded.'),
        ('counter_gaps', 'Some cumulative changes exceed last-call counters; unseen calls may be missing from attributed totals.'),
        ('unattributed_initial_totals', 'Initial cumulative totals without last-call details were excluded.')):
        if store.get(key):
            warnings.append(message)
    return {'source': 'Codex rollout JSONL adapter v1', 'files_indexed': rows[2],
            'parse_errors': rows[0], 'files_pending': rows[1], 'warnings': warnings,
            'last_scan': json.loads(store.get('last_scan', '{}'))}


def analyze(store, rows, tools, session, turn):
    p = policy(store)
    a = totals(rows)
    findings = []

    def add(code, evidence, action, confidence='signal'):
        findings.append({'code': code, 'evidence': evidence, 'suggested_action': action,
                         'confidence': confidence, 'waste_proven': False})

    if not rows:
        add('usage_unavailable', 'No attributable token records available yet.',
            'Report unavailable, not zero; reconcile after log flush.', 'coverage')
    non_steward = [t for t in tools if not t['steward']]
    repeated = collections.Counter(t['signature'] for t in non_steward)
    repeats = sum(n - 1 for n in repeated.values() if n >= p['repeat_tool_threshold'])
    if repeats:
        add('repeated_tool_inputs', '%d repeated tool invocations with identical input signatures.' % repeats,
            'Check whether state changed or polling was required; reuse results only when still valid.')
    if a['median_input_per_call'] and a['median_input_per_call'] >= p['large_context_tokens']:
        add('large_repeated_context', 'Median input per call is %s tokens; cached share is %s%%.' %
            (a['median_input_per_call'], a['cached_input_pct']),
            'Use focused retrieval and durable decisions; preserve useful cache/context. Do not blindly restart.')
    failures = sum(t['failed'] for t in non_steward)
    if failures >= 3:
        add('repeated_tool_failures', '%d tool results contain explicit failure markers.' % failures,
            'Compare failed hypotheses and change the experiment before repeating equivalent attempts.')
    browser = sum('cua' in t['name'].lower() or 'browser' in t['name'].lower() for t in non_steward)
    if browser >= 20:
        add('interaction_heavy', '%d browser/computer tool calls recorded.' % browser,
            'Consider an authorized API/CLI or a batched deterministic operation if it preserves verification.')
    coordination = sum(any(k in t['name'] for k in ('send_message','followup_task','spawn_agent')) for t in non_steward)
    if coordination >= 12:
        add('coordination_heavy', '%d agent coordination calls recorded.' % coordination,
            'Use bounded ownership, compact evidence handoffs, and stop reactivating completed work without a new need.')
    large_outputs = sum(t['output_bytes'] for t in non_steward)
    if large_outputs >= 250000:
        add('large_tool_results', '%d output bytes recorded (not a token estimate).' % large_outputs,
            'Filter at the tool boundary, persist full results locally, and return excerpts tied to the question.')
    if p['soft_turn_tokens'] and a['total_tokens'] >= p['soft_turn_tokens']:
        add('soft_budget_exceeded', '%d recorded tokens exceed the configured %d-token advisory budget.' %
            (a['total_tokens'], p['soft_turn_tokens']),
            'Check remaining scope and preserve validation/recovery capacity; this is not a hard spending cap.')
    # Baselines compare same project and model. No inference from unrelated tasks or missing acceptance.
    project = store.db.execute('SELECT project FROM sessions WHERE id=?', (session,)).fetchone()
    model_names = {r['model'] for r in rows}
    baseline = []
    if project and len(model_names) == 1:
        model = next(iter(model_names))
        baseline = list(store.db.execute('''SELECT c.session,c.turn,SUM(c.input+c.output) AS tokens
            FROM calls c JOIN sessions s ON s.id=c.session
            JOIN turns t ON t.session=c.session AND t.id=c.turn
            WHERE s.project=? AND t.status='complete' AND c.model=?
              AND NOT(c.session=? AND c.turn=?)
            GROUP BY c.session,c.turn ORDER BY MAX(c.timestamp) DESC LIMIT 40''',
            (project[0], model, session, turn)))
        if len(baseline) >= p['min_baseline_turns']:
            median = statistics.median(r['tokens'] for r in baseline)
            main_tokens = sum(r['input'] + r['output'] for r in rows if r['session'] == session)
            if median and main_tokens > median * 3:
                add('above_local_baseline', 'Main-agent volume exceeds 3x the median of %d completed project/model turns.' % len(baseline),
                    'Compare scope and outcomes before changing execution; large tasks can legitimately cost more.')
    return findings, {'comparable_project_model_turns': len(baseline),
                       'quality_inferred': False, 'policy': p['mode']}


def registry(store):
    p = store.directory / 'models.json'
    if not p.exists():
        p = Path(__file__).parent.parent / 'references' / 'models.json'
    return json.loads(p.read_text(encoding='utf-8'))


def estimate_cost(store, rows):
    catalog = registry(store)
    estimates = collections.Counter()
    priced_counts = collections.Counter()
    missing = set()
    stale = set()
    for r in rows:
        choices = [m for m in catalog.get('rates', []) if m['model'] == r['model'] and
                   m['effective_from'] <= r['timestamp'][:10] and
                   (not m.get('effective_until') or r['timestamp'][:10] < m['effective_until']) and
                   m.get('service_tier') == r['service']]
        if not choices:
            missing.add(r['model'] + '/' + r['service'])
            continue
        for unit in {m['unit'] for m in choices}:
            m = max((c for c in choices if c['unit']==unit), key=lambda x: x['effective_from'])
            age = datetime.now(timezone.utc).date() - datetime.strptime(m['checked_at'], '%Y-%m-%d').date()
            if age.days > 14 or age.days < 0:
                stale.add(r['model'])
                continue
            amount = ((r['input'] - r['cached']) * m['input'] + r['cached'] * m['cached'] + r['output'] * m['output']) / 1e6
            estimates[m['unit']] += amount
            priced_counts[m['unit']] += 1
    return {'estimated_by_unit': {k: round(v, 6) for k,v in estimates.items()},
            'priced_calls_by_unit':dict(priced_counts),
            'complete_by_unit':{k:v==len(rows) for k,v in priced_counts.items()},
            'unpriced_model_service_pairs': sorted(missing), 'stale_rate_models': sorted(stale),
            'complete': not missing and not stale and bool(rows) and all(v==len(rows) for v in priced_counts.values()),
            'note': 'Published-rate estimate only, not billed credits, subscription depletion, or a counterfactual saving.'}


def turn_report(store, session, turn=None, include_calls=True):
    if not turn:
        row = store.db.execute('SELECT id FROM turns WHERE session=? ORDER BY start DESC LIMIT 1', (session,)).fetchone()
        turn = row[0] if row else 'unattributed'
    row = store.db.execute('SELECT * FROM turns WHERE session=? AND id=?', (session, turn)).fetchone()
    root = row['root'] if row else turn
    # Only explicitly linked root IDs: do not guess subagent attribution from overlapping timestamps.
    rows = [dict(r) for r in store.db.execute('SELECT * FROM calls WHERE (session=? AND turn=?) OR (root=? AND root NOT IN (\'unknown\',\'unattributed\')) ORDER BY timestamp',
                                             (session, turn, root))]
    descendants = {session}
    relations = list(store.db.execute('SELECT id,parent FROM sessions'))
    while True:
        more = {r['id'] for r in relations if r['parent'] in descendants}
        if more <= descendants:
            break
        descendants.update(more)
    rows = [r for r in rows if r['session'] in descendants]
    pairs = {(r['session'], r['turn']) for r in rows} | {(session, turn)}
    tools = []
    for sid, tid in pairs:
        tools.extend(dict(r) for r in store.db.execute('SELECT * FROM tools WHERE session=? AND turn=?', (sid, tid)))
    findings, baseline = analyze(store, rows, tools, session, turn)
    child = [r for r in rows if r['session'] != session]
    result = {'schema_version': 1, 'generated_at': now(), 'session': session, 'turn': turn,
              'status': row['status'] if row else 'unavailable',
              'recorded_through': max((r['timestamp'] for r in rows), default=None),
              'timing_note': 'Snapshot of recorded usage. Final response and late child events can arrive later; reconcile on the next scan.',
              'usage': totals(rows), 'linked_subagent_usage': totals(child),
              'models': dict(collections.Counter(r['model'] for r in rows)),
              'efforts': dict(collections.Counter(r['effort'] for r in rows)),
              'tools': {'calls': len(tools), 'by_name': dict(collections.Counter(t['name'] for t in tools)),
                        'steward_calls_identified': sum(t['steward'] for t in tools),
                        'recorded_output_bytes': sum(t['output_bytes'] for t in tools)},
              'analysis': findings, 'personalization': baseline,
              'cost': estimate_cost(store, rows), 'coverage': coverage(store)}
    if include_calls:
        result['calls'] = [{k:v for k,v in r.items() if k != 'id'} for r in rows]
        for c in result['calls']:
            c['analysis'] = []
            if c['input'] >= policy(store)['large_context_tokens']:
                c['analysis'].append('large_input_context; inspect relevance, not automatically waste')
            if c['quality'] != 'reported_last_call':
                c['analysis'].append('aggregate event; not guaranteed one model request')
            if c['model'] not in {m['id'] for m in registry(store).get('models', [])}:
                c['analysis'].append('unknown_model; track usage without assuming price or capability')
    return result


def compact(report):
    u = report['usage']
    if not u['model_calls']:
        return 'Usage: unavailable for this turn; do not infer zero consumption.'
    return ('Usage snapshot: {model_calls:,} calls; {input_tokens:,} input '
            '({cached_input_tokens:,} cached); {output_tokens:,} output '
            '({reasoning_output_tokens:,} reasoning included).').format(**u)


def save_report(store, report):
    folder = store.directory / 'reports' / safe_id(report['session']).replace('/', '_').replace(':', '_')
    stem = safe_id(report['turn']).replace('/', '_').replace(':', '_')
    target = folder / (stem + '.json')
    atomic_json(target, report)
    text = '# Per-message usage report\n\n' + compact(report) + '\n\n'
    text += 'Recorded through: %s. Status: %s.\n\n%s\n\n' % (report['recorded_through'], report['status'], report['timing_note'])
    text += '## Analysis\n\n'
    for item in report['analysis']:
        text += '- **%s:** %s %s\n' % (item['code'], item['evidence'], item['suggested_action'])
    if not report['analysis']:
        text += 'No configured heuristic fired. This does not prove the work was optimal.\n'
    text += '\n## Coverage\n\n' + '\n'.join('- ' + w for w in report['coverage']['warnings'])
    # Atomic JSON is canonical; markdown is a convenience generated from the same snapshot.
    target.with_suffix('.md').write_text(text + '\n', encoding='utf-8')
    return target


def audit(store, days=7):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace('+00:00', 'Z')
    rows = [dict(r) for r in store.db.execute('SELECT * FROM calls WHERE timestamp>=? ORDER BY timestamp', (since,))]
    groups = {}
    for kind, key in [('model', 'model'), ('effort', 'effort'), ('session', 'session')]:
        grouped = collections.defaultdict(list)
        for r in rows:
            grouped[r[key]].append(r)
        groups[kind] = sorted([{'id': k, **totals(v)} for k,v in grouped.items()],
                              key=lambda x: x['total_tokens'], reverse=True)
    project_groups = collections.defaultdict(list)
    sessions = {r['id']:dict(r) for r in store.db.execute('SELECT * FROM sessions')}
    for r in rows:
        project_groups[sessions.get(r['session'], {}).get('project', 'unknown')].append(r)
    groups['project'] = sorted([{'id':k, **totals(v)} for k,v in project_groups.items()], key=lambda x:x['total_tokens'], reverse=True)
    limits = [dict(r) for r in store.db.execute('SELECT timestamp,bucket,window,reset,used FROM limits WHERE timestamp>=? ORDER BY timestamp', (since,))]
    windows = collections.defaultdict(list)
    for r in limits:
        windows[(r['bucket'], r['window'], r['reset'])].append(r)
    allowance = [{'bucket':k[0], 'window_minutes':k[1], 'reset_unix':k[2],
                  'first':v[0], 'last':v[-1], 'note':'Account-wide historical readings; no task cost attribution.'}
                 for k,v in windows.items()]
    observed_models = sorted({r['model'] for r in rows})
    known = {m['id'] for m in registry(store).get('models', [])}
    return {'schema_version':1, 'generated_at':now(), 'since':since, 'usage':totals(rows),
            'ranked_by':'raw recorded token volume, not cost or waste', 'groups':groups,
            'allowance_windows':allowance, 'unknown_models':sorted(set(observed_models)-known),
            'cost':estimate_cost(store, rows), 'coverage':coverage(store),
            'next_step':'Inspect top task reports, compare scope/outcomes, then record an intervention and acceptance evidence.'}
