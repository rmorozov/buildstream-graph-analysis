"""UX-103: is the cache getting worse?

`UX-92` gave one run a cache report card - hit ratio, transfer cost,
churn. A report card once is a diagnosis; the CI question is a trend. A
remote that slows from 40MB/s to 5MB/s, a hit ratio eroding as a
volatile key spreads, transfer time quietly overtaking rebuild time:
each degrades every build in the organisation, none is visible in any
single run, and all are computable from data the per-run capture refs
(`UX-81`) now retain weekly.

Two decisions worth stating, because they are what keep this from being
a second, subtly different analysis:

**The noise model is `bga.compare`'s.** `compute_band` - median ± k·
scaled MAD, with the `MIN_BASELINE_RUNS` floor - is reused verbatim
rather than reimplemented. The evidence behind that shape (seven
repeated builds of one unchanged commit, and what a single contaminated
baseline does to a mean ± σ band) is in its own docstring and applies
here unchanged.

**Churn is pairwise, and it keeps `UX-93`'s labels.** A run has no churn
on its own; churn is a fact about a run *against its predecessor*. So
each row's churn is computed against the row before it, through the same
`compute_cache_churn` the `compare` path uses - which means a run whose
predecessor was a caches-off build reports no churn verdict at all
rather than a fabricated one, and a rebuild both runs made is a
retention question rather than waste.

**What this cannot see today.** Bytes moved. Plane 1 records transfer
*seconds*, not artifact sizes, so "the remote slowed down" is measurable
here only as time per artifact - which conflates a slower remote with
larger artifacts. Seconds first, sizes as the follow-on, the same
posture `UX-100` takes to its own size axis. On captures taken with
remotes ignored (which is every published freedesktop-sdk capture, by
design) there is no transfer at all, and the trend says so rather than
reporting zero.
"""
import os
from pathlib import Path
from typing import List, Optional

from .cache_effectiveness import compute_cache_accounting, compute_cache_churn
from .compare import _SIGNIFICANCE_PCT, MIN_BASELINE_RUNS, compute_band

# A metric whose newest reading sits outside the trailing window's band
# is worth a finding. Each entry is `(key, label, direction)`, where
# direction says which way is bad - a hit ratio falling out of the band
# is a degradation, transfer time rising out of it is too, and the
# opposite move in either is good news that must not be reported as a
# regression.
TRENDED_METRICS = (
    ('hit_ratio', 'cache hit ratio', 'lower_is_worse',
     'the cache is serving less of this build than it used to'),
    ('transfer_us', 'transfer seconds', 'higher_is_worse',
     'the cache remote is degrading, before any element gets slower'),
    ('transfer_per_artifact_us', 'transfer seconds per artifact', 'higher_is_worse',
     'the cache remote is degrading, before any element gets slower'),
    ('rebuild_us', 'rebuild seconds', 'higher_is_worse',
     'this build is doing more work than the same build used to, which the '
     'hit ratio beside it either explains or does not'),
)

# The band is widened to this share of the trailing median when the
# measured one is narrower. Taken from `bga.compare`'s own
# `_SIGNIFICANCE_PCT` rather than chosen here, and for its reason: a set
# of near-identical runs yields a near-zero MAD, and a band tighter than
# quantization noise fires on everything. Measured while building this:
# three runs whose rebuild seconds differed by 0.03% produced a band
# 2.2s wide on a 4740s median, and a 6% rise read as a regression.
BAND_FLOOR_PCT = _SIGNIFICANCE_PCT


def _element_durations(result) -> dict:
    return (getattr(result, 'signals', None) or {}).get('element_durations') or {}


def _rebuild_us(tasks) -> Optional[int]:
    """Wall-clock this run spent *building*, summed over BUILD tasks.

    Not `signals.element_durations`, which is the longest task per
    element *whatever its kind* - the one definition every path
    computation shares (`UX-53`), and the wrong one here. Caught by
    measurement: adding synthetic PULL spans to a run to exercise the
    transfer trend also moved its "rebuild" seconds, because a 6.4s pull
    outlasts a short build and becomes that element's duration. A trend
    that sets rebuild time against transfer time cannot have transfer
    time inside both sides of the comparison.

    Summed rather than maxed, matching `_transfer_us`: the question is
    how much building this build did, not how long the build window was.
    """
    total = None
    for task in tasks or []:
        kind = getattr(getattr(task, 'task_key', None), 'kind', None)
        name = getattr(kind, 'value', kind)
        if name == 'BUILD':
            total = (total or 0) + (task.finish_us - task.start_us)
    return total


