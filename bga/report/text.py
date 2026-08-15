"""Human-readable text/CSV report formatting (Part 37)."""
from typing import List, Optional

from ..ingest.models import AnalysisResult
from ._shared import GRAPH_SIGNAL_KEYS

# Confidence-band labels for the Key Findings headline (P4-02) - a
# presentation-only heuristic, not a spec-defined threshold (Part 33
# defines the confidence *computation*, not a label banding on top of
# it). Picked so a passing analysis with no gate failures (confidence
# 1.0) reads "high" and a genuinely degraded one reads "low" - not a
# claim of statistical significance.
_CONFIDENCE_HIGH = 0.8
_CONFIDENCE_MEDIUM = 0.5


def _confidence_band(score: float) -> str:
    if score >= _CONFIDENCE_HIGH:
        return "high"
    if score >= _CONFIDENCE_MEDIUM:
        return "medium"
    return "low"


# efficiency_score bands (UX-02) - presentation-only, same status as the
# confidence bands above (a labeling heuristic, not a spec threshold).
# Deliberately distinct cut points from confidence's: 0.9/0.7 rather than
# 0.8/0.5, chosen so "very efficient" only applies once remaining
# scheduling headroom is genuinely small (under 10% of total duration),
# and "worth checking Certified Headroom" starts well before that (30%+
# headroom is real, actionable room, not noise).
_EFFICIENCY_HIGH = 0.9
_EFFICIENCY_MEDIUM = 0.7


def _efficiency_band(score: float) -> str:
    if score >= _EFFICIENCY_HIGH:
        return "very efficient - remaining gains are mostly in reducing Critical Path's own work, not scheduling"
    if score >= _EFFICIENCY_MEDIUM:
        return "worth checking Certified Headroom for real scheduling gains"
    return "meaningful scheduling headroom available"


def _format_violation_summary(violation: dict) -> str:
    """One-line, human-readable summary for a single violation dict -
    every `type` currently produced anywhere in bga/ (P4-02's own
    required "one-line-per-violation summary"). Falls back to a generic
    dump for an unrecognized future type rather than silently omitting
    it (this codebase's "no silent correction" philosophy)."""
    vtype = violation.get('type', 'unknown')
    if vtype == 'ordering_violation':
        return (
            f"ordering: {violation.get('predecessor')} finished after "
            f"{violation.get('successor')} started "
            f"(gap {violation.get('gap_us', 0) / 1e6:.3f}s)"
        )
    if vtype == 'attribution_reconciliation':
        return (
            f"attribution (I4) mismatch: residual "
            f"{violation.get('residual_us', 0) / 1e6:.3f}s "
            f"(sum {violation.get('attribution_sum_us', 0) / 1e6:.3f}s vs. "
            f"horizon {violation.get('horizon_us', 0) / 1e6:.3f}s)"
        )
    if vtype == 'hard_gate_failed':
        return f"hard gate failed: {violation.get('gate')} = {violation.get('value')}"
    return f"{vtype}: {violation}"


def _structural_kind_tag(entry: dict) -> str:
    """P4-12 Direction 2 / P4-15 Direction 2 (linked): a short, only-
    shown-when-relevant caveat for report listings ranking elements by a
    real, directly-observed signal (blast radius, criticality, etc.) -
    flags when the listed element is a BuildStream plugin kind that
    typically does no real compute work of its own (junction/import/
    filter/compose/stack - see bga.ingest.models.STRUCTURAL_ELEMENT_KINDS),
    so a reader can judge whether its own recorded duration means what
    they'd assume. Never hidden, never used to reorder or exclude - the
    ranking itself is untouched, this is purely an annotation.
    """
    if not entry.get('is_structural_kind'):
        return ''
    kind = entry.get('element_kind', 'unknown')
    return f" [structural: {kind}, may not reflect real compute work]"


