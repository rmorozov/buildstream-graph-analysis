"""Human-readable text/CSV report formatting (Part 37)."""
from typing import List, Optional

from .. import findings as findings_mod
from .. import sources
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

# UX-187: how much of a list-shaped section may scroll before the rest
# is folded behind a flag. Measured rather than guessed: on a 402-element
# chain the critical path rendered **405 of the report's 498 lines** -
# 81% of everything - and the four sections a reader actually acts on
# were below it. The numbers here are what a terminal shows without
# scrolling, split head and tail because a chain's two ends are the two
# places an optimizer starts.
#
# Nothing is truncated silently: every elision names its own count and
# the flag that undoes it (`UX-160`'s standing lesson - a reader cannot
# act on a number they do not know is missing).
_PATH_HEAD = 12
_PATH_TAIL = 8
_SHARED_SOURCE_ROWS = 10


def _elision(hidden: int, flag: str, what: str = "element(s)") -> str:
    return f"    ... {hidden} more {what} ({flag} to print all)"


def _head_and_tail(items, head: int, tail: int, full: bool = False):
    """`(items_to_render, index_the_elision_goes_before)`.

    A chain's two ends are where an optimizer starts - the root that
    everything waits on, and the last link before the build finishes -
    so the middle is what folds. Returns `(items, None)` unchanged when
    the list already fits or the caller asked for all of it, so the
    common case pays nothing.
    """
    if full or len(items) <= head + tail:
        return list(items), None
    return list(items[:head]) + list(items[-tail:]), head
# UX-92: an invalidation with twenty independent roots is a different
# problem from one with a single root, and the reader needs to see that
# it is - but not twenty lines of it.
_INVALIDATION_ROOTS_SHOWN = 3
_CHOKE_POINTS_SHOWN_MAX = 8


def _format_instance(instance: dict) -> str:
    """UX-95: one line naming a capture, from whichever facts it kept.

    Both halves are optional and the renderer says only what it has - a
    run directory with no wall clock genuinely has no capture time, and
    "unknown" beside a real path reads worse than the path alone.
    """
    return "  ".join(
        instance[key] for key in ('started_at', 'run_dir') if instance.get(key)
    )


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

    lines.extend(_format_timestamp_resolution(result))

    violations = result.violations or []
    if violations:
        lines.append(f"Violations ({len(violations)}):")
        for violation in violations:
            lines.append(f"  - {_format_violation_summary(violation)}")
        lines.append("")

    return lines


def _format_timestamp_resolution(result: AnalysisResult) -> List[str]:
    """UX-110: how far every duration above can be from the truth, when
    that distance is large enough to change a reading.

    Silent on a run whose tasks are long relative to the lag, which is
    every real build - a resolution line on a forty-minute compile is
    furniture. It speaks when a task is short enough for the lag to be a
    material share of it, and always when a task is reported as *shorter*
    than BuildStream's own timing of it, which is not imprecision but a
    duration that provably did not happen.
    """
    agreement = getattr(result, 'timestamp_agreement', None) or {}
    resolution = agreement.get('resolution_s')
    if not resolution:
        return []
    provably_short = agreement.get('tasks_shorter_than_bst') or 0
    material = agreement.get('tasks_where_material') or 0
    if not provably_short and not material:
        return []
    share = (agreement.get('material_share') or 0.05) * 100
    lines = [
        f"  Duration resolution: ±{resolution:.2f}s, measured - each task's length "
        f"is in this capture twice (the wrapped log's own timestamps, stamped when "
        f"the wrapper read each line, against BuildStream's own elapsed) and "
        f"{agreement['tasks_compared']} task(s) were compared",
    ]
    if material:
        lines.append(
            f"    that is more than {share:.0f}% of the duration for "
            f"{material} of {agreement.get('tasks_measured', material)} measured "
            f"task(s) - the shortest is {agreement['shortest_task_s']:.2f}s"
        )
    if provably_short:
        worst = (agreement.get('shorter_than_bst') or [{}])[0]
        lines.append(
            f"    {provably_short} task(s) are reported SHORTER than BuildStream's "
            f"own timing of them"
            + (f" - {worst.get('element')} at {worst['span_s']:.3f}s against "
               f"{worst['bst_elapsed_s']:.0f}s" if worst.get('span_s') is not None
               else "")
            + ", which is a duration that did not happen rather than one measured "
              "imprecisely (UX-110)"
        )
    return lines + [""]