def _row(name: str, result, run_context, graph, tasks, previous) -> dict:
    """One run's cache reading, plus its churn against its predecessor."""
    accounting = compute_cache_accounting(
        run_context, graph=graph, tasks=tasks,
        total_duration_us=getattr(result, 'total_duration_us', None),
    )
    transfer = accounting.get('transfer_us') or {}
    transfer_us = sum(transfer.values()) if transfer else None
    pulled = accounting.get('cached_elements')
    durations = _element_durations(result)

    row = {
        'run': name,
        'run_mode': (result.confidence or {}).get('run_mode'),
        'total_duration_us': getattr(result, 'total_duration_us', None),
        'hit_ratio': accounting.get('hit_ratio'),
        'built_elements': accounting.get('built_elements'),
        'cached_elements': accounting.get('cached_elements'),
        'transfer_us': transfer_us,
        # Per *artifact served*, since that is what a degrading remote
        # changes. None rather than zero where either half is unmeasured:
        # a run with no transfer has no transfer rate.
        'transfer_per_artifact_us': (
            transfer_us / pulled if transfer_us and pulled else None
        ),
        'rebuild_us': _rebuild_us(tasks),
        'churn': None,
    }
    if previous is not None:
        row['churn'] = compute_cache_churn(
            previous['elements'], graph.elements if graph else [],
            graph.dependencies if graph else [],
            set(durations), durations,
            baseline_built=set(previous['durations']) if previous['durations'] is not None else None,
            candidate_run_mode=row['run_mode'],
            baseline_run_mode=previous['run_mode'],
        )
    return row


def _band_findings(rows: List[dict]) -> List[dict]:
    """A finding per trended metric whose newest reading leaves the band
    the trailing window describes.

    The window is every row but the newest, which is the only split that
    makes the newest run a *candidate* rather than part of its own
    baseline - the same distinction `bga compare` draws.
    """
    if len(rows) <= MIN_BASELINE_RUNS:
        return []
    window, newest = rows[:-1], rows[-1]
    findings = []
    for key, label, direction, consequence in TRENDED_METRICS:
        values = [row[key] for row in window if row.get(key) is not None]
        current = newest.get(key)
        if current is None or len(values) < MIN_BASELINE_RUNS:
            continue
        band = compute_band(values)
        if band is None:
            continue
        median = band['median_us']
        # Widened to the fixed percentage when the measured band is
        # narrower, exactly as `bga compare` does with the same band.
        half_width = max(
            band['k'] * band['scaled_mad_us'], abs(median) * BAND_FLOOR_PCT / 100,
        )
        if not half_width:
            continue
        low, high = median - half_width, median + half_width
        band = dict(
            band, low_us=low, high_us=high,
            widened_to_fixed_pct=half_width > band['k'] * band['scaled_mad_us'],
        )
        worse = current < low if direction == 'lower_is_worse' else current > high
        if not worse:
            continue
        ratio = current / median if median else None
        findings.append({
            'id': 'cache-trend-regression',
            'severity': 'high',
            'metric': key,
            'title': (
                f"{label} is {ratio:.1f}x the trailing median"
                if ratio else f"{label} left the trailing band"
            ) + (
                f" ({_render(key, current)} against {_render(key, median)} over "
                f"{band['n']} run(s), band {_render(key, band['low_us'])}.."
                f"{_render(key, band['high_us'])}"
                + (', widened to the fixed rule' if band['widened_to_fixed_pct'] else '')
                + f") - {consequence}"
            ),
            'evidence': {
                'metric': key, 'current': current, 'median': median,
                'band_low': band['low_us'], 'band_high': band['high_us'],
                'window_runs': band['n'], 'direction': direction,
                'widened_to_fixed_pct': band['widened_to_fixed_pct'],
            },
        })
    return findings


def _render(key: str, value: float) -> str:
    if key == 'hit_ratio':
        return f"{value * 100:.1f}%"
    return f"{value / 1e6:.1f}s"