def _format_key_findings(result: AnalysisResult) -> List[str]:
    """Synthesized "what to look at first" summary (P4-02) - presentation
    only, reads already-computed fields (result.confidence/.attribution/
    .floors/.signals), performs no new computation. Shown before the
    detailed sections in the full report so a reader gets the headline
    before the flat metric dump, not instead of it.
    """
    lines: List[str] = ["Key Findings:"]

    # Confidence headline
    confidence = result.confidence or {}
    primary = confidence.get('primary')
    violations = result.violations or []
    if primary is not None:
        band = _confidence_band(primary)
        if violations:
            lines.append(
                f"  Confidence: {primary:.2f} ({band}) - see {len(violations)} "
                f"violation(s) below"
            )
        else:
            lines.append(f"  Confidence: {primary:.2f} ({band})")

    # Biggest opportunity: largest non-EXECUTION_ON_CHAIN attribution
    # category, phrased as where the time actually went.
    attribution = result.attribution or {}
    total = result.total_duration_us
    non_execution = {
        k: v for k, v in attribution.items() if k != 'execution_on_chain_us'
    }
    if non_execution and total > 0:
        top_category, top_duration_us = max(non_execution.items(), key=lambda kv: kv[1])
        if top_duration_us > 0:
            pct = top_duration_us / total * 100
            label = top_category.replace('_us', '').replace('_', ' ').upper()
            lines.append(
                f"  Biggest Opportunity: {pct:.1f}% of wall-clock time is "
                f"{label} ({top_duration_us / 1e6:.2f}s)"
            )

    # Top elements by blast radius / criticality probability, when
    # diagnostics were actually run (Part 25/26) - already computed by
    # BuildEfficiencyAnalyzer._compute_diagnostics, just surfaced here.
    signals = result.signals or {}
    top_blast_radius = signals.get('top_blast_radius') or []
    if top_blast_radius:
        lines.append("  Elements Most Worth Optimizing First (by blast radius):")
        blast_radius = signals.get('blast_radius') or {}
        for i, elem_uid in enumerate(top_blast_radius[:3], start=1):
            entry = blast_radius.get(elem_uid, {})
            count = entry.get('downstream_count', 0)
            lines.append(f"    {i}. {elem_uid} ({count} downstream elements){_structural_kind_tag(entry)}")

    criticality = signals.get('criticality_probability') or {}
    if criticality:
        nonzero_critical = sorted(
            (item for item in criticality.items() if item[1].get('probability', 0) > 0),
            key=lambda kv: kv[1].get('probability', 0), reverse=True,
        )[:3]
        if nonzero_critical:
            lines.append("  Highest Criticality Elements:")
            for i, (elem_uid, data) in enumerate(nonzero_critical, start=1):
                pct = data.get('probability', 0) * 100
                lines.append(
                    f"    {i}. {elem_uid} ({pct:.0f}% probability of being on critical path)"
                    f"{_structural_kind_tag(data)}"
                )

    # Certified headroom, in plain language
    floors = result.floors or {}
    t_inf = floors.get('t_infinity_observed') or floors.get('t_infinity_observed_us', 0)
    lb_val = floors.get('lb') or floors.get('lb_us', 0)
    headroom = floors.get('certified_headroom') or floors.get('certified_headroom_us', 0)
    if headroom > 0:
        lines.append(
            f"  Certified Headroom: up to {headroom / 1e6:.2f}s available "
            f"(T∞={t_inf / 1e6:.2f}s, LB={lb_val / 1e6:.2f}s)"
        )

    # Efficiency score (UX-02): scheduling efficiency of the observed
    # work only - never presented alone without the "not work-minimality"
    # caveat, so a high score can't be misread as "nothing more to do"
    # (Critical Path is where that remaining opportunity would show up).
    # Gated on confidence per the same discipline as the comparison
    # verdict this score feeds elsewhere - low-confidence input gets an
    # explicit caveat rather than false precision.
    efficiency_score = floors.get('efficiency_score')
    if efficiency_score is not None:
        band = _efficiency_band(efficiency_score)
        caveat = ""
        if primary is not None and primary < _CONFIDENCE_HIGH:
            caveat = " - low-confidence data, treat with caution"
        lines.append(
            f"  Efficiency Score: {efficiency_score:.2f} ({band}){caveat}"
        )

    lines.append("")
    return lines


