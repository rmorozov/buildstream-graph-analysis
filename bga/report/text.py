"""Human-readable text/CSV report formatting (Part 37)."""
from typing import List, Optional

from ..ingest.models import AnalysisResult
from ._shared import (
    GRAPH_SIGNAL_KEYS, SWEEP_CAPACITY_MODEL_CAVEAT, resolve_attribution_hint,
)

# Confidence-band labels for the Key Findings headline (P4-02) - a
# presentation-only heuristic, not a spec-defined threshold (Part 33
# defines the confidence *computation*, not a label banding on top of
# it). Picked so a passing analysis with no gate failures (confidence
# 1.0) reads "high" and a genuinely degraded one reads "low" - not a
# claim of statistical significance.
_CONFIDENCE_HIGH = 0.8
_CONFIDENCE_MEDIUM = 0.5

# UX-33: rendering thresholds, not analysis thresholds. A path at or
# below this length reads fine as a single `a → b → c` line; above it,
# the per-element form (duration + share of path) is what a reader
# actually needs. Either way the full chain is printed - the previous
# behavior withheld it entirely above 5 elements.
_CRITICAL_PATH_INLINE_MAX = 5
# Choke points are named, not counted. Capped only to keep one report
# line readable; the overflow is stated explicitly rather than silently
# dropped (this codebase's "no silent gaps" discipline).
_CHOKE_POINTS_SHOWN_MAX = 8


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
    """UX-27: the band text now names what this score does and does not
    cover. It measures how well the scheduler packed *the graph this run
    actually had*; it cannot see whether that graph was worth packing,
    because every input to it is derived from the observed graph. A build
    whose independent elements were accidentally chained scores 1.00 -
    correctly, by this definition, and uselessly. `Dispatch Occupancy`
    below is the signal that moves the other way."""
    if score >= _EFFICIENCY_HIGH:
        return (
            "scheduling is near the certified floor for this graph - further gains "
            "need the graph or the work itself to change, not the scheduler "
            "(see Dispatch Occupancy and Critical Path)"
        )
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
        base = f"hard gate failed: {violation.get('gate')} = {violation.get('value')}"
        detail = violation.get('detail')
        if detail:
            # UX-25: name the specific missing element(s), and the real
            # reason where the existing structural-kind heuristic
            # already explains it (P4-12) - never just the bare ratio.
            parts = []
            for d in detail:
                if d.get('is_structural_kind'):
                    reason = f"kind: {d.get('element_kind')}, structural - may not have a real compute task"
                else:
                    reason = "no matching task found - genuine coverage gap, worth investigating"
                parts.append(f"{d.get('element_uid')} ({reason})")
            base += " - missing: " + "; ".join(parts)
        return base
    if vtype == 'resource_oversubscription':
        ratio = violation.get('demand_ratio')
        ratio_text = f" ({ratio:.1f}x the cores)" if ratio else ""
        return (
            f"oversubscription: builders={violation.get('builders')} x "
            f"native max-jobs={violation.get('native_max_jobs')}{_auto_note(violation)} = "
            f"{violation.get('actual_demand')} potential concurrent processes "
            f"vs {_ceiling_desc(violation)}{ratio_text} - past the ratio UX-09 "
            f"measured as genuinely slower on a real host; real CPU contention "
            f"may be slowing individual tasks down (BuildStream's own "
            f"unconfigured default here would be {violation.get('default_demand')})"
        )
    if vtype == 'dispatch_oversubscription':
        # UX-28: distinct from the product check above, and sharper -
        # `builders` really are dispatched concurrently, whereas
        # `max-jobs` slots may never be claimed if an element has too
        # little parallel work to claim them.
        return (
            f"dispatch oversubscription: builders={violation.get('builders')} vs "
            f"{_ceiling_desc(violation)} - BuildStream dispatches that many "
            f"elements at once and each runs at least one process, so the host "
            f"is oversubscribed even at --max-jobs 1, see UX-09/UX-28"
        )
    if vtype == 'resource_undersubscription':
        return (
            f"undersubscription: builders={violation.get('builders')} x "
            f"native max-jobs={violation.get('native_max_jobs')}{_auto_note(violation)} = "
            f"{violation.get('actual_demand')} potential concurrent processes "
            f"vs {_ceiling_desc(violation)} - fewer than one process per core, "
            f"may be leaving cores idle"
        )
    if vtype == 'cpu_budget_exceeds_host_capacity':
        return (
            f"declared cpu_budget={violation.get('cpu_budget')} exceeds this "
            f"environment's detected host_cpu_count={violation.get('host_cpu_count')} "
            f"- the declared budget itself may be unrealistic here, see UX-15"
        )
    if vtype == 'memory_oversubscription':
        return (
            f"estimated memory oversubscription: builders={violation.get('builders')} x "
            f"native max-jobs={violation.get('native_max_jobs')}{_auto_note(violation)} x "
            f"~{violation.get('estimated_job_memory_mb')}MB/job (config-driven estimate, "
            f"not a real measurement) = ~{violation.get('estimated_demand_mb')}MB vs a "
            f"declared memory budget of {violation.get('memory_budget_mb')}MB - risk of "
            f"swap, a qualitatively worse failure mode than CPU contention, see UX-21"
        )
    return f"{vtype}: {violation}"