def _attribution_label(category: str) -> str:
    """The attribution categories are stored with the `_us` suffix their
    schema field carries. Titled naively that renders as "Execution On
    Chain Us" beside a value printed in *seconds* - a label that names
    one unit next to a number in another. The suffix is dropped here
    rather than in the model, where it is part of the contract."""
    if category.endswith("_us"):
        category = category[: -len("_us")]
    return category.replace("_", " ").title()


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


def _format_resource_blast(result, full_sections=frozenset()) -> List[str]:
    """UX-171: which repository feeds which elements, and what it costs.

    Silent when the run carries no inventory (a capture from before
    UX-171, or one extracted without its project) and when nothing is
    shared - a project of per-element `local` sources has no resource
    row to print, and printing an empty table would suggest it had been
    looked for and found wanting.

    The cost column is *work*, not wall clock: it is the sum of the
    blast elements' own durations, which a build with any parallelism
    at all completes in less. Labelled where it is printed, because a
    number a reader can mistake for wall clock is worse than no number.
    """
    blast = getattr(result, 'resource_blast', None) or {}
    rows = blast.get('rows') or []
    if not rows:
        return []
    total = blast.get('element_count') or 0
    lines = ["Shared Sources (blast radius by resource):", ""]
    lines.append(f"  {'resource':<44}{'direct':>7}{'blast':>9}{'work':>11}")
    # UX-187: rows are already ranked widest-first, so a cap keeps the
    # ones a reader acts on. Four lines each, so twenty repositories is
    # eighty lines of table.
    shown = rows if 'sources' in full_sections else rows[:_SHARED_SOURCE_ROWS]
    hidden_rows = len(rows) - len(shown)
    for row in shown:
        cost = ("unmeasured" if row['measured_seconds'] is None
                else f"{row['measured_seconds']:.0f}s")
        identity = row['identity']
        share = f"/{total}" if total else ""
        numbers = (f"{row['direct_count']:>7}"
                   f"{str(row['blast_count']) + share:>9}{cost:>11}")
        # UX-192: the identity is the join key - `bga blast <identity>`
        # is the next command a reader types - so it is never elided.
        # An identity too wide for the column takes its own line and the
        # numbers keep their alignment underneath; a key you cannot
        # paste is not a key, and the elided form resolved as a *path*
        # and answered "rebuilds nothing here" (the UX-178 defect,
        # reopened for exactly the long forge urls real projects use).
        if len(identity) > 44:
            lines.append(f"  {identity}")
            lines.append(f"  {'':<44}{numbers}")
        else:
            lines.append(f"  {identity:<44}{numbers}")
        lines.append(f"      {sources.keying_clause(row)}")
        kinds = ", ".join(f"{count} {kind}" for kind, count
                          in (row['by_element_kind'] or {}).items())
        if kinds:
            # UX-173: the split first, because it is what the count
            # means; the per-kind detail behind it.
            lines.append(
                f"      rebuilds "
                f"{sources.format_kind_split(row.get('building_count', row['blast_count']), row.get('assembling_count', 0))}"
                f": {kinds}")
        if row['measured_elements'] < row['blast_count']:
            lines.append(f"      measured for {row['measured_elements']} of "
                         f"{row['blast_count']} - the rest did not run in this build")
    if hidden_rows:
        # UX-187: named, not silent. The rows are ranked widest-first,
        # so what folds is the tail - but a reader still has to be told
        # it exists.
        lines.append(_elision(hidden_rows, "--full-sources", "resource(s)"))
    unreadable = blast.get('unreadable') or {}
    if unreadable:
        # UX-160's lesson: a reader that silently drops what it cannot
        # parse reports zero and looks like an answer.
        lines.append(f"  ({len(unreadable)} element(s) whose sources could not be "
                     f"read are not counted above)")
    lines += [
        "",
        "  Work is the sum of the named elements' own durations, not wall clock:",
        "  a build with any parallelism completes it in less. \"Assemble\" is a",
        "  kind that runs no build commands (stack, import, filter, junction);",
        "  an unrecognised kind counts as building, which overstates rather",
        "  than understates what a change costs.",
        "",
    ]
    return lines


