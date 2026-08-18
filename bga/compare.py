"""
Run-to-run comparison (UX-01).

`bga compare BASELINE CANDIDATE` answers the question the iterative-
optimization workflow asks repeatedly: "did that change actually help?"
Compares two independently-analyzed runs (bga/analyzer.py - no new
analysis algorithm here, this is a reporting layer on top of two
already-correct single-run analyses) and reports signed deltas plus a
verdict, gated on confidence and on whether the two runs' graphs are
even the same project.
"""
import logging
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .analyzer import BuildEfficiencyAnalyzer
from .ingest.models import AnalysisResult, Element
from .report.text import _CONFIDENCE_HIGH

logger = logging.getLogger(__name__)

# "No significant change" band, expressed as a percentage of the
# baseline's total_duration_us rather than an absolute microsecond
# threshold - so a small build and a large build are judged
# consistently. 1% is comfortably above realistic quantization noise
# (Part 3.2's epsilon grid is typically tens of milliseconds against
# builds of seconds-to-minutes) but small enough to catch a genuinely
# small real improvement/regression a user would care about.
_SIGNIFICANCE_PCT = 1

# Floor fields compared, in display order. 'total_duration_us' isn't a
# floors-dict key (it's AnalysisResult's own field - the run's real
# wall-clock duration per Part 4.3, falling back to the tracked-task
# horizon only when wall-clock bounds aren't available - see UX-10) -
# included here as the primary, most user-meaningful "did the build get
# faster" number; the rest are the certified/advisory floors themselves.
_FLOOR_KEYS = (
    'total_duration_us', 't_infinity_observed', 'lb', 'certified_headroom',
    't_c', 'efficiency_score',
    # UX-27: the graph-shape-aware signal. Included here specifically
    # because the iterative-optimization workflow `bga compare` exists
    # for is where the gap shows: on a real 30.5% improvement every other
    # metric in this list either stayed flat or moved backwards, and this
    # one moved 25% -> 63%.
    'occupancy_ratio',
)


# UX-59: the fewest baseline runs a band may be derived from. Below this
# a "band" is a restatement of one or two numbers, and the fixed
# percentage is the more honest rule.
MIN_BASELINE_RUNS = 3

# Default width, in scaled-MAD units. 3 is the conventional outlier
# distance and, measured on seven real repeated builds of one unchanged
# commit, contains all seven while still catching a +15% regression.
DEFAULT_BAND_K = 3.0


def compute_band(durations_us: List[float], k: float = DEFAULT_BAND_K) -> Optional[dict]:
    """Robust noise band for a set of baseline runs: median ± k·(1.4826·MAD).

    Why a band at all: `_SIGNIFICANCE_PCT` is a single constant applied to
    runs of wildly different size. Seven real repeated builds of one
    unchanged `examples/06` commit measured 26.30s … 27.72s — a standard
    deviation of **1.8% of the mean** — so the fixed 1% rule places
    **4 of those 7 identical runs outside the band** and would call them
    regressions or improvements. On a small incremental build the rule is
    at its most trigger-happy exactly where the signal is weakest.

    Why the median and MAD rather than the mean and standard deviation:
    not skew. At n=7 the same data is very nearly symmetric
    ((mean−median)/sd = −0.15), and both bands contain all seven runs.
    The difference is robustness to a *single* contaminated baseline run,
    which in CI means one runner that got a noisy neighbour. Replacing
    the slowest of those seven with a 45s outlier widens the mean±3σ band
    from 3.00s to **40.64s**, at which point it misses a real +15%
    regression outright; the median±3·MAD band is unchanged at 3.29s and
    still catches it.

    Returns None below `MIN_BASELINE_RUNS`. A zero MAD — every baseline
    run identical to the microsecond — would collapse the band to a
    point and make any delta significant, so the caller widens it to the
    fixed percentage rather than this function inventing a floor it has
    no basis for.
    """
    if len(durations_us) < MIN_BASELINE_RUNS:
        return None
    ordered = sorted(durations_us)
    median = statistics.median(ordered)
    mad = statistics.median([abs(x - median) for x in ordered])
    scaled = 1.4826 * mad
    return {
        "n": len(ordered),
        "median_us": median,
        "scaled_mad_us": scaled,
        "k": k,
        "low_us": median - k * scaled,
        "high_us": median + k * scaled,
    }