def _format_confidence_and_violations(result: AnalysisResult) -> List[str]:
    """Confidence/violations block (P4-02 requirement 1) - previously
    result.confidence/.violations (Part 33's hard/soft gates, P1-13) were
    fully populated but never printed in text output at all, only
    reachable via `--format json`."""
    lines: List[str] = []
    confidence = result.confidence or {}
    if confidence:
        lines.append("Confidence:")
        primary = confidence.get('primary')
        if primary is not None:
            lines.append(f"  Overall: {primary:.2f} ({_confidence_band(primary)})")
        hard_gates = confidence.get('hard_gates') or {}
        failed_gates = [name for name, passed in hard_gates.items() if not passed]
        if failed_gates:
            lines.append(f"  Failed Hard Gates: {', '.join(failed_gates)}")
        lines.append("")

    violations = result.violations or []
    if violations:
        lines.append(f"Violations ({len(violations)}):")
        for violation in violations:
            lines.append(f"  - {_format_violation_summary(violation)}")
        lines.append("")

    return lines


def _format_pipeline_overhead(result: AnalysisResult) -> List[str]:
    """Pipeline-level overhead block (P4-14) - BuildStream's own
    top-level "main:core activity" phases (Query cache, Resolving
    elements, etc.) are real work with a real elapsed cost, confirmed
    material on a real large-project rebuild (see
    docs/tasks/P4-14-cache-query-overhead-visibility.md), but they are
    not attributable to any individual element - only to the pipeline as
    a whole. This is deliberately a coarse, one-number-per-phase signal,
    never a fabricated per-element breakdown: BuildStream's own log
    doesn't provide more precision than this.
    """
    lines: List[str] = []
    overhead = getattr(result, 'pipeline_overhead', None) or {}
    phases = overhead.get('phases') or []
    if not phases:
        return lines

    lines.append("Pipeline Overhead (not attributable to individual elements):")
    for entry in phases:
        lines.append(f"  {entry.get('phase', '?'):25s} {entry.get('elapsed_us', 0) / 1e6:8.2f}s")
    total_us = overhead.get('total_us', 0)
    fraction = overhead.get('fraction_of_horizon')
    if fraction is not None:
        lines.append(f"  Total: {total_us / 1e6:.2f}s ({fraction * 100:.1f}% of total duration)")
    else:
        lines.append(f"  Total: {total_us / 1e6:.2f}s")
    lines.append("")
    return lines


def _format_by_kind_summary(result: AnalysisResult) -> List[str]:
    """`bga graph --by-kind` (P4-12 Direction 3) - aggregate stats
    grouped by BuildStream element_kind. Opt-in, additive, presentation
    only - see docs/tasks/P4-12-element-kind-based-heuristics.md.
    """
    lines: List[str] = []
    summary = getattr(result, 'element_kind_summary', None) or {}
    if not summary:
        return lines

    lines.append("By Element Kind:")
    for kind, entry in sorted(summary.items(), key=lambda kv: kv[1].get('total_duration_us', 0), reverse=True):
        lines.append(
            f"  {kind:15s} count={entry.get('count', 0):4d}  "
            f"total={entry.get('total_duration_us', 0) / 1e6:8.2f}s  "
            f"avg={entry.get('avg_duration_us', 0) / 1e6:8.2f}s"
        )
    lines.append("")
    return lines