def _format_blast_ranking(signals: dict) -> List[str]:
    """UX-173: the top blast elements, in the order the ranking used.

    "Ranked by cost" and "ranked by count, because this run measured
    nothing" are different claims and a reader acts on them
    differently, so the line says which one it is showing rather than
    leaving it to be inferred from whether the numbers look plausible.
    """
    top = signals.get('top_blast_radius') or []
    if not top:
        return []
    br_data = signals.get('blast_radius') or {}
    ranked_by = signals.get('blast_radius_ranked_by') or 'element-count'
    label = ("measured rebuild time" if ranked_by == 'measured-rebuild-time'
             else "downstream element count (this run measured no durations)")
    lines = [f"  Widest blast radius, by {label}:"]
    for uid in top[:5]:
        entry = br_data.get(uid) if isinstance(br_data, dict) else None
        if not isinstance(entry, dict):
            lines.append(f"    {uid}")
            continue
        cost = entry.get('weighted_duration_us') or 0
        kind = entry.get('element_kind') or 'unknown'
        suffix = (f", {cost / 1e6:.1f}s of rebuilding below it"
                  if cost else "")
        assembles = "" if sources.is_building_kind(kind) else " - assembles, does not build"
        lines.append(f"    {uid} ({kind}): "
                     f"{entry.get('downstream_count', 0)} downstream{suffix}{assembles}")
    return lines