@dataclass
class ComparisonResult:
    baseline_run_id: str
    candidate_run_id: str
    baseline_metrics: Dict[str, Optional[float]]
    candidate_metrics: Dict[str, Optional[float]]
    deltas: Dict[str, Optional[float]]
    baseline_confidence: Optional[float]
    candidate_confidence: Optional[float]
    attribution_deltas: Dict[str, dict]
    verdict: str
    low_confidence: bool
    comparability_warning: Optional[str] = None
    # UX-78: the same facts as `comparability_warning`, structured, so a
    # caller can refuse and name the check that failed rather than
    # matching on prose. Each entry is `{"check": ..., "message": ...}`;
    # `check` is stable, `message` is not.
    mismatches: List[dict] = field(default_factory=list)
    # UX-54: which of the two runs describe a build that did not
    # complete ("baseline" and/or "candidate"). Kept separate from
    # `low_confidence`, which is about a signal being noisy: a failed
    # build is not a noisy signal, it is a definite fact, and the two
    # therefore get opposite gate behaviour - low confidence fails open,
    # a failed build fails closed.
    failed_runs: List[str] = field(default_factory=list)
    # UX-59: the noise band the verdict was judged against, when
    # enough baseline runs were supplied to derive one. None means
    # the fixed-percentage rule was used, which is what every
    # comparison did before this existed.
    baseline_band: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            'baseline_run_id': self.baseline_run_id,
            'candidate_run_id': self.candidate_run_id,
            'baseline': self.baseline_metrics,
            'candidate': self.candidate_metrics,
            'deltas': self.deltas,
            'baseline_confidence': self.baseline_confidence,
            'candidate_confidence': self.candidate_confidence,
            'attribution_deltas': self.attribution_deltas,
            'verdict': self.verdict,
            'low_confidence': self.low_confidence,
            'comparability_warning': self.comparability_warning,
            'mismatches': self.mismatches,
            'failed_runs': self.failed_runs,
            'baseline_band': self.baseline_band,
        }


def _numeric_metrics(result: AnalysisResult) -> Dict[str, Optional[float]]:
    floors = result.floors or {}
    metrics: Dict[str, Optional[float]] = {'total_duration_us': result.total_duration_us}
    for key in _FLOOR_KEYS[1:]:
        metrics[key] = floors.get(key)
    return metrics


def _deltas(baseline: Dict[str, Optional[float]], candidate: Dict[str, Optional[float]]) -> Dict[str, Optional[float]]:
    deltas: Dict[str, Optional[float]] = {}
    for key in _FLOOR_KEYS:
        b, c = baseline.get(key), candidate.get(key)
        deltas[key] = (c - b) if (b is not None and c is not None) else None
    return deltas


def _attribution_deltas(
    baseline_attr: dict, candidate_attr: dict,
    baseline_total_us: int, candidate_total_us: int,
) -> Dict[str, dict]:
    """Per-category delta, both absolute (microseconds) and in
    percentage-points of each run's own total - a category that grows in
    absolute time but shrinks as a share of a much-larger total (or vice
    versa) is a real, distinguishable signal worth keeping separate."""
    categories = sorted(set(baseline_attr) | set(candidate_attr))
    result: Dict[str, dict] = {}
    for cat in categories:
        b_us = baseline_attr.get(cat, 0)
        c_us = candidate_attr.get(cat, 0)
        b_pct = (b_us / baseline_total_us * 100) if baseline_total_us > 0 else None
        c_pct = (c_us / candidate_total_us * 100) if candidate_total_us > 0 else None
        result[cat] = {
            'baseline_us': b_us,
            'candidate_us': c_us,
            'delta_us': c_us - b_us,
            'baseline_pct': b_pct,
            'candidate_pct': c_pct,
            'delta_pct_points': (c_pct - b_pct) if (b_pct is not None and c_pct is not None) else None,
        }
    return result


def _check_comparability(baseline_elements: List[Element], candidate_elements: List[Element]) -> Optional[str]:
    """Flag (don't block) when the two runs' graphs look like they might
    not even be the same project - less than half the element UIDs
    shared between them. An empty element list on either side means
    there's nothing to compare structurally, so it's silently skipped
    rather than warned about (a different, already-obvious problem)."""
    baseline_uids = {e.uid for e in baseline_elements}
    candidate_uids = {e.uid for e in candidate_elements}
    if not baseline_uids or not candidate_uids:
        return None
    overlap = baseline_uids & candidate_uids
    overlap_frac = len(overlap) / max(len(baseline_uids), len(candidate_uids))
    if overlap_frac < 0.5:
        return (
            f"baseline has {len(baseline_uids)} element(s), candidate has "
            f"{len(candidate_uids)} - only {len(overlap)} shared element UID(s) "
            "(less than half) - these runs may not be the same project"
        )
    return None