def format_text(result: AnalysisResult, section: Optional[str] = None, by_kind: bool = False) -> str:
    """
    Format analysis results as human-readable text.

    Args:
        result: The AnalysisResult object from the analyzer
        section: Restrict output to one report section (see SECTIONS) -
            None (default) produces the full `analyze` report.
        by_kind: Show the element_kind aggregate summary (P4-12
            Direction 3, `bga graph --by-kind`) - opt-in, since it's
            extra detail beyond the default graph section.

    Returns:
        Formatted string suitable for terminal display
    """
    lines = []
    lines.append("=" * 60)
    lines.append("Build Efficiency Report")
    lines.append("=" * 60)
    lines.append(f"Run: {result.run_id}")
    lines.append(f"Total Duration: {result.total_duration_us / 1e6:.1f}s")
    lines.append("")

    # Key Findings (P4-02) - synthesized summary, shown first, full
    # report only (matches format_json's own confidence/violations
    # gating: section is None). Subcommand-specific outputs (graph/
    # floors/replay/utilisation/diagnostics) stay exactly as they were.
    if section is None:
        lines.extend(_format_key_findings(result))
        lines.extend(_format_confidence_and_violations(result))

    # Certified Floors (Parts 14-17)
    if section in (None, 'floors'):
        lines.append("Certified Floors:")
        floors = result.floors
        t_inf = floors.get('t_infinity_observed') or floors.get('t_infinity_observed_us', 0)
        lb_val = floors.get('lb') or floors.get('lb_us', 0)
        headroom = floors.get('certified_headroom') or floors.get('certified_headroom_us', 0)
        lines.append(f"  T∞ (observed critical path): {t_inf / 1e6:.2f}s")
        lines.append(f"  LB (resource lower bound):   {lb_val / 1e6:.2f}s")
        lines.append(f"  Certified Headroom:          {headroom / 1e6:.2f}s")
        t_replay = floors.get('t_c') or floors.get('t_replay_us')
        if t_replay is not None:
            lines.append(f"  T_C (replay makespan):       {t_replay / 1e6:.2f}s")
        efficiency_score = floors.get('efficiency_score')
        if efficiency_score is not None:
            lines.append(f"  Efficiency Score:            {efficiency_score:.2f} ({_efficiency_band(efficiency_score)})")
        if floors.get('t_infinity_cold') is not None:
            partial_note = " (partial, confidence=low)" if floors.get('cold_partial') else ""
            lines.append(f"  T∞,cold (advisory):          {floors['t_infinity_cold'] / 1e6:.2f}s{partial_note}")
        # P2-06: per-tier duration-source breakdown for the cold critical
        # path specifically - shown whenever cold analysis was attempted
        # at all (including the "unavailable" case, where it's the
        # diagnostic for *why*), not gated on t_infinity_cold being
        # published.
        cp_sources = floors.get('cold_critical_path_duration_sources')
        if cp_sources:
            parts = ", ".join(f"{count} {tier.replace('_', ' ').lower()}" for tier, count in sorted(cp_sources.items()))
            lines.append(f"  Cold critical path sources:  {parts}")
        lines.append("")

    # Attribution (Part 11-12) - full report only; `--format csv` already
    # serves this slice on its own for any subcommand.
    if section is None and hasattr(result, 'attribution') and result.attribution:
        lines.append("Attribution Breakdown:")
        total = result.total_duration_us
        for category, duration_us in result.attribution.items():
            pct = (duration_us / total * 100) if total > 0 else 0
            lines.append(f"  {category.replace('_', ' ').title():25s} {duration_us / 1e6:8.2f}s ({pct:5.1f}%)")
        lines.append("")

    # Replay (Part 18) - dedicated block for `bga replay RUN`; the
    # Certified Floors block above already shows T_C for the full report.
    if section == 'replay':
        lines.append("Replay:")
        t_replay = result.floors.get('t_c')
        model_slack = result.floors.get('model_slack')
        if t_replay is not None:
            lines.append(f"  T_C (replay makespan): {t_replay / 1e6:.2f}s")
        if model_slack is not None:
            lines.append(f"  Model Slack (T_C - LB): {model_slack / 1e6:.2f}s")
        lines.append("")

    # Critical Path (Part 14.1) - result.signals['critical_path'] is a
    # list of element UIDs (compute_critical_path's return shape), not
    # task objects; the previous version read a nonexistent
    # result.critical_path top-level attribute and an equally nonexistent
    # task_key.element_name, so this block never actually fired for any
    # input - a pre-existing dead-code bug, fixed here since P1-14's new
    # `graph` subcommand's whole purpose depends on this content existing.
    if section in (None, 'graph') and hasattr(result, 'signals') and result.signals.get('critical_path'):
        critical_path = result.signals['critical_path']
        lines.append(f"Critical Path Length: {len(critical_path)} elements")
        if len(critical_path) <= 5:
            lines.append(f"  Path: {' → '.join(critical_path)}")
        lines.append("")

    # Occupancy Stats (Part 4)
    if hasattr(result, 'occupancy_stats') and result.occupancy_stats:
        lines.append("Occupancy Statistics:")
        lines.append(f"  Max Parallelism: {result.occupancy_stats.get('max_parallelism', 0):.1f}x")
        lines.append(f"  Avg Parallelism: {result.occupancy_stats.get('avg_parallelism', 0):.1f}x")
        lines.append("")

    # CPU Utilisation (Part 30, M4)
    if section in (None, 'utilisation') and hasattr(result, 'utilisation') and result.utilisation:
        lines.append("CPU Utilisation:")
        util = result.utilisation
        if util.get('effective_cpus') is not None:
            lines.append(f"  Effective CPUs: {util['effective_cpus']}")
        if util.get('reconciliation_error_pct') is not None:
            lines.append(f"  Reconciliation Error: {util['reconciliation_error_pct']:.2f}%")
        buckets = util.get('buckets') or {}
        for bucket_name, bucket_us in buckets.items():
            lines.append(f"  {str(bucket_name).replace('_', ' ').title():20s} {bucket_us / 1e6:8.2f}s")
        lines.append("")

    # Diagnostics (Part 20-29, M5)
    if section in (None, 'diagnostics') and hasattr(result, 'signals') and result.signals:
        diagnostics_signals = {k: v for k, v in result.signals.items() if k not in GRAPH_SIGNAL_KEYS}
        if diagnostics_signals:
            lines.append("Advanced Diagnostics:")
            if 'blast_radius' in diagnostics_signals:
                br_data = diagnostics_signals['blast_radius']
                # Handle both dict format and dataclass format
                if isinstance(br_data, dict) and br_data:
                    max_blast = max((v.get('downstream_count', 0) if isinstance(v, dict) else getattr(v, 'blast_count', 0)) for v in br_data.values())
                    lines.append(f"  Max Blast Radius: {max_blast} downstream elements")
                elif isinstance(br_data, list) and br_data:
                    max_blast = max((br.blast_count for br in br_data if hasattr(br, 'blast_count')), default=0)
                    lines.append(f"  Max Blast Radius: {max_blast} downstream elements")
            if 'criticality_probability' in diagnostics_signals:
                cp_data = diagnostics_signals['criticality_probability']
                # Handle both dict format and dataclass format
                high_crit = 0
                if isinstance(cp_data, dict):
                    high_crit = sum(1 for v in cp_data.values() if (isinstance(v, dict) and v.get('probability', 0) > 0.5) or (hasattr(v, 'probability') and v.probability > 0.5))
                elif isinstance(cp_data, list):
                    high_crit = sum(1 for cp in cp_data if getattr(cp, 'probability', 0) > 0.5)
                lines.append(f"  High Criticality Elements: {high_crit} (>50% probability)")
            lines.append("")

    # Structural Analysis (M6) - shown alongside 'graph' since it's
    # graph-shape metrics (max_depth, parallelism, etc.); the spec's own
    # Part 37 command list has no dedicated `structural` subcommand.
    # result.structural is the actual field (_compute_structural_analysis's
    # return shape: metrics/bottleneck/parallelism/sensitivity/
    # deferrability/summary) - the previous version read a nonexistent
    # result.structural_metrics attribute and mismatched key names
    # ('bottlenecks'/'parallelism_profile' vs. the real 'bottleneck'/
    # 'parallelism'), so this block never actually fired either.
    if section in (None, 'graph') and hasattr(result, 'structural') and result.structural:
        sm = result.structural
        metrics = sm.get('metrics') or {}
        bottleneck = sm.get('bottleneck') or {}
        parallelism = sm.get('parallelism') or {}
        if metrics or bottleneck or parallelism:
            lines.append("Structural Analysis:")
            if metrics:
                lines.append(
                    f"  Elements: {metrics.get('num_elements', 0)}, "
                    f"Edges: {metrics.get('num_edges', 0)}, "
                    f"Max Depth: {metrics.get('max_depth', 0)}"
                )
            choke_points = bottleneck.get('choke_points') or []
            if choke_points:
                lines.append(f"  Bottlenecks Identified: {len(choke_points)}")
            if parallelism:
                lines.append(
                    f"  Parallelism Profile: min={parallelism.get('min_width', 0):.1f}x, "
                    f"max={parallelism.get('max_width', 0):.1f}x"
                )
            consolidation_candidates = sm.get('consolidation_candidates') or []
            if consolidation_candidates:
                lines.append(
                    f"  Stack-Consolidation Candidates: {len(consolidation_candidates)} "
                    f"group(s) of elements always consumed together with no `stack` "
                    f"grouping them (P4-15, structural signal only - not a timing "
                    f"estimate; see tools/bst_checkout_cost.py for real measurement):"
                )
                for candidate in consolidation_candidates[:5]:
                    lines.append(f"    - {', '.join(candidate['elements'])}")
            lines.append("")

    if section in (None, 'graph') and by_kind:
        lines.extend(_format_by_kind_summary(result))

    if section is None:
        lines.extend(_format_pipeline_overhead(result))

    lines.append("=" * 60)
    return "\n".join(lines)


