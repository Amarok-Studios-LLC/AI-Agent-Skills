"""Local weekly allowance pacing; percentages are not token or billing estimates."""
from datetime import datetime, timezone
import math

DAY = 86400
WEEK = 7 * DAY
MAX_AGE = 6 * 3600
MIN_SPAN = 6 * 3600


def stamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace('+00:00', 'Z')


def epoch(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp requires a timezone')
    return parsed.timestamp()


def weekly_pace(store, session=None, at=None):
    current = epoch(at) if at else datetime.now(timezone.utc).timestamp()
    # Do not merge sessions: a local Codex home can have account changes.
    if session is None:
        latest = store.db.execute('SELECT session FROM limits WHERE window=10080 ORDER BY timestamp DESC LIMIT 1').fetchone()
        session = latest[0] if latest else None
    rows = store.db.execute('SELECT timestamp,bucket,reset,used FROM limits WHERE window=10080 AND session=? ORDER BY timestamp', (session,))
    groups = {}
    for row in rows:
        try:
            t = epoch(row['timestamp'])
            reset, used = row['reset'], row['used']
            if (isinstance(reset, bool) or not isinstance(reset, (int, float)) or
                    not math.isfinite(reset) or not isinstance(used, (int, float)) or
                    not math.isfinite(used) or not 0 <= used <= 100 or t > current or
                    not reset - WEEK <= t < reset):
                continue
            groups.setdefault(row['bucket'], []).append(dict(row, time=t))
        except (ValueError, TypeError, OverflowError):
            continue
    result = []
    for bucket, samples in sorted(groups.items()):
        last = samples[-1]
        reset, used, observed = last['reset'], last['used'], last['time']
        age, days_left = current - observed, (reset - current) / DAY
        # Take only the contiguous latest cycle, never a prior reset or >24h history.
        cycle = []
        for sample in reversed(samples):
            if sample['reset'] != reset:
                break
            cycle.append(sample)
        cycle.reverse()
        recent = [r for r in cycle if r['time'] >= observed - DAY]
        elapsed = (observed - (reset - WEEK)) / DAY
        span = observed - recent[0]['time']
        delta = used - recent[0]['used']
        decreased = any(b['used'] < a['used'] for a, b in zip(recent, recent[1:]))
        fresh = age <= MAX_AGE and days_left > 0
        recent_rate = delta * DAY / span if span >= MIN_SPAN and delta >= 2 and not decreased else None
        cycle_rate = used / elapsed if elapsed > 0 else None
        suggested = (100 - used) / days_left if fresh else None
        # Require six hours of observed changes, not an invented zero-percent baseline.
        forecast_rate = recent_rate if fresh else None
        depletion = observed + (100 - used) / forecast_rate * DAY if forecast_rate else None
        status = ('expired' if days_left <= 0 else 'stale' if age > MAX_AGE else 'exhausted' if used >= 100 else
                  'usage_adjustment' if decreased else 'insufficient_observations' if forecast_rate is None else
                  'projection_elapsed' if depletion <= current else 'estimated')
        if status != 'estimated':
            depletion = None
        result.append({
            'bucket': bucket, 'scope': 'Account allowance readings within one recorded session; no cross-account merge.',
            'observed_at': stamp(observed), 'reading_age_seconds': age,
            'used_percent': used, 'remaining_percent': 100 - used,
            'reset_at': stamp(reset), 'reset_at_local': datetime.fromtimestamp(reset).astimezone().isoformat(),
            'days_until_reset': max(0, days_left), 'status': status,
            'suggested_percentage_points_per_day': suggested,
            'even_week_percentage_points_per_day': 100 / 7,
            'cycle_average_percentage_points_per_day': cycle_rate,
            'recent_percentage_points_per_day': recent_rate,
            'sample_span_hours': span / 3600, 'observed_change_percentage_points': delta,
            'pace_ratio_to_suggested': forecast_rate / suggested if forecast_rate is not None and suggested else None,
            'projected_exhaustion_at': stamp(depletion) if depletion else None,
            'projected_exhaustion_at_local': datetime.fromtimestamp(depletion).astimezone().isoformat() if depletion else None,
            'projected_to_last_until_reset': depletion >= reset if depletion else None,
            'note': 'Conditional constant-pace estimate, not a guarantee. Rounded readings and changing work patterns add uncertainty. '
                    'Suggested pace assumes no unrecorded usage since the reading. Cycle average assumes this seven-day cycle began at zero; '
                    'it is descriptive only. Forecast needs >=6h and >=2 percentage points of observed increase within 24h. '
                    'Readings older than 6h or past reset cannot support a current forecast.'})
    return result


def compact_pace(items):
    parts = []
    for p in items:
        text = 'Weekly recorded: %g%% used / %g%% left. Weekly reset: %s; reading age %.1fh.' % (p['used_percent'], p['remaining_percent'], p['reset_at_local'], p['reading_age_seconds'] / 3600)
        target = p['suggested_percentage_points_per_day']
        if target is not None:
            text += ' Suggested: %.2f percentage points/day.' % target
        rate = p['recent_percentage_points_per_day']
        text += ' Recent pace: %s.' % ('%.2f points/day' % rate if rate is not None else 'unavailable')
        if p['cycle_average_percentage_points_per_day'] is not None:
            text += ' Week average at reading: %.2f points/day.' % p['cycle_average_percentage_points_per_day']
        ratio = p['pace_ratio_to_suggested']
        if ratio is not None:
            text += ' %.2fx suggested pace.' % ratio
        if p['projected_exhaustion_at']:
            text += (' At that pace: lasts until reset.' if p['projected_to_last_until_reset'] else
                     ' At that pace: may run out %s.' % p['projected_exhaustion_at_local'])
        else:
            text += ' Run-out forecast unavailable (%s).' % p['status']
        parts.append(text)
    return ' '.join(parts) or 'Weekly reset/pace: unavailable.'