def _check_run_modes(
    baseline_result: AnalysisResult, candidate_result: AnalysisResult
) -> Optional[str]:
    """UX-55: flag (don't block) a comparison between a caches-off run
    and an incremental one.

    Returns None when both runs are the same mode, or when either does
    not say - `unknown` must not be guessed into either bucket, and a
    warning on every pre-UX-55 capture would train the reader to ignore
    the field.
    """
    modes = tuple(
        (result.confidence or {}).get('run_mode') for result in
        (baseline_result, candidate_result)
    )
    if 'unknown' in modes or None in modes or modes[0] == modes[1]:
        return None
    return (
        f"baseline is a {modes[0]} run and candidate is a {modes[1]} run - "
        "their durations and floors differ by however much the cache "
        "happened to hold, which says nothing about whether the build got "
        "worse; compare a nightly against a nightly and a pre-commit run "
        "against a pre-commit run"
    )


def _compare_results(
    baseline_result: AnalysisResult,
    candidate_result: AnalysisResult,
    baseline_elements: List[Element],
    candidate_elements: List[Element],
    baseline_band: Optional[dict] = None,
) -> ComparisonResult:
    baseline_metrics = _numeric_metrics(baseline_result)
    candidate_metrics = _numeric_metrics(candidate_result)
    deltas = _deltas(baseline_metrics, candidate_metrics)

    baseline_confidence = (baseline_result.confidence or {}).get('primary')
    candidate_confidence = (candidate_result.confidence or {}).get('primary')
    low_confidence = (
        baseline_confidence is None or baseline_confidence < _CONFIDENCE_HIGH
        or candidate_confidence is None or candidate_confidence < _CONFIDENCE_HIGH
    )

    # UX-78: both checks are recorded structurally as well as in prose.
    # They used to *only* flag, while README/guide promised a refusal -
    # and a golden fixture against a real run produced
    # `Verdict: REGRESSED (+105668.8%)`, exit 0, and exit 4 under the
    # gate, so a CI artifact-path bug read as "your build got slower".
    # The refusal itself lives in the CLI (it is an exit-code decision);
    # what belongs here is naming which check failed.
    mismatches: List[dict] = []
    comparability_warning = _check_comparability(baseline_elements, candidate_elements)
    if comparability_warning:
        mismatches.append({'check': 'shared_elements', 'message': comparability_warning})

    # UX-55: the two CI scenarios are not comparable to each other. A
    # caches-off nightly builds everything; a pre-commit run builds
    # whatever the change invalidated. Their total durations, floors and
    # occupancy differ by however much the cache happened to hold, which
    # has nothing to do with whether the build got worse. Flagged with
    # the same weight as "these may not be the same project", because it
    # is the same kind of mistake.
    mode_warning = _check_run_modes(baseline_result, candidate_result)
    if mode_warning:
        mismatches.append({'check': 'run_mode', 'message': mode_warning})
        comparability_warning = (
            f"{comparability_warning}; {mode_warning}" if comparability_warning
            else mode_warning
        )

    # UX-54: a run whose build failed is not a candidate for a
    # scheduling verdict at all.
    failed_runs = [
        name for name, res in (("baseline", baseline_result), ("candidate", candidate_result))
        if any(v.get('type') == 'build_failed' for v in (res.violations or []))
    ]

    baseline_total = baseline_metrics['total_duration_us']
    candidate_total = candidate_metrics['total_duration_us']
    delta_total_us = deltas['total_duration_us']

    if baseline_total is None or baseline_total <= 0 or delta_total_us is None:
        verdict = "not comparable (baseline has no measurable duration)"
    else:
        # Integer-only significance check: |delta|/baseline >= 1% <=>
        # |delta|*100 >= baseline*_SIGNIFICANCE_PCT - no float division
        # needed for the classification decision itself (Part 3.1's
        # discipline, applied here even though this isn't itself
        # timeline-accounting code, since it's driving a real decision).
        # UX-59: when enough baseline runs were supplied, judge against
        # their measured noise band instead of the fixed percentage. The
        # band is widened to the fixed rule when it is narrower - a set
        # of near-identical baseline runs yields a near-zero MAD, and a
        # band tighter than quantization noise would fire on everything.
        if baseline_band is not None:
            fixed_half_width = baseline_total * _SIGNIFICANCE_PCT / 100
            half_width = max(
                baseline_band['k'] * baseline_band['scaled_mad_us'], fixed_half_width
            )
            low = baseline_band['median_us'] - half_width
            high = baseline_band['median_us'] + half_width
            baseline_band = dict(baseline_band, low_us=low, high_us=high,
                                 widened_to_fixed_pct=half_width == fixed_half_width)
            significant = not (low <= candidate_total <= high)
        else:
            significant = abs(delta_total_us) * 100 >= baseline_total * _SIGNIFICANCE_PCT
        if not significant:
            verdict = "no significant change"
        elif delta_total_us < 0:
            verdict = "improved"
        else:
            verdict = "regressed"

    attribution_deltas = _attribution_deltas(
        baseline_result.attribution or {}, candidate_result.attribution or {},
        baseline_total or 0, candidate_total or 0,
    )

    return ComparisonResult(
        baseline_run_id=baseline_result.run_id,
        candidate_run_id=candidate_result.run_id,
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        deltas=deltas,
        baseline_confidence=baseline_confidence,
        candidate_confidence=candidate_confidence,
        attribution_deltas=attribution_deltas,
        verdict=verdict,
        low_confidence=low_confidence,
        comparability_warning=comparability_warning,
        mismatches=mismatches,
        failed_runs=failed_runs,
        baseline_band=baseline_band,
    )


