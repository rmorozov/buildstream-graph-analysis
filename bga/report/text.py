"""Human-readable text/CSV report formatting (Part 37)."""
from typing import List, Optional

from .. import findings as findings_mod
from ..findings import compute_findings, render_findings
from ..ingest.models import AnalysisResult
from ._shared import GRAPH_SIGNAL_KEYS, SWEEP_CAPACITY_MODEL_CAVEAT

# Confidence-band labels for the Key Findings headline (P4-02) - a
# presentation-only heuristic, not a spec-defined threshold (Part 33
# defines the confidence *computation*, not a label banding on top of
# it). Picked so a passing analysis with no gate failures (confidence
# 1.0) reads "high" and a genuinely degraded one reads "low" - not a
# claim of statistical significance.
# UX-75: these live in `bga/findings.py` now, with everything else that
# decides *what is worth saying*. Re-exported under their historic names
# because they are a stable surface for tests and callers, and because a
# rename would say something changed when nothing did.
_CONFIDENCE_HIGH = findings_mod._CONFIDENCE_HIGH
_CONFIDENCE_MEDIUM = findings_mod._CONFIDENCE_MEDIUM
_EFFICIENCY_HIGH = findings_mod._EFFICIENCY_HIGH
_EFFICIENCY_MEDIUM = findings_mod._EFFICIENCY_MEDIUM
_OPPORTUNITY_FLOOR_PCT = findings_mod.OPPORTUNITY_FLOOR_PCT
_CHAIN_BOUND_RATIO = findings_mod.CHAIN_BOUND_RATIO
_confidence_band = findings_mod.confidence_band
_efficiency_band = findings_mod.efficiency_band
_structural_kind_tag = findings_mod.structural_kind_tag
_heaviest_on_path = findings_mod.heaviest_on_path
_path_elements_by_duration = findings_mod.path_elements_by_duration

