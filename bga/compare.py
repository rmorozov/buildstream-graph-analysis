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
from dataclasses import dataclass
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
# floors-dict key (it's AnalysisResult's own field, the task horizon) -
# included here as the primary, most user-meaningful "did the build get
# faster" number; the rest are the certified/advisory floors themselves.
_FLOOR_KEYS = (
    'total_duration_us', 't_infinity_observed', 'lb', 'certified_headroom',
    't_c', 'efficiency_score',
)


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
            "(less than half) - these runs may not be the same project; "
            "treat any comparison below with real skepticism"
        )
    return None


def _compare_results(
    baseline_result: AnalysisResult,
    candidate_result: AnalysisResult,
    baseline_elements: List[Element],
    candidate_elements: List[Element],
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

    comparability_warning = _check_comparability(baseline_elements, candidate_elements)

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
    )


def compare_runs(baseline_dir: Path, candidate_dir: Path, **analyzer_kwargs) -> ComparisonResult:
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

    return _compare_results(
        baseline_result, candidate_result,
        baseline_analyzer.graph.elements, candidate_analyzer.graph.elements,
    )