def compare_runs(baseline_dir: Path, candidate_dir: Path,
                 baseline_runs: Optional[List[Path]] = None,
                 band_k: float = DEFAULT_BAND_K,
                 **analyzer_kwargs) -> ComparisonResult:
    """Load, analyze, and compare two run directories independently -
    each gets its own BuildEfficiencyAnalyzer instance (no shared state),
    matching how any two separate `bga analyze` invocations would behave.
    analyzer_kwargs are passed through to both (e.g. capacity override) -
    a caller comparing under a hypothetical capacity wants that applied
    symmetrically to both runs, not just one.
    """
    baseline_analyzer = BuildEfficiencyAnalyzer(**analyzer_kwargs)
    baseline_analyzer.load(baseline_dir)
    baseline_result = baseline_analyzer.analyze()

    candidate_analyzer = BuildEfficiencyAnalyzer(**analyzer_kwargs)
    candidate_analyzer.load(candidate_dir)
    candidate_result = candidate_analyzer.analyze()

    # UX-59: a baseline is a *set* when one is supplied. Each run is
    # analyzed the same way the two principals are, and one that does not
    # share the candidate's run_mode is refused rather than averaged in -
    # UX-55 already established that a nightly and a pre-commit run are
    # not comparable, and a band mixing them is that mistake with extra
    # arithmetic.
    band = None
    if baseline_runs:
        candidate_mode = (candidate_result.confidence or {}).get('run_mode')
        durations = []
        for run_dir in baseline_runs:
            analyzer = BuildEfficiencyAnalyzer(**analyzer_kwargs)
            analyzer.load(run_dir)
            result = analyzer.analyze()
            mode = (result.confidence or {}).get('run_mode')
            if candidate_mode not in (None, 'unknown') and mode not in (None, 'unknown') \
                    and mode != candidate_mode:
                raise ValueError(
                    f"baseline run {run_dir} is a {mode} run but the candidate is "
                    f"{candidate_mode} - a noise band may only be built from runs of "
                    "the same kind (UX-55)"
                )
            durations.append(result.total_duration_us)
        band = compute_band(durations, k=band_k)

    return _compare_results(
        baseline_result, candidate_result,
        baseline_analyzer.graph.elements, candidate_analyzer.graph.elements,
        baseline_band=band,
    )