def build_trend(rows: List[dict]) -> dict:
    """The trend payload: the rows as given, plus whatever the window
    supports.

    `insufficient_window` is a field rather than an absence. Two runs is
    not a trend, and a command that quietly printed two rows and no
    verdict would look identical to one that checked and found nothing.
    """
    findings = _band_findings(rows)
    return {
        'runs': rows,
        'findings': findings,
        'insufficient_window': (
            {
                'supplied': len(rows),
                'required': MIN_BASELINE_RUNS + 1,
                'message': (
                    f"{len(rows)} run(s) supplied; a band needs {MIN_BASELINE_RUNS} "
                    f"trailing runs plus the one being judged, so {MIN_BASELINE_RUNS + 1}. "
                    f"The rows above are real readings with no verdict attached."
                ),
            }
            if len(rows) <= MIN_BASELINE_RUNS else None
        ),
        'note': (
            "Transfer figures are wall-clock seconds, not bytes: Plane 1 does not "
            "record artifact sizes, so a rise in seconds per artifact is a slower "
            "remote or a larger artifact and this cannot tell them apart. A capture "
            "taken with remotes ignored has no transfer at all and reports None "
            "rather than zero."
        ),
    }


def trend_from_run_dirs(run_dirs, **analyzer_kwargs) -> dict:
    """Load each run directory in the order given - chronological, which
    the caller knows and this cannot - and build the trend.

    Each run gets its own analyzer, the same way `compare_runs` does: two
    runs sharing analysis state would be two runs that are not
    independent measurements.
    """
    from .analyzer import BuildEfficiencyAnalyzer

    rows: List[dict] = []
    previous = None
    for run_dir in run_dirs:
        analyzer = BuildEfficiencyAnalyzer(**analyzer_kwargs)
        analyzer.load(Path(run_dir))
        result = analyzer.analyze()
        graph = analyzer.graph
        # The last two path components, not the whole path: in CI these
        # are `<something>/<run-id>/run`, and truncating a long absolute
        # path from the left throws away the only part that differs.
        path = Path(run_dir)
        label = os.path.join(path.parent.name, path.name) if path.parent.name else path.name
        rows.append(_row(
            label, result, analyzer.run_context, graph,
            analyzer.normalized_tasks, previous,
        ))
        previous = {
            'elements': graph.elements if graph else [],
            'durations': _element_durations(result),
            'run_mode': (result.confidence or {}).get('run_mode'),
        }
    return build_trend(rows)


def format_trend_text(trend: dict) -> str:
    lines = [
        # 60, the width every other report in this tool uses. A single
        # wider banner reads as a different program's output when two
        # reports are pasted into one issue.
        '=' * 60,
        'Cache Health Trend',
        '=' * 60,
        f"{'run':<28s} {'hit':>6s} {'built':>6s} {'cached':>7s} "
        f"{'xfer':>8s} {'/artifact':>10s} {'churn':>7s}",
    ]
    for row in trend['runs']:
        churn = row.get('churn') or {}
        if churn.get('applicable') is False:
            churn_cell = 'n/a'
        elif churn:
            churn_cell = f"{churn.get('churned_count', 0)}"
            if churn.get('rebuilt_in_both_count'):
                churn_cell += f"+{churn['rebuilt_in_both_count']}r"
        else:
            churn_cell = '-'
        hit = row['hit_ratio']
        hit_cell = f"{hit * 100:.0f}%" if hit is not None else '-'
        built = row['built_elements']
        cached = row['cached_elements']
        transfer = row['transfer_us']
        per_artifact = row['transfer_per_artifact_us']
        lines.append(
            f"{row['run'][:28]:<28s} "
            f"{hit_cell:>6s} "
            f"{(built if built is not None else '-'):>6} "
            f"{(cached if cached is not None else '-'):>7} "
            f"{(f'{transfer / 1e6:.1f}s' if transfer else '-'):>8s} "
            f"{(f'{per_artifact / 1e6:.2f}s' if per_artifact else '-'):>10s} "
            f"{churn_cell:>7s}"
        )
    lines.append('')
    # The churn cell is the only column in this table a reader cannot
    # decode from its header. `0+25r` said nothing until you found the
    # docs, which is one lookup too many for a column of five characters.
    if any((row.get('churn') or {}).get('rebuilt_in_both_count')
           for row in trend['runs']):
        lines.append(
            'churn: elements rebuilt since the previous run, then `+Nr` for the '
            'N of them that rebuilt in BOTH runs with the same cache key - work '
            'the cache should have served and did not. `n/a` where the two runs '
            'are not comparable (one full, one incremental).'
        )
        lines.append('')
    if trend['insufficient_window']:
        lines.append(f"No verdict: {trend['insufficient_window']['message']}")
    elif not trend['findings']:
        lines.append(
            'Every trended metric on the newest run sits inside the band its '
            'trailing window describes.'
        )
    for finding in trend['findings']:
        lines.append(f"[{finding['severity']}] {finding['id']}: {finding['title']}")
    lines.append('')
    lines.append(f"({trend['note']})")
    lines.append('=' * 60)
    return '\n'.join(lines)
