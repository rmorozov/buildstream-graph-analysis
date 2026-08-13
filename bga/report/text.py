"""Human-readable text/CSV report formatting (Part 37)."""
from typing import Optional

from ..ingest.models import AnalysisResult
from ._shared import GRAPH_SIGNAL_KEYS


def format_text(result: AnalysisResult, section: Optional[str] = None) -> str:
    """
    Format analysis results as human-readable text.

    Args:
        result: The AnalysisResult object from the analyzer
        section: Restrict output to one report section (see SECTIONS) -
            None (default) produces the full `analyze` report.

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
        if floors.get('t_infinity_cold') is not None:
            partial_note = " (partial, confidence=low)" if floors.get('cold_partial') else ""
            lines.append(f"  T∞,cold (advisory):          {floors['t_infinity_cold'] / 1e6:.2f}s{partial_note}")
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
            lines.append("")

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