def regression_exceeds_threshold(comparison: ComparisonResult, threshold_pct: Optional[float] = None) -> bool:
    """UX-03: the single, primary CI-gating question `bga compare
    --fail-on-regression` exists to answer - "did the candidate run's
    real total_duration_us (Part 4.3, UX-10) regress beyond
    threshold_pct% of the baseline's". Kept here (not cli.py) since it's
    comparison semantics, not command-line wiring - the CLI is only
    responsible for deciding what to *do* with the answer (exit code,
    the low-confidence fail-open rule).

    total_duration_us is chosen as the one primary metric (rather than
    an ambiguous multi-metric AND/OR) because it's the same real
    wall-clock number `compare_runs`'s own `verdict` field already
    gates on - "did the build get slower" is the natural top-level
    question a CI regression gate exists to answer, and reusing the
    exact same metric/formula the report already shows as `REGRESSED`
    means `--fail-on-regression` (with no threshold override) fails
    exactly when a human reading the report would call it a regression,
    never a second, silently-different definition.

    threshold_pct defaults to the same _SIGNIFICANCE_PCT `verdict`
    itself uses - an explicit override lets a CI pipeline set its own,
    stricter or looser, bar without changing what the report's own
    verdict text calls "regressed".
    """
    baseline_total = comparison.baseline_metrics.get('total_duration_us')
    delta_total = comparison.deltas.get('total_duration_us')
    if baseline_total is None or baseline_total <= 0 or delta_total is None:
        return False
    pct = _SIGNIFICANCE_PCT if threshold_pct is None else threshold_pct
    return delta_total > 0 and abs(delta_total) * 100 >= baseline_total * pct


# UX-39: how far `occupancy_ratio` (UX-27) may fall, in percentage
# points, before `--fail-on-efficiency-regression` fails a pipeline.
#
# Derived, not guessed. Three repeat captures of an *unchanged* project
# on one real runner (examples/06-macro-micro-optimization/optimized,
# `bst --builders 4 --max-jobs 4`, cache cleared between each):
#
#   run 1: wall 25.98s   occupancy 60.0%
#   run 2: wall 25.94s   occupancy 59.9%
#   run 3: wall 24.07s   occupancy 59.0%
#
# Occupancy spread across three identical builds: 1.0 percentage point.
# Wall-clock spread over the same three: 7.4% - i.e. more than seven
# times `_SIGNIFICANCE_PCT`, which is direct evidence that the existing
# duration gate's own default sits below this runner's noise floor.
#
# 5pp gives roughly 5x headroom over the measured noise while staying
# far below both real signals available: the macro+micro optimization
# moved occupancy 27.8% -> 63.0% (35.2pp), and running the same project
# oversubscribed at 8x8 on 4 cores moved it 63.0% -> 48.6% (14.4pp).
#
# This is one project on one runner and is documented as a starting
# point, not a universal constant - a CI owner should re-derive it the
# same way on their own runner, which is why `--max-efficiency-drop`
# exists.
_EFFICIENCY_DROP_PP = 5.0


def efficiency_regression_exceeds_threshold(
    comparison: ComparisonResult, max_drop_pp: Optional[float] = None,
) -> bool:
    """UX-39: "did this change make the build *less efficient*", as
    distinct from "did it make the build slower".

    Gates on `occupancy_ratio` (UX-27) because that is the one published
    metric invariant to how much work the build does: adding three
    well-parallelized elements barely moves it, adding three serialized
    ones moves it sharply. Wall-clock cannot express that - it moves for
    both - which is why the existing `--fail-on-regression` cannot say
    "new work is fine, new inefficiency is not".

    Expressed in percentage points rather than as a relative percentage:
    a 5% relative drop means something very different at 60% occupancy
    than at 10%, and the measured noise floor this is calibrated against
    is itself an absolute spread.

    Returns False when either run lacks the metric - never fabricates a
    verdict from missing data.
    """
    baseline = comparison.baseline_metrics.get('occupancy_ratio')
    candidate = comparison.candidate_metrics.get('occupancy_ratio')
    if baseline is None or candidate is None:
        return False
    drop_pp = (baseline - candidate) * 100
    threshold = _EFFICIENCY_DROP_PP if max_drop_pp is None else max_drop_pp
    return drop_pp >= threshold


def efficiency_below_floor(
    comparison: ComparisonResult, min_efficiency: Optional[float] = None,
) -> bool:
    """UX-39: an absolute floor on the candidate run's own
    `occupancy_ratio`, independent of any baseline.

    The delta gate alone ratchets - a slow drift of 2pp per change never
    trips it, and after twenty changes the build is unrecognisable. The
    floor is also what makes "we accept 55%, we do not accept 30%"
    expressible when there is no trustworthy baseline to compare against
    at all, which in CI is the normal case for a first run on a new
    branch.

    No default: a floor is a statement about what *this* project's owner
    considers acceptable, and there is no defensible universal value.
    """
    if min_efficiency is None:
        return False
    candidate = comparison.candidate_metrics.get('occupancy_ratio')
    if candidate is None:
        return False
    return candidate < min_efficiency