def _auto_note(violation: dict) -> str:
    """UX-16: a `resource_(over|under)subscription` violation's
    `native_max_jobs` field always holds the *resolved* value used in
    the demand math - when the operator actually declared BuildStream's
    own `--max-jobs 0` auto sentinel, say so, so the reader doesn't read
    "native max-jobs=4" as a literal `--max-jobs 4` the operator typed."""
    if violation.get('native_max_jobs_was_auto'):
        return " (resolved from --max-jobs=0's own auto sentinel)"
    return ""


def _ceiling_desc(violation: dict) -> str:
    """UX-15: the governing capacity ceiling a resource_(over|under)
    subscription violation was checked against - either the operator's
    declared cpu_budget or the environment's detected host_cpu_count,
    named accurately rather than always saying "host" (which would be
    wrong when a declared budget, not real hardware, is what governed
    the check)."""
    governing_cores = violation.get('governing_cores')
    if violation.get('capacity_source') == 'declared_cpu_budget':
        return f"a declared CPU budget of {governing_cores} cores"
    return f"a {governing_cores}-core host"


def _format_capacity_model_note(result: AnalysisResult) -> str:
    """UX-13: renders `AnalysisResult.floors['capacity_model_note']`
    (computed once in `BuildEfficiencyAnalyzer._build_capacity_model_note`
    - a single source of truth shared with `--format json`) as a report
    line. Always present - see that method's own docstring for why."""
    note = (result.floors or {}).get('capacity_model_note') or ""
    return f"  Note: {note}"


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
            # UX-04: explain what this category means and what to do
            # about it - previously a reader had no way to know from the
            # report itself that IDLE/RESOURCE_WAIT/SCHEDULER_WAIT are
            # three different problems with three different fixes.
            # UX-35: conditioned on this run's own capacity verdict.
            hint = resolve_attribution_hint(
                top_category, getattr(result, 'capacity_verdict', None),
            )
            if hint:
                lines.append(f"    -> {hint}")

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
        # UX-27: the graph-shape-aware companion to the score above.
        occupancy_ratio = floors.get('occupancy_ratio')
        if occupancy_ratio is not None:
            lines.append(
                f"  Dispatch Occupancy:          {occupancy_ratio * 100:.1f}% of available "
                f"slot-time used (unlike Efficiency Score, this falls when independent "
                f"work is serialized - see UX-27)"
            )
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
        lines.append(_format_capacity_model_note(result))
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
        # UX-33: the path is always printed now. It used to be withheld
        # above 5 elements, which suppressed it exactly when a reader
        # cannot hold it in their head - on a real 10-element chain the
        # report said "Critical Path Length: 10 elements" and nothing
        # else, while the chain itself (the entire finding) sat in the
        # JSON. Short paths keep the one-line arrow form; longer ones
        # get one element per line with its real measured duration and
        # share of the path, which is what answers "which link do I
        # attack first".
        detail = result.signals.get('critical_path_detail') or []
        if len(critical_path) <= _CRITICAL_PATH_INLINE_MAX:
            lines.append(f"  Path: {' → '.join(critical_path)}")
        elif detail:
            lines.append("  Path (chain order, with each element's real measured duration):")
            for entry in detail:
                share = entry.get('share_of_path')
                share_text = f"{share * 100:5.1f}% of path" if share is not None else "  n/a"
                structural = (
                    " [structural: {}, no build commands to speed up]".format(entry['element_kind'])
                    if entry.get('is_structural_kind') else ""
                )
                lines.append(
                    f"    {entry['element_uid']:<40s} {entry['duration_us'] / 1e6:7.2f}s "
                    f"({share_text}){structural}"
                )
        else:
            # No per-element detail available (an older run directory, or
            # a result built without normalized tasks) - print the chain
            # anyway rather than falling back to the bare length.
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
        util = result.utilisation
        # UX-36: the bucket totals are task-*occupancy* seconds (how long
        # each task held a dispatch slot), not CPU time. P1-33 established
        # that internally - "it was never actually a CPU-time
        # measurement, just labeled as CPU-microseconds" - and
        # `cpu_accounting_available` correctly gates every genuinely
        # CPU-derived field, but the report kept rendering the section
        # under a CPU heading with an `Effective CPUs` line. Read as CPU
        # time, a real optimization looked like it burned 53% more CPU
        # for identical work; it had simply overlapped tasks that used to
        # run one after another. Same report-honesty fix UX-13 applied to
        # the Certified Floors block: keep the numbers, name them
        # correctly.
        # `cpu_accounting_available` does NOT mean real CPU accounting
        # was present: UX-17 deliberately kept that name while widening
        # it to "some real capacity value is available", including a
        # merely *detected* host core count. `effective_cpus_source ==
        # "measured"` is the real discriminator (a genuine
        # cpu_accounting.effective_cpus or a cgroup quota/period).
        measured_cpu = util.get('effective_cpus_source') == 'measured'
        if measured_cpu:
            lines.append("CPU Utilisation:")
        else:
            lines.append("Dispatch Occupancy (no real CPU accounting in this run):")
        if util.get('effective_cpus') is not None:
            source = util.get('effective_cpus_source')
            # UX-36: `4.0` measured and `4.0` inferred from a detected
            # host core count are different claims and used to render
            # identically. UX-17 already computes the provenance.
            source_text = f" (source: {source})" if source else " (source: unknown)"
            label = "Effective CPUs" if measured_cpu else "Capacity"
            lines.append(f"  {label}: {util['effective_cpus']}{source_text}")
        if measured_cpu and util.get('reconciliation_error_pct') is not None:
            lines.append(f"  Reconciliation Error: {util['reconciliation_error_pct']:.2f}%")
        elif not measured_cpu:
            # Previously rendered as `Reconciliation Error: 0.00%`, which
            # implies something was reconciled. Nothing was: I9
            # reconciliation needs a real CPU measurement.
            lines.append("  Reconciliation: not performed (I9 needs real CPU accounting, absent here)")
        buckets = util.get('buckets') or {}
        if buckets:
            # True in every case, measured or not (P1-33): the buckets
            # are built from each task's real job-slot occupancy
            # (task.dur_us), never from a CPU-time measurement. Stated
            # here rather than left to the section heading, because a
            # reader who takes them for CPU seconds draws the opposite
            # conclusion from a real optimization - overlapping tasks
            # that used to run serially raises total occupancy while
            # doing identical work.
            lines.append("  Buckets below are task slot-time (occupancy), not CPU time:")
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
                # UX-33: name them. `Bottlenecks Identified: 5` with the
                # names only in the JSON was, on a real mis-shaped
                # project, the single most actionable output the tool
                # produced - reduced to an integer.
                shown = choke_points[:_CHOKE_POINTS_SHOWN_MAX]
                lines.append(
                    f"  Bottlenecks Identified: {len(choke_points)} - {', '.join(shown)}"
                    + (
                        f" (+{len(choke_points) - len(shown)} more, see --format json)"
                        if len(choke_points) > len(shown) else ""
                    )
                )
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
            # UX-20: sensitivity.top_opportunities was already computed
            # (Part 34's own docstring citation was stale - see
            # compute_sensitivity's docstring - this is a bga-specific
            # additive heuristic) but never rendered anywhere outside
            # --format json's structural.sensitivity key, making it
            # effectively invisible to a user reading the text report.
            sensitivity = sm.get('sensitivity') or {}
            top_opportunities = sensitivity.get('top_opportunities') or []
            if top_opportunities:
                lines.append(
                    f"  Top Improvement Opportunities (best-case speedup "
                    f"{sensitivity.get('best_case_speedup', 1.0):.2f}x if all "
                    f"{sensitivity.get('total_improvable_time_us', 0) / 1e6:.2f}s of "
                    f"improvable time were eliminated):"
                )
                for key, score, impact_pct in top_opportunities[:5]:
                    lines.append(
                        f"    - {key}: sensitivity {score:.2f} ({impact_pct:.1f}% impact)"
                    )
            # UX-34: say which candidates were filtered and why, rather
            # than silently shortening the ranking (same discipline as
            # UX-26's omitted-groups line).
            omitted_structural = sensitivity.get('omitted_structural_opportunities') or []
            if omitted_structural:
                lines.append(
                    "  ({} structural element(s) omitted - no build commands to speed up: {})".format(
                        len(omitted_structural),
                        ", ".join(
                            f"{o['element']} [{o['element_kind']}]" for o in omitted_structural[:5]
                        ),
                    )
                )
            # UX-20 (map-reduce tier): the real, simulated combined
            # effect of fixing several independent high-sensitivity
            # elements together in one batch, vs. serially discovering
            # and fixing them one bga-analyze iteration at a time - see
            # bga/structural/batching.py's own module docstring for the
            # "fixing = eliminate duration" definition this shares with
            # the sensitivity best-case-speedup figure above.
            batch_opportunities = sm.get('batch_opportunities') or {}
            batch_groups = batch_opportunities.get('groups') or []
            if batch_groups:
                lines.append("  Batch Opportunities (independent elements, simulated combined effect):")
                for group in batch_groups:
                    lines.append(
                        f"    - {', '.join(group['elements'])}: fixing all together -> "
                        f"makespan {group['baseline_makespan_us'] / 1e6:.2f}s -> "
                        f"{group['combined_makespan_us'] / 1e6:.2f}s "
                        f"(saves {group['combined_savings_us'] / 1e6:.2f}s combined, "
                        f"vs. {', '.join(f'{k}={v / 1e6:.2f}s' for k, v in group['individual_savings_us'].items())} fixed alone)"
                    )
            omitted_zero_savings_groups = batch_opportunities.get('omitted_zero_savings_groups') or []
            if omitted_zero_savings_groups:
                lines.append(
                    f"  ({len(omitted_zero_savings_groups)} further group(s) had no "
                    f"measurable combined effect, omitted)"
                )
            serialized_pairs = batch_opportunities.get('serialized_pairs') or []
            if serialized_pairs:
                lines.append(
                    "  Serialized (same dependency chain, not independently batchable): "
                    + "; ".join(f"{a} -> {b}" for a, b in serialized_pairs[:5])
                )
            # UX-22: real per-element `max-jobs` overrides that combine
            # a long measured duration with a near-full-core setting AND
            # genuine concurrent-dispatch potential under this run's real
            # `builders` value - see
            # bga/structural/serialization_points.py's own module
            # docstring for why this is a distinct risk from
            # _check_process_oversubscription's single-aggregate check.
            serialization_point_risks = sm.get('serialization_point_risks') or []
            if serialization_point_risks:
                lines.append(
                    "  Parallelism-Pinned Elements (UX-31 - running fewer native build "
                    "jobs than the rest of this build, and expensive enough for it to matter):"
                )
                for risk in serialization_point_risks:
                    lines.append(f"    - {risk['hint']}")
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