_CRITICAL_PATH_INLINE_MAX = 5
# UX-92: an invalidation with twenty independent roots is a different
# problem from one with a single root, and the reader needs to see that
# it is - but not twenty lines of it.
_INVALIDATION_ROOTS_SHOWN = 3
_CHOKE_POINTS_SHOWN_MAX = 8


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
    if vtype == 'floor_below_longest_task':
        return (
            f"I3 violated: T-infinity,observed "
            f"{violation.get('t_infinity_observed_us', 0) / 1e6:.3f}s is shorter "
            f"than the longest single observed task "
            f"({violation.get('longest_task_us', 0) / 1e6:.3f}s) - "
            f"{violation.get('detail')}"
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


def _format_key_findings(result: AnalysisResult) -> List[str]:
    """Synthesized "what to look at first" summary (P4-02).

    `UX-75`: this used to *be* the synthesis - every conclusion the tool
    draws was computed here, rendered, and thrown away, so a machine
    consumer had to re-derive `_heaviest_on_path`'s structural exclusion
    and four thresholds from this file's source to reach what a human
    read for free. The synthesis moved to `bga/findings.py`, which both
    renderers consume; this decides only how to say it.

    A consequence worth stating: a finding `compute_findings` does not
    produce cannot appear in either format, and one it does produce
    appears in both. That is the property, not a side effect.
    """
    return ["Key Findings:"] + render_findings(compute_findings(result)) + [""]


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
    docs/backlog/tasks/P4-14-cache-query-overhead-visibility.md), but they are
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
    only - see docs/backlog/tasks/P4-12-element-kind-based-heuristics.md.
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
        # UX-48: the two idle buckets recommend opposite fixes, so
        # whichever one dominates is the actionable part of this block.
        # Naming that here rather than leaving a reader to infer it from
        # two similar-looking numbers.
        underparallel_us = buckets.get('idle_underparallel', 0)
        no_tasks_us = buckets.get('idle_no_tasks', 0)
        if underparallel_us > 0:
            lines.append(
                f"  -> {underparallel_us / 1e6:.2f}s of that idle capacity had work "
                f"ready and waiting for a builder: raising build concurrency is the "
                f"lever here (`bga sweep` estimates the payoff)."
            )
        if no_tasks_us > underparallel_us and no_tasks_us > 0:
            lines.append(
                f"  -> {no_tasks_us / 1e6:.2f}s had nothing ready to run at all - no "
                f"amount of extra concurrency helps that; it is a dependency-graph "
                f"shape problem."
            )
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
                # UX-49: `mean_width` is the number that actually answers
                # "how parallel is this graph" - it is average
                # parallelism, work over depth - and it was the one the
                # line did not show. On the real examples/06 pair it
                # reads 1.1x for the chained baseline against 2.2x for
                # the fan-out, which is exactly the macro improvement
                # that project exists to demonstrate.
                lines.append(
                    f"  Parallelism Profile: min={parallelism.get('min_width', 0):.1f}x, "
                    f"avg={parallelism.get('mean_width', 0):.1f}x, "
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
                # UX-44: the numbers here used to be derived from a
                # placeholder slack of `duration * 0.5`, which made the
                # ranking an inverted duration sort and rendered a sum
                # over *work* (2828s) as though it were wall-clock on a
                # 362s build, three orders of magnitude away from the
                # `Certified Headroom` line above it. Both quantities
                # are now real, and both are named for what they are:
                # per-element savings in seconds off the finish, and a
                # structural ceiling that is explicitly not the
                # certified one.
                critical_path_us = sensitivity.get('critical_path_us') or 0
                improvable_us = sensitivity.get('total_improvable_time_us', 0)
                speedup = sensitivity.get('best_case_speedup')
                # None means every element is on the critical path, so
                # the ceiling is unbounded rather than 1.0 - see
                # SensitivityResult.best_case_speedup.
                ceiling = (
                    f"{speedup:.2f}x" if speedup is not None
                    else "unbounded (every element is on the critical path)"
                )
                lines.append(
                    f"  Top Improvement Opportunities (critical path "
                    f"{critical_path_us / 1e6:.2f}s; structural ceiling "
                    f"{ceiling}, i.e. up to {improvable_us / 1e6:.2f}s off it "
                    f"if every critical-path element were free):"
                )
                for key, score, impact_pct in top_opportunities[:5]:
                    lines.append(
                        f"    - {key}: up to {score * critical_path_us / 1e6:.2f}s "
                        f"off the finish ({impact_pct:.1f}%)"
                    )
                lines.append(
                    "    (graph-only upper bound, not a target: each saving is capped "
                    "where the next path becomes critical, and the savings are not "
                    "additive. `Certified Headroom` above is the measured, certified "
                    "figure - these two answer different questions.)"
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
                # UX-74: this answers "can these be worked concurrently"
                # - a fact about the graph, and about people. Whether the
                # savings *add* is `joint_saving` in Key Findings, which
                # is simulated in the same longest-path model as
                # `realizable_saving_us`; the figures below come from the
                # replay scheduler and are not the same quantity.
                lines.append(
                    "  Independently workable together (graph-independent elements; "
                    "replay-model combined effect, not the longest-path joint saving "
                    "in Key Findings):"
                )
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


def _plane2_knee_caveat(plane2_capacity: Optional[dict], knee) -> List[str]:
    """What Plane 2 knows about whether the knee is reachable (`UX-83`).

    Measured once on a real dual-plane capture: the sweep put the knee at
    capacity 5 on a 4-core host whose elements were already runnable at
    16 potential compiler processes, while the same capture's `correlate`
    output named a `-j1`-pinned element as the actual fix.
    """
    plane2 = plane2_capacity or {}
    cores_busy, host = plane2.get('cores_busy'), plane2.get('host_cpu_count')
    if cores_busy is None or not host:
        return []
    lines = [
        f"  Plane 2 measured {cores_busy:.2f} of {host} cores busy over this run"
        + (" - the host was already CPU-saturated" if plane2.get('saturated') else "")
    ]
    if plane2.get('saturated'):
        lines.append(
            "  The knee above is a replay-model answer and the replay model does "
            "not know about CPU (UX-09/UX-14): raising capacity past what the host "
            "can actually run adds contention, not throughput."
        )
    pinned = plane2.get('pinned_elements') or []
    if pinned:
        lines.append(
            "  Free capacity you already have: "
            + ", ".join(pinned[:3])
            + " asked its native build for -j1."
        )
    return lines


def format_sweep_text(resource: str, sweep_result, calibration_capacities: Optional[List[int]] = None, plane2_capacity: Optional[dict] = None) -> str:
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
            # UX-83: the knee is a property of the replay model, which
            # does not know about CPU. When Plane 2 measured this same
            # run, say what it measured - a knee above a saturated host
            # is a scheduling answer to a contention question.
            for line in _plane2_knee_caveat(plane2_capacity, knee):
                lines.append(line)
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
    # UX-59: a gate that fires must state the band it fired against, or
    # it cannot be argued with.
    band = comparison.baseline_band
    if band:
        width = "widened to the fixed 1% rule" if band.get('widened_to_fixed_pct') else (
            f"median {_fmt_us(band['median_us'])} +/- "
            f"{band['k']:g}x{_fmt_us(band['scaled_mad_us'])} (scaled MAD)"
        )
        lines.append(
            f"  Judged against a noise band from {band['n']} baseline run(s): "
            f"{_fmt_us(band['low_us'])} .. {_fmt_us(band['high_us'])} - {width}"
        )
    # UX-79: what this change added, and how much of it landed on the
    # chain. Said next to the verdict, because "the build got slower" and
    # "the build got slower *because you serialized the new work*" are
    # the same line to a reader who only sees the first.
    marginal = getattr(comparison, 'marginal_efficiency', None)
    if marginal:
        added = ", ".join(marginal['added_elements'][:4])
        more = (
            f" (+{len(marginal['added_elements']) - 4} more)"
            if len(marginal['added_elements']) > 4 else ""
        )
        lines.append(
            f"  New this change: {added}{more} - "
            f"{marginal['added_work_us'] / 1e6:.1f}s of work added, "
            f"{marginal['added_critical_path_us'] / 1e6:.1f}s of it on the critical "
            f"path (stretch {marginal['stretch']:.2f})"
        )
        if marginal['on_critical_path']:
            lines.append(
                "    on the path: " + ", ".join(marginal['on_critical_path'][:4])
            )

    # UX-92: what the cache did between these two runs. Placed after the
    # marginal block because both answer "what did this change cost",
    # and the cache answer is the one nothing in the tool could give
    # before: every other signal describes the work the build did, so a
    # change that quintuples the work while running efficiently reads as
    # fine everywhere else.
    churn = getattr(comparison, 'cache_churn', None)
    if churn and churn.get('applicable') is False:
        # UX-93: silence would be indistinguishable from an all-clear.
        # One line, and it names the precondition rather than the
        # finding it declined to make.
        lines.append(f"  Cache churn not assessed: {churn['explanation']}")
    elif churn:
        if churn.get('rebuilt_in_both_count'):
            named = ", ".join(churn['rebuilt_in_both_elements'][:4])
            more = (
                f" (+{churn['rebuilt_in_both_count'] - 4} more)"
                if churn['rebuilt_in_both_count'] > 4 else ""
            )
            lines.append(
                f"  Cache retention: {churn['rebuilt_in_both_count']} element(s) "
                f"rebuilt in BOTH runs with the same cache key, costing "
                f"{churn['rebuilt_in_both_us'] / 1e6:.1f}s here - {named}{more}. The "
                f"artifact is not surviving between runs (deliberate cut, eviction, "
                f"or a remote that is not serving it): a question about the cache, "
                f"not about the project"
            )
        if churn.get('churned_count'):
            named = ", ".join(churn['churned_elements'][:4])
            more = (
                f" (+{churn['churned_count'] - 4} more)"
                if churn['churned_count'] > 4 else ""
            )
            lines.append(
                f"  Cache churn: {churn['churned_count']} element(s) rebuilt with an "
                f"unchanged cache key, costing "
                f"{churn['wasted_rebuild_us'] / 1e6:.1f}s - {named}{more}. Nothing "
                f"they depend on changed, so that time bought nothing"
            )
        for root in (churn.get('invalidation_roots') or [])[:_INVALIDATION_ROOTS_SHOWN]:
            total_us = root['duration_us'] + root['downstream_us']
            downstream = (
                f" and invalidated {root['downstream_rebuilt']} element(s) below it"
                if root['downstream_rebuilt'] else " and invalidated nothing below it"
            )
            lines.append(
                f"  Invalidated at {root['element_uid']}: its cache key changed "
                f"({root['baseline_cache_key'][:8]} -> "
                f"{root['candidate_cache_key'][:8]}){downstream}, "
                f"{total_us / 1e6:.1f}s of rebuilding in total. Nothing it depends on "
                f"changed, so the change starts here"
            )
        extra = len(churn.get('invalidation_roots') or []) - _INVALIDATION_ROOTS_SHOWN
        if extra > 0:
            lines.append(
                f"    (+{extra} more independent invalidation root(s), see --format json)"
            )

    # UX-81: a band that could not be built used to be silent, so a
    # pipeline that asked for one got the fixed rule it was trying to
    # replace and no way to know. Name the shortfall and what closes it.
    shortfall = getattr(comparison, 'baseline_band_shortfall', None)
    if shortfall:
        lines.append(
            f"  No noise band: {shortfall['supplied']} baseline run(s) supplied, "
            f"{shortfall['required']} required - "
            f"{shortfall['required'] - shortfall['supplied']} more of the same shape "
            f"would replace the fixed 1% significance rule used here"
        )
    if comparison.low_confidence:
        lines.append("  Caveat: at least one run's confidence is below the 'high' band - treat this comparison with caution.")
    if comparison.comparability_warning:
        # UX-78: reaching this text at all means `--allow-mismatch` was
        # passed - the default is now a refusal, printed instead of the
        # comparison rather than beside it - so the caveat belongs here,
        # where there really is a comparison below it.
        lines.append(f"  Warning: {comparison.comparability_warning}")
        lines.append("  (--allow-mismatch was given; treat every figure below with real skepticism)")
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
