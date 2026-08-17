"""
Confidence and reconciliation gates (Part 33).

Hard gates (33.1): ordering_violations == 0, critical_path_coverage ==
1.0, dominator_coverage == 1.0, blame_chain_coverage == 1.0.
Soft gates (33.2, defaults): task_coverage >= 0.95, duration_coverage >=
0.98 - these reduce confidence (via coverage_score's min, below) rather
than hard-failing.

confidence = min(provenance_score, coverage_score, model_score,
attribution_score) (33.4). The spec names these four sub-scores and
gives attribution_score's exact inputs, but does not spell out
provenance_score/coverage_score/model_score's formulas - each is
grounded in the one other place the spec actually defines the relevant
concept (see inline comments), not guessed from nothing.

cold_confidence stays fully separate (already lives in floors, from
bga.floors.cold.compute_cold_floor - never read or written here).
"""
import logging
from typing import List, Optional, Tuple

from ..ingest.models import STRUCTURAL_ELEMENT_KINDS, Graph, NormalizedTask, RunContext, Trace
from ..occupancy.sweep import compute_task_horizon

logger = logging.getLogger(__name__)

TASK_COVERAGE_THRESHOLD = 0.95
DURATION_COVERAGE_THRESHOLD = 0.98


def compute_confidence(
    normalized_tasks: List[NormalizedTask],
    run_context: Optional[RunContext],
    trace: Optional[Trace],
    graph: Optional[Graph],
    violations: List[dict],
    attribution_segments: list,
    graph_analysis: Optional[dict],
    attribution: dict,
    floors: dict,
) -> Tuple[dict, List[dict]]:
    """
    Compute confidence metrics.

    Args:
        normalized_tasks, run_context, trace, graph: pipeline state, as
            held on BuildEfficiencyAnalyzer.
        violations: existing violations list (read-only here - hard-gate
            failures this function finds are returned separately, not
            appended in place, keeping this function side-effect-free;
            the caller appends them).
        attribution_segments: the flattened blame-chain segments
            (BuildEfficiencyAnalyzer._attribution_segments), for
            ambiguous_wait_us.
        graph_analysis: analyze_graph(...) result.
        attribution: the attribution dict from _compute_attribution.
        floors: the floors dict from _compute_floors.

    Returns:
        (confidence_dict, new_hard_gate_violations) - the caller is
        responsible for appending new_hard_gate_violations to its own
        violations list.
    """
    graph_analysis = graph_analysis or {}
    ordering_violations = sum(
        1 for v in violations if v.get('type') == 'ordering_violation'
    )
    reconciliation_violations = [
        v for v in violations if v.get('type') == 'attribution_reconciliation'
    ]

    total_tasks = len(normalized_tasks) if normalized_tasks else 0
    _, _, horizon_us = compute_task_horizon(normalized_tasks) if normalized_tasks else (0, 0, 0)

    # --- Coverage metrics ---
    critical_path = graph_analysis.get('critical_path', [])
    elements_with_tasks = {t.task_key.element_uid for t in normalized_tasks}

    # UX-55: on an incremental run - a pre-commit build with caches on,
    # which is the majority of what CI actually runs - most of the graph
    # legitimately has no task, because BuildStream skipped it as already
    # cached. Counting those as missing measurements failed a hard gate,
    # which dropped confidence, which made UX-03/UX-39's regression gate
    # fail open: the better the cache worked, the less bga gated.
    #
    # Three conditions, all required, because "absent" is only safe to
    # read as "cached" when the capture proves it:
    #   - BuildStream itself reported skipped elements (run_mode), so the
    #     claim rests on the log rather than on absence;
    #   - the build succeeded, since a failed build's missing tasks may
    #     genuinely be lost;
    #   - the element count BuildStream says it *processed* equals the
    #     number that produced tasks - the checksum that proves nothing
    #     was dropped in extraction.
    # If any fails, this behaves exactly as it did before.
    cached_on_critical_path: List[str] = []
    if run_context is not None and run_context.run_mode == 'incremental':
        built = run_context.built_element_count
        if not run_context.failed_elements and built == len(elements_with_tasks):
            cached_on_critical_path = [
                uid for uid in critical_path if uid not in elements_with_tasks
            ]

    measured_critical_path = [
        uid for uid in critical_path if uid not in set(cached_on_critical_path)
    ]
    if measured_critical_path:
        resolved = sum(1 for uid in measured_critical_path if uid in elements_with_tasks)
        critical_path_coverage = resolved / len(measured_critical_path)
    else:
        # Either there is no critical path, or every element on it was
        # cached. Both mean there is nothing on the chain this run failed
        # to measure - the report says which, rather than this number.
        critical_path_coverage = 1.0

    dominators = graph_analysis.get('dominators', {})
    total_elements = len(graph.elements) if graph else 0
    dominator_coverage = (len(dominators) / total_elements) if total_elements > 0 else 1.0

    attribution_sum_us = sum(attribution.get(k, 0) for k in (
        'execution_on_chain_us', 'dependency_wait_us', 'resource_wait_us',
        'scheduler_wait_us', 'idle_us', 'retry_wait_us',
    ))
    blame_chain_coverage = (attribution_sum_us / horizon_us) if horizon_us > 0 else 1.0

    declared_task_count = len(trace.spans) if trace else 0
    task_coverage = (total_tasks / declared_task_count) if declared_task_count > 0 else 1.0

    declared_duration_us = sum(s.dur_us for s in trace.spans) if trace else 0
    accounted_duration_us = sum(t.dur_us for t in normalized_tasks)
    duration_coverage = (
        accounted_duration_us / declared_duration_us if declared_duration_us > 0 else 1.0
    )

    # --- Run identity (I8, P1-37) ---
    # The spec states I8's invariant ("all analysis inputs must belong to
    # the same run identity") but defines no concrete field/mechanism for
    # it - tools/bst_extract_run.py's real, additive extension embeds the
    # same manifest_hash into run-context.json (run_identity.manifest_hash),
    # graph.json, and trace.json (both run_identity_hash) at extraction
    # time. Cross-checked here: matching -> no penalty; any missing (e.g.
    # an older/hand-built run directory with no identity fields at all) ->
    # backward-compatible, not a hard failure, but a real, visible
    # provenance-score reduction (see below); present but conflicting
    # (e.g. a trace.json swapped in from an unrelated extraction) -> a
    # genuine hard-gate failure and violation, since analysis would
    # otherwise silently proceed over mismatched inputs.
    run_context_identity_hash = (
        (run_context.run_identity or {}).get('manifest_hash')
        if run_context and run_context.run_identity else None
    )
    graph_identity_hash = graph.run_identity_hash if graph else None
    trace_identity_hash = trace.run_identity_hash if trace else None
    identity_hashes = (run_context_identity_hash, graph_identity_hash, trace_identity_hash)
    run_identity_all_present = all(h is not None for h in identity_hashes)
    run_identity_consistent = (
        len(set(identity_hashes)) == 1 if run_identity_all_present else True
    )

    # --- Hard gates (33.1) ---
    hard_gates = {
        'ordering_violations_zero': ordering_violations == 0,
        'critical_path_coverage_full': critical_path_coverage >= 1.0,
        'dominator_coverage_full': dominator_coverage >= 1.0,
        'blame_chain_coverage_full': blame_chain_coverage >= 1.0,
        'run_identity_consistent': run_identity_consistent,
    }
    # Only critical_path_coverage/dominator_coverage failures need a new
    # violation entry - ordering violations are already individually
    # reported by normalize_trace, and blame_chain_coverage < 1.0 is
    # exactly the condition P1-05's attribution_reconciliation violation
    # already reports. Adding another entry for either would just
    # duplicate an existing, more specific one.
    #
    # UX-25: a bare `value` ratio (e.g. 0.8) gives no indication of
    # *which* element is missing or *why* - real friction found via a
    # real bga analyze run (docs/scenarios/UX-25's own Motivation): the
    # report's own critical-path ranking already knows and displays a
    # `kind: stack` element's own structural caveat elsewhere in the
    # same output, this gate just never connected the two. `detail`
    # names the specific missing element(s) and, where the existing
    # STRUCTURAL_ELEMENT_KINDS heuristic (P4-12) already explains it,
    # the real reason - never a generic re-statement of the ratio.
    kind_by_uid = {e.uid: (e.element_kind or 'unknown') for e in graph.elements} if graph else {}

    def _missing_element_detail(uids: List[str]) -> List[dict]:
        return [
            {
                'element_uid': uid,
                'element_kind': kind_by_uid.get(uid, 'unknown'),
                'is_structural_kind': kind_by_uid.get(uid) in STRUCTURAL_ELEMENT_KINDS,
            }
            for uid in uids
        ]

    new_violations: List[dict] = []

    # UX-60: I3 - `T∞,observed >= max(observed task duration)`. The spec
    # states it and nothing implemented it, which is why `UX-53` could
    # change the per-element duration definition without any check
    # noticing. It holds trivially under the current definition (the
    # per-element duration *is* the maximum task, and the chain includes
    # that element), and that is exactly the point: it is the guard that
    # would catch a future definition - `BUILD`-only, say - that stops
    # holding. Filed as a violation rather than a hard gate, since a
    # capture with no tasks at all must not fail it.
    t_infinity = floors.get('t_infinity_observed')
    longest_task_us = max((t.dur_us for t in normalized_tasks), default=0)
    if t_infinity is not None and longest_task_us > t_infinity:
        new_violations.append({
            'type': 'floor_below_longest_task',
            'invariant': 'I3',
            't_infinity_observed_us': t_infinity,
            'longest_task_us': longest_task_us,
            'detail': (
                'the structural floor is shorter than a single observed task, '
                'so it claims a schedule that cannot exist - no amount of '
                'capacity makes one task finish sooner than it did'
            ),
        })
    if not hard_gates['critical_path_coverage_full']:
        missing_critical_path_uids = [
            uid for uid in measured_critical_path if uid not in elements_with_tasks
        ]
        new_violations.append({
            'type': 'hard_gate_failed', 'gate': 'critical_path_coverage',
            'value': critical_path_coverage,
            'detail': _missing_element_detail(missing_critical_path_uids),
        })
    if not hard_gates['dominator_coverage_full']:
        missing_dominator_uids = [e.uid for e in graph.elements if e.uid not in dominators] if graph else []
        new_violations.append({
            'type': 'hard_gate_failed', 'gate': 'dominator_coverage',
            'value': dominator_coverage,
            'detail': _missing_element_detail(missing_dominator_uids),
        })
    if not hard_gates['run_identity_consistent']:
        new_violations.append({
            'type': 'run_identity_mismatch',
            'run_context_hash': run_context_identity_hash,
            'graph_hash': graph_identity_hash,
            'trace_hash': trace_identity_hash,
        })
    for gate_name, passed in hard_gates.items():
        if not passed:
            logger.warning("Hard gate failed: %s", gate_name)
    if all(hard_gates.values()):
        logger.info("All hard gates passed (%d tasks checked)", total_tasks)

    # --- Soft gates (33.2) - logged, not hard-failed; the actual
    # confidence reduction comes from coverage_score's min() below.
    if task_coverage < TASK_COVERAGE_THRESHOLD:
        logger.warning(
            "Soft gate failed: task_coverage %.3f < %.2f", task_coverage, TASK_COVERAGE_THRESHOLD,
        )
    if duration_coverage < DURATION_COVERAGE_THRESHOLD:
        logger.warning(
            "Soft gate failed: duration_coverage %.3f < %.2f",
            duration_coverage, DURATION_COVERAGE_THRESHOLD,
        )

    # --- Sub-scores (33.4) ---
    # provenance_score: the spec's only other use of "provenance" (Part
    # 4.3) is wall_clock's preferred run_context source vs the reduced-
    # provenance trace_horizon fallback - mirrored here directly.
    #
    # Run identity (P1-37) folds into the same score: no identity data at
    # all (older/hand-built run directories - backward compatible, not a
    # hard failure) reduces provenance_score to at most 0.75, a real,
    # visible "reduced provenance" signal distinct from a clean run -
    # min()'d against the wall_clock check so an already-reduced score
    # from missing wall_clock isn't overridden upward. A genuine mismatch
    # (inputs present but disagree) is far more serious than merely
    # missing data - collapses provenance_score to 0.0, since that's
    # exactly the "inputs may not belong to the same run" case I8 exists
    # to catch, not just an absence of provenance metadata.
    if run_context and run_context.wall_start_us is not None and run_context.wall_end_us is not None:
        provenance_score = 1.0
    else:
        provenance_score = 0.5
    if not run_identity_consistent:
        provenance_score = 0.0
    elif not run_identity_all_present:
        provenance_score = min(provenance_score, 0.75)

    coverage_score = min(
        critical_path_coverage, dominator_coverage, blame_chain_coverage,
        task_coverage, duration_coverage,
    )

    # model_score: reflects whether the replay counterfactual model
    # (Part 18) stayed consistent with the certified lower bound
    # (I2: LB <= T_C) - the concrete "model validity" signal already
    # computed elsewhere in the pipeline, rather than a new one invented
    # from nothing.
    model_score = 1.0
    if floors.get('t_c') is not None and floors.get('lb') is not None:
        if floors['t_c'] < floors['lb']:
            model_score = 0.5
            logger.warning("Model score reduced: T_C (%d) < LB (%d)", floors['t_c'], floors['lb'])

    # attribution_score (33.4): untracked_time, ambiguous_wait_time,
    # violation_time - never penalizes legitimate phase overlap (phase
    # annotations don't change a segment's category, so this formula
    # never even looks at them).
    untracked_us = attribution.get('untracked_head_us', 0) + attribution.get('untracked_tail_us', 0)
    ambiguous_wait_us = sum(
        seg.end_us - seg.start_us
        for seg in (attribution_segments or [])
        if seg.category.value == 'RESOURCE_WAIT'
        and seg.metadata.get('holder_info', {}).get('ambiguous')
    )
    violation_us = sum(
        abs(v.get('gap_us', 0)) for v in violations if v.get('type') == 'ordering_violation'
    )
    violation_us += sum(abs(v.get('residual_us', 0)) for v in reconciliation_violations)

    # UX-40: untracked time that is *explained* by BuildStream's own
    # measured pipeline phases (Loading/Resolving elements, Query cache,
    # Initializing remote caches - P4-14, already parsed into
    # run_context.pipeline_overhead and already shown as its own report
    # section) is accounted-for time, not ambiguous time. Part 33.4
    # penalizes untracked/ambiguous/violation time; startup that the
    # tool can name and price is none of those.
    #
    # This matters because UX-10 deliberately made total_duration_us
    # prefer real wall-clock so that startup would stop being invisible,
    # and the side effect was that measuring it dragged every real
    # capture's confidence down - the smaller the build, the larger
    # BuildStream's fixed startup as a fraction of it, the lower the
    # score. Real captures landed at ~0.69 ("medium"), below the 0.8 bar
    # `bga compare --fail-on-regression` fails open on, so the CI gate
    # was silently off on exactly the small, fast projects most likely
    # to run it.
    #
    # Genuinely unexplained head/tail still counts, in full: this only
    # ever subtracts as much as the pipeline phases actually account for.
    explained_untracked_us = 0
    if run_context is not None and getattr(run_context, 'pipeline_overhead', None):
        explained_untracked_us = min(
            untracked_us,
            sum(entry.get('elapsed_us', 0) for entry in run_context.pipeline_overhead),
        )

    penalized_us = (untracked_us - explained_untracked_us) + ambiguous_wait_us + violation_us
    # untracked_us lives outside the task horizon by definition (Part 11),
    # while ambiguous_wait_us/violation_us live inside it - the correct
    # normalizer for their sum is the full wall-clock horizon (task
    # horizon + untracked), not the task horizon alone (P1-23: before
    # untracked_head_us/untracked_tail_us were computed for real, this
    # was unreachable dead code, since untracked_us was always 0).
    full_horizon_us = horizon_us + untracked_us
    attribution_score = max(0.0, 1.0 - (penalized_us / full_horizon_us)) if full_horizon_us > 0 else 1.0

    confidence = min(provenance_score, coverage_score, model_score, attribution_score)

    confidence_dict = {
        'primary': confidence,
        'provenance_score': provenance_score,
        'coverage_score': coverage_score,
        'model_score': model_score,
        'attribution_score': attribution_score,
        # UX-40: how much of the untracked head/tail was explained by
        # measured pipeline overhead and therefore not penalized -
        # published so the number above is auditable rather than just
        # higher than it used to be.
        'explained_untracked_us': explained_untracked_us,
        'critical_path_coverage': critical_path_coverage,
        # UX-55: what the coverage figure above is a fraction *of*. On an
        # incremental run it excludes elements BuildStream skipped as
        # cached, and a reader needs to know that without inferring it.
        'run_mode': run_context.run_mode if run_context is not None else 'unknown',
        # UX-62: how much measured execution was work the build threw
        # away. Attribution still counts it as EXECUTION_ON_CHAIN -
        # moving it would change `I4`'s identity, a decision with a proof
        # obligation rather than a re-bucketing - so it is published
        # beside the numbers instead of silently reclassified. Both zero
        # on a capture with no recorded statuses, which is not the same
        # as a run with no failures and is why `run_mode`-style
        # "unrecorded" handling applies to the *span* field, not here.
        'failed_task_count': sum(1 for t in normalized_tasks if t.failed),
        'failed_task_us': sum(
            t.finish_us - t.start_us for t in normalized_tasks if t.failed
        ),
        'critical_path_cached': cached_on_critical_path,
        'dominator_coverage': dominator_coverage,
        'blame_chain_coverage': blame_chain_coverage,
        'task_coverage': task_coverage,
        'duration_coverage': duration_coverage,
        'hard_gates': hard_gates,
        'ordering_violations': ordering_violations,
        'task_count': total_tasks,
        'run_identity_available': run_identity_all_present,
    }
    return confidence_dict, new_violations