def format_sweep_text(resource: str, sweep_result, calibration_capacities: Optional[List[int]] = None) -> str:
    """Format a capacity_sweep result (Part 19) as human-readable text.

    `calibration_capacities` (UX-14 tier 2, PR #58's approved design):
    the real, distinct capacities the caller's `--calibration-dir` runs
    were captured at, if any were supplied - `None`/empty reproduces
    tier 1's own existing output exactly, unchanged.
    """
    has_contention_model = any('contention_model' in entry for entry in sweep_result.sweeps)
    lines = []
    lines.append("=" * 60)
    lines.append(f"Capacity Sweep: {resource}")
    lines.append("=" * 60)
    if has_contention_model:
        lines.append(f"{'Capacity':>10} {'T_C (s)':>12} {'Improvement':>14} {'Calibrated':>12}")
    else:
        lines.append(f"{'Capacity':>10} {'T_C (s)':>12} {'Improvement':>14}")
    for entry in sweep_result.sweeps:
        cap = entry['capacity'].get(resource, '?')
        makespan_s = entry['makespan_us'] / 1e6
        improvement_pct = entry['normalized_improvement'] * 100
        row = f"{cap:>10} {makespan_s:>12.2f} {improvement_pct:>13.1f}%"
        if has_contention_model:
            cm = entry.get('contention_model', {})
            calibrated = cm.get('calibrated_task_count', 0)
            total = cm.get('total_task_count', 0)
            extrapolated = cm.get('extrapolated_task_count', 0)
            suffix = f" ({extrapolated} extrap.)" if extrapolated else ""
            row += f" {f'{calibrated}/{total}':>12}{suffix}"
        lines.append(row)
    if sweep_result.knee_points:
        lines.append("")
        for res, knee in sweep_result.knee_points.items():
            lines.append(f"Knee point ({res}): capacity {knee} (diminishing returns beyond this)")
    if sweep_result.monotonicity_violations:
        lines.append("")
        lines.append("Monotonicity violations:")
        for violation in sweep_result.monotonicity_violations:
            lines.append(f"  {violation}")
    lines.append("")
    lines.append(f"Note: {SWEEP_CAPACITY_MODEL_CAVEAT}")
    if calibration_capacities:
        lines.append(
            f"Note: Contention-aware duration model active (UX-14 tier 2) - calibrated from real "
            f"captured runs at {resource} capacities {calibration_capacities}. The \"Calibrated\" "
            f"column above shows how many of the run's tasks actually got a real, interpolated "
            f"duration at each swept capacity vs. still using tier 1's fixed, uncalibrated one; "
            f"\"extrap.\" marks capacities outside the calibrated range, where the nearest real "
            f"endpoint's duration was kept rather than projected forward."
        )
    lines.append("=" * 60)
    return "\n".join(lines)