def format_csv(result: AnalysisResult) -> str:
    """
    Format attribution results as CSV.

    Args:
        result: The AnalysisResult object from the analyzer

    Returns:
        CSV string with attribution breakdown
    """
    lines = ["category,duration_us,duration_s,percent"]
    total = result.total_duration_us

    if hasattr(result, 'attribution') and result.attribution:
        for category, duration_us in result.attribution.items():
            pct = (duration_us / total * 100) if total > 0 else 0
            lines.append(f"{category},{duration_us},{duration_us / 1e6:.6f},{pct:.2f}")

    return "\n".join(lines)


def format_sweep_text(resource: str, sweep_result) -> str:
    """Format a capacity_sweep result (Part 19) as human-readable text."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"Capacity Sweep: {resource}")
    lines.append("=" * 60)
    lines.append(f"{'Capacity':>10} {'T_C (s)':>12} {'Improvement':>14}")
    for entry in sweep_result.sweeps:
        cap = entry['capacity'].get(resource, '?')
        makespan_s = entry['makespan_us'] / 1e6
        improvement_pct = entry['normalized_improvement'] * 100
        lines.append(f"{cap:>10} {makespan_s:>12.2f} {improvement_pct:>13.1f}%")
    if sweep_result.knee_points:
        lines.append("")
        for res, knee in sweep_result.knee_points.items():
            lines.append(f"Knee point ({res}): capacity {knee} (diminishing returns beyond this)")
    if sweep_result.monotonicity_violations:
        lines.append("")
        lines.append("Monotonicity violations:")
        for violation in sweep_result.monotonicity_violations:
            lines.append(f"  {violation}")
    lines.append("=" * 60)
    return "\n".join(lines)