def format_text(result: AnalysisResult, section: Optional[str] = None,
                by_kind: bool = False, full_sections=frozenset()) -> str:
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
    # UX-95: the identity hash above says which runs are comparable; it
    # is stable across captures of the same project and targets by
    # design, so on its own it cannot say *which* capture this is.
    instance = getattr(result, 'run_instance', None) or {}
    if instance:
        lines.append(f"Instance: {_format_instance(instance)}")
    lines.append(f"Total Duration: {result.total_duration_us / 1e6:.1f}s")
    # UX-156 item 2: before any efficiency number, because every one of
    # them describes a build that stopped early. `_format_key_findings`
    # already carries the same fact (UX-54), but it is a dozen lines
    # down a report a user scrolls past - and the figures above it are
    # the ones that get quoted.
    for violation in (result.violations or []):
        if violation.get('type') != 'build_failed':
            continue
        # UX-164 item 3: cache hits are not casualties.
        built, cached = violation.get('built_count'), violation.get('cached_count')
        counts = ""
        if built is not None:
            counts = f", {built} built"
            if cached:
                counts += f", {cached} already cached"
        if violation.get('suspended') and not violation.get('failed_elements') \
                and not violation.get('interrupted'):
            # UX-185: neither a failure nor an interrupt - the build ran
            # to the end, and the machine was asleep for part of it. The
            # sentence names the fix, because the reader has a capture
            # they cannot use and the next question is what to do
            # differently.
            from ..suspend import describe as _describe_suspension
            lines.append(_describe_suspension(violation['suspended']))
            what = "the machine slept while it ran"
        elif violation.get('interrupted') and not violation.get('failed_elements'):
            # UX-157: an interrupt is not a failure, and saying it is
            # sends the reader hunting for a compile error.
            what = "it was interrupted before it finished"
        else:
            named = ", ".join(violation.get('failed_elements') or []) or "unnamed element"
            what = (f"{violation.get('failed_count')} element(s) ended in "
                    f"FAILURE ({named})")
        lines.append(
            f"THIS BUILD DID NOT FINISH: {what}{counts}. Every figure below "
            f"describes a partial build."
        )
        break
    lines.append("")

    # Key Findings (P4-02) - synthesized summary, shown first, full
    # report only (matches format_json's own confidence/violations
    # gating: section is None). Subcommand-specific outputs (graph/
    # floors/replay/utilisation/diagnostics) stay exactly as they were.
    if section is None:
        lines.extend(_format_key_findings(result))
        lines.extend(_format_confidence_and_violations(result))

    # UX-171: with the graph, because it is a fact about the graph's
    # inputs rather than about this run's scheduling.
    if section in (None, 'graph'):
        lines.extend(_format_resource_blast(result, full_sections))

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
            lines.append(
                f"  {_attribution_label(category):25s} "
                f"{duration_us / 1e6:8.2f}s ({pct:5.1f}%)"
            )
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
            shown, hidden_at = _head_and_tail(
                detail, _PATH_HEAD, _PATH_TAIL,
                full=('path' in full_sections))
            for index, entry in enumerate(shown):
                if index == hidden_at:
                    lines.append(_elision(len(detail) - len(shown), "--full-path"))
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
            # ...and in *slot*-seconds, which is a different quantity
            # from the wall-clock seconds every other number in this
            # report is printed in: N builders running for the whole
            # build contribute N seconds per second. Printing both as
            # bare `s` let a 3261s build report 8626s of idle, which
            # reads as impossible rather than as a different unit.
            lines.append(
                "  Buckets below are task slot-time (occupancy), not CPU time, and "
                "are measured in slot-seconds - a build of H seconds on N builders "
                "has N*H of them to spend:"
            )
        for bucket_name, bucket_us in buckets.items():
            lines.append(
                f"  {str(bucket_name).replace('_', ' ').title():20s} "
                f"{bucket_us / 1e6:8.2f} slot-s"
            )
        # UX-48: the two idle buckets recommend opposite fixes, so
        # whichever one dominates is the actionable part of this block.
        # Naming that here rather than leaving a reader to infer it from
        # two similar-looking numbers.
        underparallel_us = buckets.get('idle_underparallel', 0)
        no_tasks_us = buckets.get('idle_no_tasks', 0)
        if underparallel_us > 0:
            lines.append(
                f"  -> {underparallel_us / 1e6:.2f} slot-s of that idle capacity had "
                f"work ready and waiting for a builder: raising build concurrency is "
                f"the lever here (`bga sweep` estimates the payoff)."
            )
        if no_tasks_us > underparallel_us and no_tasks_us > 0:
            lines.append(
                f"  -> {no_tasks_us / 1e6:.2f} slot-s had nothing ready to run at "
                f"all - no amount of extra concurrency helps that; it is a "
                f"dependency-graph shape problem."
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
                # UX-173: which order the ranking below is in, and what
                # the elements in it actually are. A blast of 84 where 39
                # are stacks is not a blast of 84 things that build.
                lines.extend(_format_blast_ranking(diagnostics_signals))
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
                    f"estimate; see `bga checkout-cost` for real measurement):"
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
                # UX-187: `[:5]` was silent. A reader cannot act on a
                # number they do not know is missing (`UX-160`).
                hidden = len(serialized_pairs) - 5
                lines.append(
                    "  Serialized (same dependency chain, not independently batchable): "
                    + "; ".join(f"{a} -> {b}" for a, b in serialized_pairs[:5])
                    + (f" (+{hidden} more, see --format json)" if hidden > 0 else "")
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


def memory_envelope_direction(delta_mb: float) -> str:
    """UX-145: the word, gated on the delta the line actually *prints*.

    It read "Memory envelope grew: 0.6 GB -> 0.6 GB (+0.0 GB, +0%)" on a
    real run. A direction the numbers beside it do not show is the kind
    of sentence that teaches a reader to stop believing the others, so
    zero is "unchanged" - and so is anything that rounds to zero at the
    one decimal place of GB this line renders.
    """
    if abs(round(delta_mb / 1024, 1)) < 0.05:
        return 'unchanged'
    return 'grew' if delta_mb > 0 else 'shrank'


def _memory_knee_caveat(memory_envelope: Optional[dict], knee) -> List[str]:
    """UX-104: which constraint binds at the knee.

    The sweep's knee is a replay-model answer about *scheduling*, and
    the replay model knows nothing about memory any more than it knows
    about CPU (`UX-09`/`UX-14`). A knee above the memory-feasible
    capacity is not a recommendation, it is a recommendation to swap -
    and swapping is the worst build slowdown there is, with no CPU-side
    signal that predicts it.
    """
    envelope = memory_envelope or {}
    projections = envelope.get('projections') or []
    if knee is None or not projections:
        return []
    # `knee_points` maps a resource name to a plain capacity integer -
    # the same value the line above prints.
    capacity = knee if isinstance(knee, int) else None
    if not capacity:
        return []
    at_knee = next((p for p in projections if p['builders'] == capacity), None)
    host_gb = envelope['host_memory_mb'] / 1024
    if at_knee is None:
        # The knee sits beyond the measured population - more builders
        # than there are elements with a measured peak - so the envelope
        # has nothing to say rather than an extrapolation to offer.
        return [
            f"  Memory: no envelope at capacity {capacity} - only "
            f"{envelope['elements_measured']} element(s) have a measured peak, so "
            f"this cannot say whether {host_gb:.1f} GB is enough there."
        ]
    if at_knee['fits']:
        return [
            f"  Memory: capacity {capacity} needs ~{at_knee['envelope_mb'] / 1024:.1f} GB "
            f"of {host_gb:.1f} GB ({at_knee['share_of_host'] * 100:.0f}%) - memory is "
            f"not what binds at the knee."
        ]
    return [
        f"  MEMORY BINDS BEFORE THE KNEE: capacity {capacity} needs "
        f"~{at_knee['envelope_mb'] / 1024:.1f} GB against {host_gb:.1f} GB of RAM. The "
        f"knee is a scheduling answer and the replay model does not know about "
        f"memory (UX-09/UX-14) - building there would swap."
    ]


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


def format_sweep_text(resource: str, sweep_result, calibration_capacities: Optional[List[int]] = None, plane2_capacity: Optional[dict] = None, memory_envelope: Optional[dict] = None) -> str:
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
            for line in _memory_knee_caveat(memory_envelope, knee):
                lines.append(line)
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


def _format_invalidation_roots(churn: dict) -> List[str]:
    """UX-92's invalidation roots, one line each.

    Extracted from `format_compare_text` by `UX-173`, which had to
    change the counting: a root that invalidated four stacks and
    three compilers is a different fact from one that invalidated
    seven compilers, and a guard on that wording needs something to
    call.
    """
    lines: List[str] = []
    for root in (churn.get('invalidation_roots') or [])[:_INVALIDATION_ROOTS_SHOWN]:
        total_us = root['duration_us'] + root['downstream_us']
        # UX-173: the split, where there is one to make.
        assembling = root.get('downstream_assembling') or 0
        building = root.get('downstream_building',
                            root['downstream_rebuilt'] - assembling)
        downstream = (
            f" and invalidated "
            f"{sources.format_kind_split(building, assembling)} below it"
            if root['downstream_rebuilt'] else " and invalidated nothing below it"
        )
        lines.append(
            f"  Invalidated at {root['element_uid']}: its cache key changed "
            f"({root['baseline_cache_key'][:8]} -> "
            f"{root['candidate_cache_key'][:8]}){downstream}, "
            f"{total_us / 1e6:.1f}s of rebuilding in total. Nothing it depends on "
            f"changed, so the change starts here"
        )
    return lines


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
    baseline_instance = getattr(comparison, 'baseline_run_instance', None) or {}
    if baseline_instance:
        lines.append(f"           {_format_instance(baseline_instance)}")
    lines.append(f"Candidate: {comparison.candidate_run_id or '(no run identity)'}")
    candidate_instance = getattr(comparison, 'candidate_run_instance', None) or {}
    if candidate_instance:
        lines.append(f"           {_format_instance(candidate_instance)}")
    lines.append("")

    baseline_total = b.get('total_duration_us')
    delta_total = d.get('total_duration_us')
    pct = (delta_total / baseline_total * 100) if (baseline_total and delta_total is not None) else None
    # UX-156: a refusal is `not comparable (<why>)`, and the `<why>` is a
    # whole sentence. Shouting it and then appending the very delta it
    # calls meaningless - which is what uppercasing the entire verdict
    # did - reads as a measurement with an angry preamble. The label is
    # the verdict; the reason gets its own line; the numbers follow
    # marked as what they are.
    head, _, reason = comparison.verdict.partition(" (")
    reason = reason[:-1] if reason.endswith(")") else reason
    measurement = (
        f"total duration {_fmt_signed_us(delta_total, pct)}, "
        f"{_fmt_us(baseline_total)} -> {_fmt_us(c.get('total_duration_us'))}"
    ) if pct is not None else None
    if reason:
        lines.append(f"Verdict: {head.upper()}")
        lines.append(f"  {reason}")
        if measurement:
            lines.append(f"  Not a verdict, for reference only: {measurement}")
    else:
        verdict_line = f"Verdict: {head.upper()}"
        if measurement:
            verdict_line += f"  ({measurement})"
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
        lines.extend(_format_invalidation_roots(churn))
        extra = len(churn.get('invalidation_roots') or []) - _INVALIDATION_ROOTS_SHOWN
        if extra > 0:
            lines.append(
                f"    (+{extra} more independent invalidation root(s), see --format json)"
            )

    # UX-104: did this change make the build need more memory? Placed
    # with the other "what did this change cost" answers.
    memory_delta = getattr(comparison, 'memory_envelope_delta', None) or {}
    if memory_delta:
        share = memory_delta.get('delta_share')
        direction = memory_envelope_direction(memory_delta['delta_mb'])
        lines.append(
            f"  Memory envelope {direction}: "
            f"{memory_delta['baseline_envelope_mb'] / 1024:.1f} GB -> "
            f"{memory_delta['candidate_envelope_mb'] / 1024:.1f} GB "
            f"({memory_delta['delta_mb'] / 1024:+.1f} GB"
            + (f", {share * 100:+.0f}%" if share is not None else "")
            + f") against {memory_delta['host_memory_mb'] / 1024:.1f} GB of RAM"
            + ("" if memory_delta['candidate_fits'] else " - the candidate does NOT fit")
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
            # UX-121: the same label path `analyze` uses. This rendered
            # the raw field name - `Execution On Chain Us` beside a value
            # in seconds - on the one surface a CI reviewer reads most,
            # through UX-111's whole audit, because the guard test
            # asserted the helper rather than any rendered output.
            label = _attribution_label(category)
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