def _fmt_us(value_us: Optional[float]) -> str:
    return f"{value_us / 1e6:.2f}s" if value_us is not None else "n/a"


def _fmt_signed_us(delta_us: Optional[float], pct: Optional[float] = None) -> str:
    if delta_us is None:
        return "n/a"
    sign = "+" if delta_us >= 0 else ""
    text = f"{sign}{delta_us / 1e6:.2f}s"
    if pct is not None:
        text += f", {sign}{pct:.1f}%"
    return text


def format_compare_text(comparison) -> str:
    """Format a ComparisonResult (UX-01) as human-readable text. Takes
    the dataclass directly (not AnalysisResult) - this is a genuinely
    different report shape (two runs, deltas, a verdict), not a slice of
    one AnalysisResult like every other format_* function here."""
    b = comparison.baseline_metrics
    c = comparison.candidate_metrics
    d = comparison.deltas

    lines = ["=" * 60, "Run Comparison", "=" * 60]
    lines.append(f"Baseline:  {comparison.baseline_run_id or '(no run identity)'}")
    lines.append(f"Candidate: {comparison.candidate_run_id or '(no run identity)'}")
    lines.append("")

    baseline_total = b.get('total_duration_us')
    delta_total = d.get('total_duration_us')
    pct = (delta_total / baseline_total * 100) if (baseline_total and delta_total is not None) else None
    verdict_line = f"Verdict: {comparison.verdict.upper()}"
    if pct is not None:
        verdict_line += f"  (total duration {_fmt_signed_us(delta_total, pct)}, {_fmt_us(baseline_total)} -> {_fmt_us(c.get('total_duration_us'))})"
    lines.append(verdict_line)
    if comparison.low_confidence:
        lines.append("  Caveat: at least one run's confidence is below the 'high' band - treat this comparison with caution.")
    if comparison.comparability_warning:
        lines.append(f"  Warning: {comparison.comparability_warning}")
    lines.append("")

    lines.append("Certified Floors:")
    floor_labels = [
        ('total_duration_us', 'Total Duration'),
        ('t_infinity_observed', 'T∞ (observed)'),
        ('lb', 'LB'),
        ('certified_headroom', 'Certified Headroom'),
        ('t_c', 'T_C (replay)'),
    ]
    for key, label in floor_labels:
        if b.get(key) is None and c.get(key) is None:
            continue
        lines.append(f"  {label:20s} {_fmt_us(b.get(key)):>10s} -> {_fmt_us(c.get(key)):>10s}   ({_fmt_signed_us(d.get(key))})")
    if b.get('efficiency_score') is not None or c.get('efficiency_score') is not None:
        be = b.get('efficiency_score')
        ce = c.get('efficiency_score')
        de = d.get('efficiency_score')
        be_s = f"{be:.2f}" if be is not None else "n/a"
        ce_s = f"{ce:.2f}" if ce is not None else "n/a"
        de_s = f"{'+' if de is not None and de >= 0 else ''}{de:.2f}" if de is not None else "n/a"
        lines.append(f"  {'Efficiency Score':20s} {be_s:>10s} -> {ce_s:>10s}   ({de_s})")
    # UX-27: shown as a percentage, and shown right below Efficiency
    # Score deliberately - on a real optimization the two move in
    # opposite directions, and seeing that side by side is the whole
    # point of publishing a second signal.
    if b.get('occupancy_ratio') is not None or c.get('occupancy_ratio') is not None:
        bo = b.get('occupancy_ratio')
        co = c.get('occupancy_ratio')
        do = d.get('occupancy_ratio')
        bo_s = f"{bo * 100:.1f}%" if bo is not None else "n/a"
        co_s = f"{co * 100:.1f}%" if co is not None else "n/a"
        do_s = (
            f"{'+' if do is not None and do >= 0 else ''}{do * 100:.1f}pp"
            if do is not None else "n/a"
        )
        lines.append(f"  {'Dispatch Occupancy':20s} {bo_s:>10s} -> {co_s:>10s}   ({do_s})")
    lines.append("")

    lines.append("Confidence:")
    bc = comparison.baseline_confidence
    cc = comparison.candidate_confidence
    lines.append(f"  Baseline:  {f'{bc:.2f} ({_confidence_band(bc)})' if bc is not None else 'n/a'}")
    lines.append(f"  Candidate: {f'{cc:.2f} ({_confidence_band(cc)})' if cc is not None else 'n/a'}")
    lines.append("")

    if comparison.attribution_deltas:
        lines.append("Attribution Deltas:")
        for category, entry in comparison.attribution_deltas.items():
            label = category.replace('_', ' ').title()
            b_pct = f"{entry['baseline_pct']:.1f}%" if entry['baseline_pct'] is not None else "n/a"
            c_pct = f"{entry['candidate_pct']:.1f}%" if entry['candidate_pct'] is not None else "n/a"
            delta_pp = entry['delta_pct_points']
            delta_pp_s = f"{'+' if delta_pp is not None and delta_pp >= 0 else ''}{delta_pp:.1f}pp" if delta_pp is not None else "n/a"
            lines.append(
                f"  {label:25s} {_fmt_us(entry['baseline_us']):>8s} ({b_pct:>6s}) -> "
                f"{_fmt_us(entry['candidate_us']):>8s} ({c_pct:>6s})   {_fmt_signed_us(entry['delta_us'])} ({delta_pp_s})"
            )
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
