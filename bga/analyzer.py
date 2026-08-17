"""
Main analyzer module.

Orchestrates the complete analysis pipeline as specified in the v9 specification.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Set
from collections import defaultdict

from .ingest.models import AnalysisResult, Graph, RunContext, Trace, TaskKind, STRUCTURAL_ELEMENT_KINDS
from .ingest.loader import load_all
from .normalize.timestamps import normalize_trace
from .occupancy.sweep import compute_occupancy_stats, compute_task_horizon
from .graph.edg import analyze_graph
from .attribution.blame_chain import BlameChainAnalyzer
from .floors import (
    compute_capacity_lower_bound,
    compute_cold_floor,
    compute_default_capacities,
    compute_exclusive_serialization_bound,
    compute_t_infinity_observed,
)
from .replay.scheduler import ReplayScheduler
from .utilisation import (
    CPUAccounting,
    UtilizationAnalyzer,
    compute_rebuild_tasks,
    compute_retry_tasks,
)
from .diagnostics import analyze_diagnostics
from .structural import StructuralAnalyzer
from .validation import compute_confidence
from .validation.provenance import Advisory, Certified, assemble_floors

logger = logging.getLogger(__name__)

# UX-28: how far past the governing core count a run's *potential*
# concurrent-process demand (`builders x native max-jobs`) may go before
# it is reported as oversubscription. Expressed as a multiple of the real
# governing ceiling, deliberately - the previous bar was BuildStream's
# own unconfigured default (`4 * min(cores, 8)`), which is 4x the cores
# on a 4-core host but only 0.5x on a 64-core one, so the sensitivity of
# the whole check depended on host size rather than on anything physical.
#
# The value is calibrated against UX-09's own real 6-configuration timing
# table on a real 4-core host, which is the only measured evidence this
# repo has:
#
#   4 builders x 4 max-jobs  = 16 procs =  4x cores -> 6.5s, the BEST config
#   4 builders x 16 max-jobs = 64 procs = 16x cores -> 6.4s, ~flat
#   8 builders x 8 max-jobs  = 64 procs = 16x cores -> 7.2s, ~11% SLOWER
#
# So a bar at or below 4x would flag the measured-optimal configuration,
# and the measured harm appears by 16x. 8x sits strictly between the two
# and is host-size-independent. It is an honest interpolation between two
# real data points, not a derived constant - and note the two 16x rows
# disagree with each other, which is exactly why the far sharper
# `builders > cores` dispatch check below exists alongside this one.
_OVERSUBSCRIPTION_DEMAND_RATIO = 8.0


class BuildEfficiencyAnalyzer:
    """
    Main analyzer class implementing the bga v9 specification.
    
    The analyzer separates three fundamentally different kinds of statements:
    1. Measurement - what actually happened in the trace
    2. Certification - what cannot be beaten given constraints
    3. Estimation/counterfactual modeling - what might happen under different conditions
    
    Governing principle:
    > Measure what happened. Certify what cannot be improved. Label what is estimated.
      Never mix the three.
    """
    
    def __init__(
        self,
        run_dir: Optional[Path] = None,
        capacity: Optional[int] = None,
        run_replay: bool = False,
        replay_heuristic: str = 'lpt',
        run_diagnostics: bool = False,
        verbose: bool = False,
        cold: bool = False,
        allow_partial_cold: bool = False,
        historical_runs: Optional[List[Tuple[RunContext, Graph, Trace]]] = None,
    ):
        """
        Initialize the analyzer.

        Args:
            run_dir: Path to the run directory containing input files
            capacity: Override system resource capacity (optional)
            run_replay: Whether to run replay scheduling
            replay_heuristic: Heuristic for replay scheduling ('lpt', 'spt', 'fifo', 'depth')
            run_diagnostics: Whether to run advanced diagnostics
            verbose: Enable verbose logging
            cold: Whether to compute the advisory cold structural floor
                T∞,cold (Part 15) - off by default, only meaningful when
                historical_runs is also supplied.
            allow_partial_cold: When True, publish T∞,cold with
                partial=true/confidence=low instead of unavailable when
                some cold-critical-path element has no resolvable
                duration (Part 15.3). Ignored unless cold is also True.
            historical_runs: Optional list of (RunContext, Graph, Trace)
                tuples for prior runs, e.g. from
                bga.ingest.loader.load_historical_runs - the duration
                source for cold-floor resolution (Part 15.2). Fully
                isolated from LB/certified_headroom/primary confidence/
                measured attribution (I12) - see bga.floors.cold.compute_cold_floor.
        """
        self.run_dir = run_dir
        self.capacity_override = capacity
        self.run_replay = run_replay
        self.replay_heuristic = replay_heuristic
        self.run_diagnostics = run_diagnostics
        self.verbose = verbose
        self.cold = cold
        self.allow_partial_cold = allow_partial_cold
        self.historical_runs = historical_runs or []
        self.run_context: Optional[RunContext] = None
        self.graph: Optional[Graph] = None
        self.trace: Optional[Trace] = None
        self.normalized_tasks = []
        self.violations = []
        # UX-29: which capacity-check inputs were missing, when the
        # over/under-subscription and memory guards declined to run.
        # Empty list = they ran. Surfaced in the capacity-model note,
        # not in `violations` - nothing about the build is wrong, the
        # tool simply could not check.
        self.capacity_check_skipped_inputs = []
        self.analysis_result: Optional[AnalysisResult] = None
        self.blame_chain_analyzer: Optional[BlameChainAnalyzer] = None
        self.replay_scheduler: Optional[ReplayScheduler] = None
        self.utilization_analyzer: Optional[UtilizationAnalyzer] = None
    
    def load(self, run_dir: Optional[Path] = None) -> None:
        """
        Load input data from a run directory.
        
        Expected structure:
            run_dir/
                run_context.json
                graph.json
                trace.json
        
        Args:
            run_dir: Path to run directory (uses instance run_dir if not provided)
        """
        path = run_dir or self.run_dir
        if path is None:
            raise ValueError("No run directory specified")
        
        self.run_context, self.graph, self.trace = load_all(path)
    
    def load_from_data(
        self,
        run_context: RunContext,
        graph: Graph,
        trace: Trace,
    ) -> None:
        """
        Load input data directly from objects.
        
        Args:
            run_context: Run context object
            graph: Dependency graph object
            trace: Trace object
        """
        self.run_context = run_context
        self.graph = graph
        self.trace = trace
    
    def normalize(self) -> None:
        """
        Normalize the trace data.
        
        Performs:
        - Timestamp quantization to epsilon grid (Part 3.2)
        - Ready time computation (Part 7)
        - Ordering validation (Part 3.3)
        - Start time clamping (Part 3.4)
        """
        if self.trace is None or self.graph is None:
            raise ValueError("Must load data before normalizing")
        
        epsilon_us = self.run_context.trace_epsilon_us if self.run_context else 50000
        
        self.normalized_tasks, self.violations = normalize_trace(
            self.trace,
            self.graph,
            epsilon_us,
        )
        
        # Initialize blame chain analyzer with normalized tasks
        phase_spans = self.trace.phases if self.trace else []
        
        # Build active_tasks_at_time for classification (kept for
        # BlameChainAnalyzer's interface stability - unused internally as
        # of P1-31, which derives real occupancy from the task list
        # itself rather than from precomputed per-timestamp snapshots).
        # concurrent_jobs_at_time (a per-start-timestamp task count) was
        # removed here entirely (P1-32) - it measured "how many tasks
        # started at exactly this instant", not true concurrency, and
        # classify_scheduler_wait now computes real concurrency directly
        # from the task list instead.
        active_tasks_at_time: Dict[int, Set[str]] = defaultdict(set)

        for task in self.normalized_tasks:
            # Mark task as active during its execution [start_us, finish_us)
            active_tasks_at_time[task.start_us].add(str(task.task_key))
        
        # Resource capacity from run context (run-context/v9's own
        # resource_capacities field, e.g. {"PROCESS": 4} - Part 32.1).
        # P1-31: this previously checked a `run_context.builders`
        # attribute that RunContext has never actually defined (always
        # absent, so hasattr() was always False) - resource_capacity was
        # silently empty `{}` for every real run, structurally disabling
        # classify_resource_wait's capacity check regardless of how
        # correct that check itself was. An unrecognized resource name
        # (outside the Resource enum) is skipped with a warning rather
        # than raising - a run-context.json from a newer schema version
        # naming a resource this build doesn't know about yet shouldn't
        # break analysis of the resources it does recognize.
        resource_capacity = {}
        if self.run_context and self.run_context.resource_capacities:
            from .ingest.models import Resource
            for name, capacity in self.run_context.resource_capacities.items():
                try:
                    resource_capacity[Resource(name)] = capacity
                except ValueError:
                    logger.warning(
                        "Ignoring unrecognized resource %r in run_context.resource_capacities",
                        name,
                    )
        
        max_jobs = self.run_context.max_jobs if self.run_context else None
        
        self.blame_chain_analyzer = BlameChainAnalyzer(
            self.normalized_tasks,
            self.run_context,
            phase_spans,
            active_tasks_at_time=active_tasks_at_time,
            resource_capacity=resource_capacity,
            max_jobs=max_jobs,
        )
        
        # Initialize replay scheduler
        self.replay_scheduler = ReplayScheduler(
            self.normalized_tasks,
            self.run_context,
        )
        
        # Initialize utilization analyzer (M4)
        if self.run_context:
            cpu_accounting = None
            if self.run_context.cpu_accounting:
                cpu_accounting = CPUAccounting(
                    effective_cpus=self.run_context.cpu_accounting.get('effective_cpus'),
                    cgroup_quota_us=self.run_context.cpu_accounting.get('cgroup_quota_us'),
                    cgroup_period_us=self.run_context.cpu_accounting.get('cgroup_period_us'),
                    accounting_method=self.run_context.cpu_accounting.get('accounting_method'),
                )
            
            wall_clock_us = self.run_context.wall_clock_us or 0

            # host_cpu_count/cpu_budget (UX-12/UX-15), not max_jobs -
            # UX-17: max_jobs here would be RunContext.max_jobs, which
            # per run-context/v9's own schema means `builders` (see
            # _check_process_oversubscription's own docstring), and
            # UtilizationAnalyzer no longer computes its own competing
            # config-oversubscription evidence from it anyway - see
            # UtilizationAnalyzer.__init__'s own docstring.
            self.utilization_analyzer = UtilizationAnalyzer(
                cpu_accounting=cpu_accounting,
                wall_clock_us=wall_clock_us,
                host_cpu_count=self.run_context.host_cpu_count,
                cpu_budget=self.run_context.cpu_budget,
            )
    
    def _compute_floors(self, graph_analysis: Optional[dict] = None) -> dict:
        """
        Compute certified and advisory floors (Part 14-17).

        Args:
            graph_analysis: Pre-computed analyze_graph(...) result, reused
                from the caller (P1-21) instead of recomputing it here -
                analyze_graph (and the compute_reachability call inside
                it) was previously run 3 separate times per analyze()
                call (here, in _compute_attribution, and in analyze()
                itself) for the exact same deterministic input. Computed
                internally only if not supplied, for standalone callers.

        Returns:
            Dict containing floor metrics including:
            - t_infinity_observed: Critical path length with observed durations
            - t_infinity_cold: Critical path with cold durations (advisory)
            - lb: Lower bound = max(T∞, resource bounds, serialization bounds)
            - certified_headroom: H - LB
            - t_c: Replay makespan (Part 18)
            - model_slack: T_C - LB
            - efficiency_score: LB / horizon_us (UX-02) - scheduling
              efficiency of the observed work, not work-minimality; None
              when horizon_us is 0
        """
        if not self.normalized_tasks:
            return {
                't_infinity_observed': None,
                't_infinity_cold': None,
                'cold_partial': False,
                'cold_confidence': None,
                'cold_duration_sources': {},
                'cold_critical_path_duration_sources': {},
                'lb': None,
                'certified_headroom': None,
                't_c': None,
                'model_slack': None,
                'efficiency_score': None,
            }

        # Get task horizon
        _, _, horizon_us = compute_task_horizon(self.normalized_tasks)

        # Get graph analysis
        if graph_analysis is None:
            graph_analysis = analyze_graph(self.graph, self.normalized_tasks)
        t_infinity_observed = compute_t_infinity_observed(graph_analysis)

        # Capacity lower bound (Part 16): LB = max(T∞,observed,
        # max_p(W_p/C_p), exclusive-serialization bounds). Computing the
        # non-exclusive and exclusive terms as two separate maxes and
        # combining via max() below is equivalent to a single running max
        # over the combined resource set (max is associative/commutative),
        # so this split changes nothing about the resulting value -
        # bga/floors/ (P1-15).
        capacity_lb = compute_capacity_lower_bound(self.normalized_tasks, self.run_context)
        serialization_lb = compute_exclusive_serialization_bound(self.normalized_tasks, self.run_context)
        lb = max(t_infinity_observed, capacity_lb, serialization_lb)

        certified_headroom = max(0, horizon_us - lb)

        # UX-02: efficiency_score = LB / total_duration - the fraction of
        # wall-clock time already at the certified floor (equivalently
        # 1 - certified_headroom/horizon_us). Chosen over other candidate
        # ratios (e.g. t_c/horizon_us, which would measure the replay
        # model's own scheduling rather than a proven bound) specifically
        # because LB is a certified, proven-un-improvable quantity - this
        # score inherits that same certainty, not a model-dependent
        # estimate. None when horizon_us is 0 (nothing to divide by) -
        # never fabricated. This measures *scheduling* efficiency of the
        # observed work, not whether that work itself is minimal - a
        # slow-but-perfectly-scheduled critical path still scores near
        # 1.0; Critical Path is what surfaces the "reduce the work
        # itself" opportunity efficiency_score deliberately doesn't.
        efficiency_score = (lb / horizon_us) if horizon_us > 0 else None

        # Compute replay makespan T_C (Part 18)
        t_c = None
        model_slack = None

        if self.replay_scheduler:
            default_caps = compute_default_capacities(self.run_context)
            replay_result = self.replay_scheduler.replay(default_caps)
            t_c = replay_result.makespan_us

            # Model slack = T_C - LB (Part 18)
            model_slack = max(0, t_c - lb)

        # Advisory cold structural floor (Part 15) - fully isolated from
        # everything above (I12): computed independently, from observed
        # durations already finalized (lb/certified_headroom/t_c/model_slack
        # never read cold_floor, and cold_floor never reads them back).
        cold_floor = compute_cold_floor(
            self.graph, self.normalized_tasks, self.historical_runs,
            self.cold, self.allow_partial_cold,
        )

        # P2-08: assemble the final plain floors dict (the existing wire
        # format, unchanged) through a structural certified/advisory
        # checkpoint - wrapping each value in its provenance type right
        # here makes an accidental swap (e.g. a future edit passing
        # cold_floor['t_infinity_cold'] for 'lb') a TypeError at this
        # call site instead of a silently wrong certified number.
        floors = assemble_floors(
            certified={
                't_infinity_observed': Certified(t_infinity_observed),
                'lb': Certified(lb),
                'certified_headroom': Certified(certified_headroom),
                't_c': Certified(t_c) if t_c is not None else None,
                'model_slack': Certified(model_slack) if model_slack is not None else None,
                'efficiency_score': Certified(efficiency_score) if efficiency_score is not None else None,
            },
            advisory={
                't_infinity_cold': Advisory(cold_floor['t_infinity_cold']),
            },
        )
        # UX-27: a second, graph-shape-aware efficiency signal, because
        # `efficiency_score` above structurally cannot be one.
        #
        # Every certified floor is derived from the run's *own observed
        # graph*. A build whose independent elements have been
        # accidentally chained one behind another has a critical path
        # equal to its own total work, so LB == T-infinity == T_C
        # identically, headroom is zero, and efficiency_score is 1.00.
        # Measured on `examples/06-macro-micro-optimization`: three
        # one-line fixes made a real build 30.5% faster while
        # efficiency_score moved 1.00 -> 0.83 and certified headroom
        # 0.00s -> 4.05s. Both moved backwards, correctly, by their own
        # definitions - which is exactly the problem.
        #
        # occupancy_ratio does not consult the graph at all: it asks how
        # much of the available dispatch-slot-time the run actually used.
        # Chaining work that could have run concurrently lowers it;
        # unchaining raises it. On that same real pair: 25.4% -> 55.9%.
        #
        # Known weakness, stated rather than hidden: the numerator is
        # slot *occupancy*, not CPU time (P1-33/UX-36), so it inflates
        # under contention - the same work costs more occupancy when
        # elements overlap. That makes this an honest directional signal,
        # not a precise one, and is why UX-39's CI gate needs a stated
        # tolerance rather than a hair-trigger threshold.
        floors['occupancy_ratio'] = self._compute_occupancy_ratio(horizon_us)
        floors['cold_partial'] = cold_floor['cold_partial']
        floors['cold_confidence'] = cold_floor['cold_confidence']
        # P2-06: per-tier duration-source provenance, additive - doesn't
        # change any of the values above.
        floors['cold_duration_sources'] = cold_floor['cold_duration_sources']
        floors['cold_critical_path_duration_sources'] = cold_floor['cold_critical_path_duration_sources']
        return floors

    def _compute_attribution(self, graph_analysis: Optional[dict] = None) -> dict:
        """
        Compute measured attribution using blame chain (Part 11, M2).

        Categories:
        - EXECUTION_ON_CHAIN: Execution on the dependency blame chain
        - DEPENDENCY_WAIT: Time waiting for dependencies
        - RESOURCE_WAIT: Time waiting for resources
        - SCHEDULER_WAIT: Time waiting for scheduler dispatch
        - IDLE: Unexplained idle time
        - RETRY_WAIT: Time due to retry sequencing
        - UNTRACKED_HEAD: Time before first task
        - UNTRACKED_TAIL: Time after last task

        Args:
            graph_analysis: Pre-computed analyze_graph(...) result, reused
                from the caller (P1-21) rather than recomputed here -
                see _compute_floors's docstring for why. Computed
                internally only if not supplied.

        Returns:
            Dict containing attribution by category in microseconds
        """
        if not self.normalized_tasks or not self.blame_chain_analyzer or not self.graph:
            return {
                'execution_on_chain_us': 0,
                'dependency_wait_us': 0,
                'resource_wait_us': 0,
                'scheduler_wait_us': 0,
                'idle_us': 0,
                'retry_wait_us': 0,
                'untracked_head_us': 0,
                'untracked_tail_us': 0,
            }

        # Get graph analysis for depths and predecessors
        if graph_analysis is None:
            graph_analysis = analyze_graph(self.graph, self.normalized_tasks)
        
        # Build explicit predecessor map from graph, at task granularity.
        #
        # Element-level dependency edges (graph.dependencies) express "this
        # element requires that element's build to have completed" - the
        # real-world semantics of a BuildStream `depends:` edge. The
        # predecessor side is always the specific BUILD task of the upstream
        # element (not just "whichever task happened to match last", which
        # silently produced wrong/overwritten predecessors for any element
        # with more than one task kind - e.g. TRACK/FETCH/BUILD - and fed
        # bogus ready-time lookups downstream). An upstream element with no
        # BUILD task (e.g. a FAILed or TRACK/FETCH-only run) simply
        # contributes no edge, rather than a wrong one.
        #
        # The successor side is *every* task of the downstream element, not
        # just its BUILD task - the same intra-element propagation
        # bga/normalize/timestamps.py's clamp_task_starts gives every task
        # kind of a dependent element access to (via NormalizedTask itself),
        # even though ready-time *gating* (compute_ready_times) is scoped to
        # BUILD only (P1-27). Without this, a TRACK/FETCH task's real
        # cross-element wait had no explicit_predecessors entry, so the
        # blame-chain walk had no way to continue into the actual
        # responsible predecessor once it reached such a task - it just
        # stopped, silently dropping the segment that should have explained
        # the wait.
        #
        # Only build-gating edges are included (P4-11, same filter as
        # compute_ready_times/clamp_task_starts) - a runtime-only
        # dependency's BUILD finishing has no causal bearing on when the
        # successor's own work can start, so it must not become a
        # responsible predecessor in the blame chain either.
        build_task_by_element: Dict[str, str] = {}
        tasks_by_element: Dict[str, List[str]] = defaultdict(list)
        for task in self.normalized_tasks:
            key_str = str(task.task_key)
            tasks_by_element[task.task_key.element_uid].append(key_str)
            if task.task_key.task_kind == TaskKind.BUILD:
                build_task_by_element[task.task_key.element_uid] = key_str

        explicit_predecessors: Dict[str, List[str]] = {}
        for dep in self.graph.dependencies:
            if dep.dependency_type == "runtime":
                continue
            pred_key = build_task_by_element.get(dep.predecessor)
            if not pred_key:
                continue
            for succ_key in tasks_by_element.get(dep.successor, []):
                explicit_predecessors.setdefault(succ_key, []).append(pred_key)
        
        # Build finish time map
        task_finish_times: Dict[str, int] = {
            str(t.task_key): t.finish_us
            for t in self.normalized_tasks
        }
        
        # Use unweighted depth as proxy for task depths
        task_depths: Dict[str, int] = {}
        for task in self.normalized_tasks:
            elem_uid = task.task_key.element_uid
            task_depths[str(task.task_key)] = graph_analysis['unweighted_depth'].get(elem_uid, 0)

        # Identify genuine terminal tasks (P1-04): elements the graph
        # actually has no dependent for, or elements the run explicitly
        # requested as a target - covering the case of several
        # independent requested targets in one run, not just the single
        # element whose own finish happens to be latest. A blame-chain
        # walk is started from each; already_covered (inside
        # compute_full_attribution) prevents double-counting if two
        # terminals' walks converge on shared upstream lineage.
        successor_elements: Dict[str, List[str]] = defaultdict(list)
        for dep in self.graph.dependencies:
            successor_elements[dep.predecessor].append(dep.successor)

        terminal_element_uids = {
            elem.uid for elem in self.graph.elements
            if elem.requested_target or not successor_elements.get(elem.uid)
        }

        terminal_tasks: Set[str] = set()
        for elem_uid in terminal_element_uids:
            elem_task_keys = tasks_by_element.get(elem_uid, [])
            if not elem_task_keys:
                continue
            rep_key = build_task_by_element.get(elem_uid)
            if rep_key is None:
                rep_key = max(elem_task_keys, key=lambda k: task_finish_times.get(k, 0))
            terminal_tasks.add(rep_key)

        # Compute full attribution
        blame_chain, task_attributions, segments = self.blame_chain_analyzer.compute_full_attribution(
            explicit_predecessors,
            task_finish_times,
            task_depths,
            terminal_tasks=terminal_tasks or None,
        )
        
        # Reconcile attribution
        reconciled = self.blame_chain_analyzer.reconcile_attribution(segments)

        # Task-horizon boundaries (Part 13), reused below both for the
        # I4 task-horizon check and for UNTRACKED_HEAD/UNTRACKED_TAIL
        # (Part 11/12.1's full-wall-clock identity).
        min_start_us, max_finish_us, horizon_us = compute_task_horizon(self.normalized_tasks)

        # UNTRACKED_HEAD/UNTRACKED_TAIL (Part 11): the gap between the run's
        # wall-clock bounds and the first/last recognized task activity.
        # Only computable when run-context actually supplies wall-clock
        # bounds (Part 4.3's provenance hierarchy - falls back to 0/0, not
        # an estimate, when unavailable, rather than inventing a value).
        untracked_head_us = 0
        untracked_tail_us = 0
        if (
            self.run_context and self.normalized_tasks
            and self.run_context.wall_start_us is not None
            and self.run_context.wall_end_us is not None
        ):
            untracked_head_us = max(0, min_start_us - self.run_context.wall_start_us)
            untracked_tail_us = max(0, self.run_context.wall_end_us - max_finish_us)

        # Build result with all categories
        result = {
            'execution_on_chain_us': reconciled.get('EXECUTION_ON_CHAIN', 0),
            'dependency_wait_us': reconciled.get('DEPENDENCY_WAIT', 0),
            'resource_wait_us': reconciled.get('RESOURCE_WAIT', 0),
            'scheduler_wait_us': reconciled.get('SCHEDULER_WAIT', 0),
            'idle_us': reconciled.get('IDLE', 0),
            'retry_wait_us': reconciled.get('RETRY_WAIT', 0),
            'untracked_head_us': untracked_head_us,
            'untracked_tail_us': untracked_tail_us,
        }

        # I4 reconciliation check (Part 33/34): Sigma attribution must equal
        # the task horizon H exactly. P1-03/P1-04/P1-19/P1-20 closed every
        # known undercounting gap, so this should never fire today - but per
        # the spec's "no silent correction" philosophy (ordering violations
        # are reported, not hidden; resource ambiguity is UNKNOWN, not
        # invented), any future residual must be reported, not silently
        # absorbed. Never pad or truncate to force the sum to match.
        attribution_sum_us = sum(result[k] for k in (
            'execution_on_chain_us', 'dependency_wait_us', 'resource_wait_us',
            'scheduler_wait_us', 'idle_us', 'retry_wait_us',
        ))
        if attribution_sum_us != horizon_us:
            residual_us = horizon_us - attribution_sum_us
            logger.warning(
                "Attribution reconciliation (I4) failed: Sigma=%dus != H=%dus (residual %dus)",
                attribution_sum_us, horizon_us, residual_us,
            )
            self.violations.append({
                'type': 'attribution_reconciliation',
                'invariant': 'I4',
                'attribution_sum_us': attribution_sum_us,
                'horizon_us': horizon_us,
                'residual_us': residual_us,
            })

        # Store detailed attribution for later use
        self._task_attributions = task_attributions
        self._blame_chain = blame_chain
        self._attribution_segments = segments

        return result

    def _check_process_oversubscription(self) -> None:
        """UX-12: `--builders` (this run's `resource_capacities.PROCESS`)
        and native `--max-jobs` (each element's own internal `make -jN`/
        `ninja` parallelism, `run_context.native_max_jobs`) both consume
        the same physical CPU cores, uncoordinated - confirmed with real
        timing evidence in docs/scenarios/UX-09-builders-max-jobs-joint-
        optimization.md (examples/05-cmake-cpp-toolchain: 8 builders x 8
        max-jobs on a real 4-core host measured ~11% slower than
        BuildStream's own 4x4 defaults on that same host).

        UX-15: the *governing* ceiling for this check is the operator's
        declared `cpu_budget` when present, not the raw detected
        `host_cpu_count` - a cgroup CFS CPU quota (what `docker run
        --cpus=N`/Kubernetes CPU limits actually use) throttles CPU time,
        not core affinity, so `os.sched_getaffinity` (host_cpu_count's own
        detection method) cannot see it; an operator may also simply
        intend to reserve headroom. Both values, when known, are kept and
        surfaced separately (never silently discarding the detected
        value) - if the declared budget itself exceeds what the
        environment can actually provide, that is its own real signal
        (`cpu_budget_exceeds_host_capacity`), not something to paper over.

        All of `builders`, `native_max_jobs`, and a governing core count
        (`cpu_budget` or `host_cpu_count`) are best-effort/optional - this
        check only runs when they're actually present.

        Threshold: compares this run's real declared concurrency demand
        (`builders * native_max_jobs`) against what BuildStream's own
        real defaults would produce given the governing core count
        (`builders=4` - confirmed in `buildstream/data/userconfig.yaml`;
        `max_jobs = min(cores, 8)` - confirmed in `buildstream/_context.py`'s
        `effective_build_max_jobs`) - i.e. "did this run ask for
        meaningfully more concurrent process slots than BuildStream would
        have used unconfigured against this ceiling", the exact
        real-world comparison UX-09's own 4x4-vs-8x8 evidence supports,
        rather than an arbitrary constant. This is a coarse, config-level
        signal (declared capacity, not measured achieved concurrency) -
        see UX-14 for why it can't fully replace real per-task profiling.
        """
        if not self.run_context:
            return
        builders = self.run_context.resource_capacities.get('PROCESS')
        native_max_jobs = self.run_context.native_max_jobs
        host_cpu_count = self.run_context.host_cpu_count
        cpu_budget = self.run_context.cpu_budget

        if cpu_budget is not None and host_cpu_count is not None and cpu_budget > host_cpu_count:
            logger.warning(
                "declared cpu_budget=%d exceeds this environment's detected "
                "host_cpu_count=%d - the declared budget itself may be "
                "unrealistic here (see UX-15)",
                cpu_budget, host_cpu_count,
            )
            self.violations.append({
                'type': 'cpu_budget_exceeds_host_capacity',
                'cpu_budget': cpu_budget,
                'host_cpu_count': host_cpu_count,
            })

        governing_cores = cpu_budget if cpu_budget is not None else host_cpu_count
        capacity_source = 'declared_cpu_budget' if cpu_budget is not None else 'detected_host_cpu_count'
        # UX-16: explicit `is None` checks, not truthiness - `builders`/
        # `native_max_jobs`/`governing_cores` of 0 are real, present data
        # (BuildStream's own documented `--max-jobs 0` sentinel, resolved
        # just below), not "missing." `not 0` is True in Python, so a
        # truthiness check here would silently skip this entire function
        # for exactly the runs most worth checking.
        if builders is None or native_max_jobs is None or governing_cores is None:
            # UX-29: a check that silently declines to run is
            # indistinguishable, in the report, from a check that ran and
            # found nothing. Every capacity guard built across
            # UX-12/15/16/17/21 keys off these three inputs, so say which
            # one was missing rather than returning in silence.
            missing = [
                name for name, value in (
                    ('builders', builders),
                    ('native_max_jobs', native_max_jobs),
                    ('governing core count (host_cpu_count/cpu_budget)', governing_cores),
                ) if value is None
            ]
            logger.info("capacity checks not run - missing: %s", ", ".join(missing))
            # Recorded on the analyzer, not appended to `violations`:
            # nothing about this build is wrong, the tool simply could not
            # check. It surfaces in the capacity-model note (UX-13), which
            # is always printed and is already the place that states what
            # LB/Efficiency Score do and do not certify against.
            self.capacity_check_skipped_inputs = missing
            return

        # BuildStream's own real, documented meaning of `--max-jobs 0`:
        # "let BuildStream choose - up to the available host threads,
        # capped at 8" - the same resolution `default_demand` already
        # applies for BuildStream's own unconfigured behavior below, so
        # `max-jobs: 0` is BuildStream choosing that same behavior, not a
        # different one. Resolved once, explicitly, rather than treating
        # a literal 0 as "zero parallelism" anywhere in the demand math.
        resolved_native_max_jobs = min(governing_cores, 8) if native_max_jobs == 0 else native_max_jobs
        native_max_jobs_was_auto = native_max_jobs == 0

        actual_demand = builders * resolved_native_max_jobs
        # Kept only as *context* in the message now, never as the bar
        # (UX-28): "what BuildStream would do unconfigured" is a moving
        # target that says nothing about this host. `4 * min(cores, 8)`
        # is 4x the cores on a 4-core host but only 0.5x on a 64-core
        # one, so the ratio at which the old check fired collapsed as the
        # host grew - on anything above 8 cores it flagged configurations
        # that were *below* one process per core, while the undersubscription
        # branch just below considers exactly that condition idle capacity.
        default_demand = 4 * min(governing_cores, 8)
        oversubscription_ceiling = governing_cores * _OVERSUBSCRIPTION_DEMAND_RATIO

        if actual_demand > oversubscription_ceiling:
            logger.warning(
                "builders=%d x native max-jobs=%d%s = %d potential concurrent "
                "processes vs a governing ceiling of %d cores (%s) - more than "
                "%gx the cores, past the ratio UX-09 measured as genuinely "
                "slower on a real host (BuildStream's own unconfigured default "
                "here would be %d)",
                builders, resolved_native_max_jobs,
                " (resolved from BuildStream's own max-jobs=0 auto sentinel)" if native_max_jobs_was_auto else "",
                actual_demand, governing_cores, capacity_source,
                _OVERSUBSCRIPTION_DEMAND_RATIO, default_demand,
            )
            self.violations.append({
                'type': 'resource_oversubscription',
                'builders': builders,
                'native_max_jobs': resolved_native_max_jobs,
                'native_max_jobs_was_auto': native_max_jobs_was_auto,
                'actual_demand': actual_demand,
                'governing_cores': governing_cores,
                'capacity_source': capacity_source,
                'host_cpu_count': host_cpu_count,
                'cpu_budget': cpu_budget,
                'default_demand': default_demand,
                'oversubscription_ceiling': oversubscription_ceiling,
                'demand_ratio': actual_demand / governing_cores if governing_cores else None,
            })
        elif actual_demand < governing_cores:
            logger.info(
                "builders=%d x native max-jobs=%d%s = %d potential concurrent "
                "processes vs a governing ceiling of %d cores (%s) - fewer "
                "than one process per core, may be leaving cores idle",
                builders, resolved_native_max_jobs,
                " (resolved from BuildStream's own max-jobs=0 auto sentinel)" if native_max_jobs_was_auto else "",
                actual_demand, governing_cores, capacity_source,
            )
            self.violations.append({
                'type': 'resource_undersubscription',
                'builders': builders,
                'native_max_jobs': resolved_native_max_jobs,
                'native_max_jobs_was_auto': native_max_jobs_was_auto,
                'actual_demand': actual_demand,
                'governing_cores': governing_cores,
                'capacity_source': capacity_source,
                'host_cpu_count': host_cpu_count,
                'cpu_budget': cpu_budget,
            })

        # UX-28: a second, independent and much sharper signal. The
        # product check above is over *potential* demand, which UX-09
        # showed can overstate reality badly - its own 4x16 configuration
        # reached the same 64 potential processes as the 8x8 one and cost
        # nothing, because each element only had two source files, so the
        # extra `make -j` slots were never claimed. `builders` has no
        # such escape hatch: BuildStream really does dispatch that many
        # elements at once, and each one runs at least one process. More
        # concurrently-dispatched elements than cores means the host is
        # oversubscribed even at `--max-jobs 1`.
        #
        # This is also what actually separates UX-09's two same-product
        # configurations: 8x8 (8 builders on 4 cores) measured ~11%
        # slower than the best config; 4x16 (4 builders) did not.
        if builders > governing_cores:
            logger.warning(
                "builders=%d exceeds the governing ceiling of %d cores (%s) - "
                "BuildStream dispatches that many elements concurrently and each "
                "runs at least one process, so the host is oversubscribed even at "
                "--max-jobs 1 (see UX-09/UX-28)",
                builders, governing_cores, capacity_source,
            )
            self.violations.append({
                'type': 'dispatch_oversubscription',
                'builders': builders,
                'governing_cores': governing_cores,
                'capacity_source': capacity_source,
                'host_cpu_count': host_cpu_count,
                'cpu_budget': cpu_budget,
            })

    def _check_memory_oversubscription(self) -> None:
        """UX-21: every concurrently-running build subprocess also
        consumes real memory (compilers, especially C++ ones doing heavy
        template instantiation or LTO, can each use gigabytes) -
        pushing the build host into swap is a qualitatively worse
        failure mode than CPU oversubscription (the whole machine
        thrashes, every process, not just the build slowing down).
        Independent of `_check_process_oversubscription`'s own CPU-core
        check - a config can be memory-oversubscribed while CPU-fine, or
        vice versa - so this is its own, distinct violation type rather
        than folded into `resource_oversubscription`.

        No real per-task memory measurement source exists in this
        ingestion pipeline (mirrors `UX-12`/`UX-15`'s own CPU-side
        honesty, and `P1-33`'s "never fabricate a measurement" rule) -
        this is a coarse, explicitly-labeled *estimate*: `builders x
        native_max_jobs x estimated_job_memory_mb` (both purely
        operator-declared - `RunContext.memory_budget_mb`/
        `estimated_job_memory_mb`) compared against the operator's
        declared memory envelope. All four inputs are best-effort/
        optional - this check only runs when they're all actually
        present.
        """
        if not self.run_context:
            return
        builders = self.run_context.resource_capacities.get('PROCESS')
        native_max_jobs = self.run_context.native_max_jobs
        memory_budget_mb = self.run_context.memory_budget_mb
        estimated_job_memory_mb = self.run_context.estimated_job_memory_mb

        # UX-16: explicit `is None` checks, not truthiness - see
        # _check_process_oversubscription's own comment on this.
        if (
            builders is None or native_max_jobs is None
            or memory_budget_mb is None or estimated_job_memory_mb is None
        ):
            return

        if native_max_jobs == 0:
            # BuildStream's own real "auto" sentinel (UX-16) - resolving
            # it needs a governing CPU-core count, same as
            # _check_process_oversubscription's own resolution (this is
            # BuildStream's own CPU-core-based behavior, not something
            # specific to the memory dimension). If neither is known,
            # skip rather than silently treat the literal 0 as "no
            # parallelism" - that would understate real memory demand,
            # the exact class of bug UX-16 fixed for the CPU check.
            governing_cores = (
                self.run_context.cpu_budget
                if self.run_context.cpu_budget is not None
                else self.run_context.host_cpu_count
            )
            if governing_cores is None:
                return
            resolved_native_max_jobs = min(governing_cores, 8)
            native_max_jobs_was_auto = True
        else:
            resolved_native_max_jobs = native_max_jobs
            native_max_jobs_was_auto = False

        estimated_demand_mb = builders * resolved_native_max_jobs * estimated_job_memory_mb

        if estimated_demand_mb > memory_budget_mb:
            logger.warning(
                "estimated memory demand: builders=%d x native max-jobs=%d%s x "
                "~%dMB/job = ~%dMB vs a declared memory budget of %dMB - risk of "
                "swap (see UX-21); this is a config-driven estimate, not a "
                "real per-task memory measurement",
                builders, resolved_native_max_jobs,
                " (resolved from BuildStream's own max-jobs=0 auto sentinel)" if native_max_jobs_was_auto else "",
                estimated_job_memory_mb, estimated_demand_mb, memory_budget_mb,
            )
            self.violations.append({
                'type': 'memory_oversubscription',
                'builders': builders,
                'native_max_jobs': resolved_native_max_jobs,
                'native_max_jobs_was_auto': native_max_jobs_was_auto,
                'estimated_job_memory_mb': estimated_job_memory_mb,
                'estimated_demand_mb': estimated_demand_mb,
                'memory_budget_mb': memory_budget_mb,
            })

    def _compute_occupancy_ratio(self, horizon_us: int) -> Optional[float]:
        """UX-27: sum of real task slot-occupancy over the dispatch
        capacity that was available for the whole run.

        Denominator is `builders` (dispatch slots), not a CPU core count:
        the numerator is slot-time, so this is dimensionally a slot
        utilisation, and `builders` is the one capacity `bga` genuinely
        knows for every run. None - never fabricated - when either input
        is missing.
        """
        if not self.run_context or horizon_us <= 0:
            return None
        builders = self.run_context.resource_capacities.get('PROCESS')
        if not builders or builders <= 0:
            return None
        occupied_us = sum(task.dur_us for task in self.normalized_tasks)
        return occupied_us / (horizon_us * builders)

    def _build_capacity_verdict(self) -> dict:
        """UX-35: a small, already-decided summary of this run's capacity
        situation, for consumers that must not re-derive it.

        `checks_ran` is the load-bearing field: "the checks ran and found
        no oversubscription" and "the checks could not run at all" look
        identical from `violations` alone, and advice conditioned on the
        second as if it were the first is exactly the failure this task
        exists to fix.
        """
        types = {v.get('type') for v in self.violations}
        skipped = list(getattr(self, 'capacity_check_skipped_inputs', []) or [])
        return {
            'oversubscribed': bool(
                types & {'resource_oversubscription', 'dispatch_oversubscription'}
            ),
            'undersubscribed': 'resource_undersubscription' in types,
            'checks_ran': not skipped,
            'skipped_inputs': skipped,
        }

    def _build_capacity_model_note(self) -> str:
        """UX-13: `LB`/`Efficiency Score` are correctly computed per spec
        Part 16, but only ever certify against this run's *recorded*
        resource capacities (`builders`/`fetchers`/`pushers`) - not real
        host CPU cores. Native build-system parallelism (`--max-jobs`) is
        a separate axis LB's own math does not model (see UX-09's real
        evidence this can matter, and UX-14 for why `bga sweep`/`replay`
        share the same blind spot). Always returns a note - even when
        UX-12's `native_max_jobs`/`host_cpu_count` aren't available, a
        reader still shouldn't assume a high Efficiency Score means no
        further gains exist on this host. Enriched with this run's own
        real numbers when UX-12's `resource_oversubscription` violation
        fired for it, computed here (not in the report formatter) so
        `--format json` and `--format text` both see the same value from
        a single source of truth.
        """
        oversub = next(
            (v for v in self.violations if v.get('type') == 'resource_oversubscription'), None,
        )
        if oversub:
            if oversub.get('capacity_source') == 'declared_cpu_budget':
                ceiling_desc = f"your declared CPU budget of {oversub.get('governing_cores')} cores"
            else:
                ceiling_desc = f"a {oversub.get('governing_cores')}-core host"
            return (
                f"This run shows real resource oversubscription (builders="
                f"{oversub.get('builders')} x native max-jobs={oversub.get('native_max_jobs')} "
                f"= {oversub.get('actual_demand')} processes vs {ceiling_desc}) - LB/Efficiency "
                f"Score certify against recorded resource capacities, not real host CPU cores "
                f"(or your declared budget), so Efficiency Score may overstate real efficiency "
                f"here (see UX-09/UX-15)."
            )
        note = (
            "LB/Efficiency Score certify against this run's recorded resource "
            "capacities (builders/fetchers/pushers), not real host CPU cores or any "
            "declared CPU budget - native build-system parallelism (--max-jobs) is a "
            "separate, currently unmodeled axis (see UX-09/UX-15)."
        )
        # UX-29: a capacity guard that declined to run is indistinguishable,
        # in the report, from one that ran and found nothing - and until
        # UX-29 auto-recovered `native_max_jobs` from the wrapped log's own
        # recorded invocation, that was the state of every run the
        # documented pipeline produced. Say it, in the one note that is
        # always printed.
        if getattr(self, 'capacity_check_skipped_inputs', None):
            note += (
                " Capacity checks (over/under-subscription, memory) did not run for "
                "this run - missing: " + ", ".join(self.capacity_check_skipped_inputs)
                + ". They are inert here, not passing; a wrapped log records "
                "--max-jobs on its own first line (UX-29), or declare the missing "
                "value explicitly at extraction time."
            )
        return note

    def analyze(self, run_dir: Optional[Path] = None) -> AnalysisResult:
        """
        Perform complete analysis.
        
        Executes the full pipeline:
        1. Trace normalization (M0)
        2. Occupancy analysis (M0)
        3. Graph analysis (M1)
        4. Attribution (M2)
        5. Floors computation (M3)
        6. CPU utilization analysis (M4)
        7. Advanced diagnostics (M5)
        8. Structural analysis (M6)
        
        Args:
            run_dir: Path to run directory (uses instance run_dir if not provided)
        
        Returns:
            AnalysisResult with all computed metrics
        """
        # Load data if needed
        if run_dir is not None:
            self.load(run_dir)
        elif self.run_dir is not None and (self.run_context is None or self.graph is None or self.trace is None):
            self.load()
        
        if self.normalized_tasks is None or len(self.normalized_tasks) == 0:
            self.normalize()
        
        result = AnalysisResult()
        
        # Set run_id and total_duration from context/trace. Previously
        # read a `run_id`/`uuid` attribute RunContext has never actually
        # defined (always '' in practice) - now the real run-identity
        # manifest_hash (P1-37), when available.
        if self.run_context and self.run_context.run_identity:
            result.run_id = self.run_context.run_identity.get('manifest_hash', '') or ''
        
        # Compute horizon for total duration
        occupancy_stats = compute_occupancy_stats(self.normalized_tasks)
        horizon_us = occupancy_stats.get('horizon_us', 0)

        # Total Duration (Part 4.3): the spec's own preferred definition
        # is the run's real wall-clock window (run_context.wall_start/
        # wall_end); the tracked-task horizon is explicitly marked
        # "reduced provenance" - a fallback for when wall-clock bounds
        # aren't available, not the primary definition. Using the horizon
        # unconditionally (as before) understated real wall-clock time
        # whenever meaningful pre-task overhead exists (BuildStream's own
        # startup, large sandbox-staging cost) - confirmed via a real run
        # where the reported Total Duration was 4.0s against a real 7.6s
        # wall clock (docs/scenarios/UX-10-total-duration-excludes-pre-
        # task-overhead.md). UNTRACKED_HEAD/UNTRACKED_TAIL (computed
        # above in _compute_attribution) are already wall-clock-relative,
        # so this also makes the Attribution Breakdown's percentages
        # (each category / total_duration_us) sum to 100% again, per Part
        # 12's exact identity (UNTRACKED_HEAD + task-horizon attribution
        # + UNTRACKED_TAIL == wall_clock).
        if (
            self.run_context
            and self.run_context.wall_start_us is not None
            and self.run_context.wall_end_us is not None
        ):
            wall_clock_us = self.run_context.wall_end_us - self.run_context.wall_start_us
            result.total_duration_us = wall_clock_us
            # Part 13: "wall_clock >= H is a provenance/containment
            # relationship" - a real violation of this (not just an
            # unlikely edge case) is exactly the symptom a corrupted
            # timestamp reconstruction produces (see UX-06's raw-log
            # elapsed-time bug), so it's reported, not silently ignored.
            if wall_clock_us < horizon_us:
                logger.warning(
                    "Wall clock (%dus) is less than task horizon (%dus) - "
                    "this violates Part 13's containment relationship and "
                    "usually indicates corrupted timestamp reconstruction",
                    wall_clock_us, horizon_us,
                )
                self.violations.append({
                    'type': 'wall_clock_containment',
                    'invariant': 'Part 13',
                    'wall_clock_us': wall_clock_us,
                    'horizon_us': horizon_us,
                })
        else:
            result.total_duration_us = horizon_us

        self._check_process_oversubscription()
        self._check_memory_oversubscription()

        # Pipeline overhead (P4-14, non-spec additive signal) - see
        # docs/tasks/P4-14-cache-query-overhead-visibility.md
        result.pipeline_overhead = self._compute_pipeline_overhead(result.total_duration_us)

        # Element-kind summary (P4-12 Direction 3, non-spec additive
        # signal) - see docs/tasks/P4-12-element-kind-based-heuristics.md
        result.element_kind_summary = self._compute_element_kind_summary()
        
        # Occupancy analysis (M0)
        occupancy_stats = compute_occupancy_stats(self.normalized_tasks)
        result.occupancy = {
            'average_concurrency': occupancy_stats['average_concurrency'],
            'peak_concurrency': occupancy_stats['peak_concurrency'],
            'horizon_start_us': occupancy_stats['horizon_start'],
            'horizon_end_us': occupancy_stats['horizon_end'],
            'horizon_us': occupancy_stats['horizon_us'],
            'idle_us': occupancy_stats['idle_us'],
            'resource_occupancy': {
                str(k): v for k, v in occupancy_stats['resource_occupancy'].items()
            },
            'peak_resource_occupancy': {
                str(k): v for k, v in occupancy_stats['peak_resource_occupancy'].items()
            },
        }
        
        # Graph analysis (M1) - computed once and reused by _compute_floors/
        # _compute_attribution below (P1-21) instead of each recomputing it
        # independently (previously 3x per analyze() call, tripling the
        # cost of compute_reachability inside it - the single largest
        # remaining hotspot after P1-16's fix).
        graph_analysis = None
        if self.graph:
            graph_analysis = analyze_graph(self.graph, self.normalized_tasks)
            result.signals = {
                'critical_path': graph_analysis['critical_path'],
                'critical_path_length': graph_analysis['critical_path_length'],
                'critical_path_detail': self._build_critical_path_detail(
                    graph_analysis['critical_path']
                ),
                'downstream_count': graph_analysis['downstream_count'],
                'slack': graph_analysis['slack'],
                'unweighted_depth': graph_analysis['unweighted_depth'],
            }

        # Floors (M3)
        result.floors = self._compute_floors(graph_analysis)
        result.floors['capacity_model_note'] = self._build_capacity_model_note()

        # Attribution (M2)
        result.attribution = self._compute_attribution(graph_analysis)
        
        # CPU Utilization (M4)
        result.utilisation = self._compute_utilization(occupancy_stats)
        
        # Advanced Diagnostics (M5)
        result.signals.update(self._compute_diagnostics(occupancy_stats, graph_analysis))
        
        # Structural Analysis (M6)
        result.structural = self._compute_structural_analysis()
        
        # Violations
        result.violations = self.violations

        # UX-35: publish the capacity verdict the checks above already
        # reached, so the report layer can condition its next-step hints
        # on it instead of deriving a second, independent capacity
        # formula (UX-17's own resolved rule).
        result.capacity_verdict = self._build_capacity_verdict()
        
        # Confidence (Part 33)
        result.confidence = self._compute_confidence(graph_analysis, result.attribution, result.floors)

        self.analysis_result = result
        return result

    def _compute_pipeline_overhead(self, horizon_us: int) -> dict:
        """BuildStream's own top-level "main:core activity" pipeline
        phases (Query cache, Resolving elements, Loading elements,
        Initializing remote caches) are real work with a real elapsed
        cost - confirmed material on a real ~2000-element fully-cached
        rebuild (Query cache + Resolving elements together were ~87% of
        total wall time there - see
        docs/tasks/P4-14-cache-query-overhead-visibility.md's
        Verification Log), but they are not attributable to any
        individual element, only to the pipeline as a whole.
        `tools/bst_extract_run.py` extracts them into
        run-context.json's `pipeline_overhead` field; this is a thin
        pass-through plus a total/fraction-of-horizon summary - a
        deliberately coarse, one-number-per-phase signal, never a
        fabricated per-element breakdown (this codebase's "no silent
        correction" discipline).
        """
        entries = self.run_context.pipeline_overhead if self.run_context else []
        if not entries:
            return {}
        phases = [
            {'phase': e.get('phase', ''), 'elapsed_us': e.get('elapsed_us', 0)}
            for e in entries
        ]
        total_us = sum(p['elapsed_us'] for p in phases)
        return {
            'phases': phases,
            'total_us': total_us,
            'fraction_of_horizon': (total_us / horizon_us) if horizon_us else None,
            'note': (
                'Not attributable to individual elements - BuildStream logs '
                'these as pipeline-level operations, not per-element tasks.'
            ),
        }

    def _build_critical_path_detail(self, critical_path: List[str]) -> List[dict]:
        """UX-33: per-element detail for every critical-path element, so
        the text report can name the whole chain instead of printing a
        bare length.

        The path itself (`signals['critical_path']`) was always
        computed and always correct; `bga/report/text.py` simply refused
        to print it above 5 elements - i.e. exactly when a reader cannot
        reconstruct it from memory. Naming what was already computed is
        the same fix `UX-25` applied to coverage-gate violations, and
        this carries the same two facts that fix found useful: the real
        measured duration (so a reader can see *which link* dominates)
        and whether the element is structural (`STRUCTURAL_ELEMENT_KINDS`,
        P4-12 - a `stack`/`import` on the path is real graph structure
        but has no build commands to speed up).

        `share_of_path` is each element's fraction of the summed
        critical-path durations, not of total build time - the path's
        own internal weighting is the question this answers ("where on
        the chain is the time?"). Elements with no measured task
        (structural ones typically) report `duration_us: 0` rather than
        being omitted, so the printed chain is the real chain.
        """
        if not critical_path:
            return []
        duration_by_uid: Dict[str, int] = defaultdict(int)
        for task in self.normalized_tasks:
            duration_by_uid[task.task_key.element_uid] += task.dur_us
        kind_by_uid = self._element_kind_lookup()
        path_total_us = sum(duration_by_uid.get(uid, 0) for uid in critical_path)
        return [
            {
                'element_uid': uid,
                'element_kind': kind_by_uid.get(uid, 'unknown'),
                'is_structural_kind': kind_by_uid.get(uid) in STRUCTURAL_ELEMENT_KINDS,
                'duration_us': duration_by_uid.get(uid, 0),
                'share_of_path': (
                    duration_by_uid.get(uid, 0) / path_total_us if path_total_us else None
                ),
            }
            for uid in critical_path
        ]

    def _element_kind_lookup(self) -> Dict[str, str]:
        """uid -> element_kind, defaulting to the explicit "unknown"
        bucket (never silently omitted - P4-12's own Out of Scope: an
        unrecognized/absent kind must never be misclassified, only
        called out as genuinely unknown)."""
        if not self.graph:
            return {}
        return {e.uid: (e.element_kind or "unknown") for e in self.graph.elements}

    def _compute_element_kind_summary(self) -> dict:
        """Aggregate stats grouped by element_kind (P4-12 Direction 3,
        `bga graph --by-kind`) - count, total observed duration, average
        duration, per kind. Purely additive/presentational: reads
        already-computed per-task durations, changes no existing
        computation. See
        docs/tasks/P4-12-element-kind-based-heuristics.md.
        """
        if not self.graph:
            return {}
        duration_by_uid: Dict[str, int] = defaultdict(int)
        for task in self.normalized_tasks:
            duration_by_uid[task.task_key.element_uid] += task.dur_us

        summary: Dict[str, dict] = {}
        for elem in self.graph.elements:
            kind = elem.element_kind or "unknown"
            entry = summary.setdefault(kind, {"count": 0, "total_duration_us": 0})
            entry["count"] += 1
            entry["total_duration_us"] += duration_by_uid.get(elem.uid, 0)
        for entry in summary.values():
            entry["avg_duration_us"] = entry["total_duration_us"] / entry["count"] if entry["count"] else 0.0
        return summary

    def _compute_confidence(self, graph_analysis: Optional[dict], attribution: dict, floors: dict) -> dict:
        """
        Compute confidence metrics (Part 33) - see
        bga.validation.invariants.compute_confidence for the full
        computation. Thin orchestrator: appends the hard-gate-failure
        violations that function finds to self.violations (kept as a
        side effect here, at the call site, rather than inside the
        extracted function, so bga.validation.invariants.compute_confidence
        stays a pure function of its inputs - bga/floors/, bga/report/,
        bga/validation/ extraction, P1-15).
        """
        confidence, new_violations = compute_confidence(
            self.normalized_tasks, self.run_context, self.trace, self.graph,
            self.violations, getattr(self, '_attribution_segments', []),
            graph_analysis, attribution, floors,
        )
        self.violations.extend(new_violations)
        return confidence

    def _compute_utilization(self, occupancy_stats: dict) -> dict:
        """
        Compute CPU utilization analysis (M4, Part 30).
        
        Args:
            occupancy_stats: Occupancy statistics from sweep analysis
            
        Returns:
            Dict containing utilization metrics including:
            - effective_cpus
            - capacity_cpu_us
            - buckets (useful, idle, wasted, etc.)
            - oversubscription analysis
            - reconciliation error
        """
        if not self.utilization_analyzer or not self.run_context:
            return {}
        
        # Build task intervals from real, measured wall-clock job-slot
        # occupancy (task.dur_us - how long each task actually held a job
        # slot, real data). This is NOT a CPU-time measurement (P1-33) -
        # UtilizationAnalyzer's bucket totals (useful/wasted-retry/
        # wasted-rebuild) stay meaningful under this honest wall-clock-
        # occupancy interpretation regardless of whether real CPU
        # accounting is available; the capacity-derived metrics that
        # *would* require a genuine CPU measurement (capacity_cpu_us,
        # the *_pct properties, I9 reconciliation, Part 30.3's
        # oversubscription check) are gated on
        # UtilizationResult.cpu_accounting_available instead of
        # computed against this occupancy data as if it were CPU time.
        task_intervals = []
        for task in self.normalized_tasks:
            interval = {
                'task_key': str(task.task_key),
                'start_us': task.start_us,
                'end_us': task.finish_us,
                'cpu_usage_us': task.dur_us,
                'concurrent_tasks': [str(task.task_key)],
                # UX-48: `[ready_us, start_us)` is the window in which
                # this task was dependency-ready but had not been
                # dispatched - the evidence that distinguishes idle
                # capacity meaning "nothing could run" from idle
                # capacity meaning "nothing was scheduled". `ready_us`
                # is a real `max(finish(predecessors))` from
                # bga/normalize/timestamps.py, so no new capture or
                # graph plumbing is needed for the split.
                'ready_us': task.ready_us,
            }
            task_intervals.append(interval)
        
        # Convert occupancy segments to format expected by utilization analyzer
        occupancy_segments = []
        if 'segments' in occupancy_stats:
            for seg in occupancy_stats['segments']:
                # Segments are tuples: (start_us, end_us, active_tasks_set, resource_counts_dict)
                if isinstance(seg, tuple):
                    start_us, end_us, active_tasks, _ = seg
                else:
                    start_us = seg.start_us
                    end_us = seg.end_us
                    active_tasks = seg.active_tasks
                
                occupancy_segments.append({
                    'start_us': start_us,
                    'end_us': end_us,
                    'active_tasks': list(active_tasks),
                })
        
        # Run utilization analysis. UX-17: evidence source 1 (Part 30.3's
        # config-based oversubscription check) delegates to
        # _check_process_oversubscription's (UX-12) own already-computed
        # verdict - self.violations is already populated by the time this
        # runs (_check_process_oversubscription is called early in
        # analyze(), well before _compute_utilization).
        oversubscription_violation = next(
            (v for v in self.violations if v.get('type') == 'resource_oversubscription'), None,
        )
        util_result = self.utilization_analyzer.analyze(
            task_intervals=task_intervals,
            occupancy_segments=occupancy_segments,
            retry_tasks=compute_retry_tasks(self.normalized_tasks),
            rebuild_tasks=compute_rebuild_tasks(
                self.graph, self.normalized_tasks, self.historical_runs,
            ),
            oversubscription_violation=oversubscription_violation,
        )
        
        # Store result for later access
        self._utilization_result = util_result
        
        return util_result.to_dict()
    
    def _compute_diagnostics(self, occupancy_stats: dict, graph_analysis: dict) -> dict:
        """
        Compute advanced diagnostics (M5, Parts 20-29).
        
        Args:
            occupancy_stats: Occupancy statistics from sweep analysis
            graph_analysis: Graph analysis results
            
        Returns:
            Dict containing diagnostic metrics including:
            - wall_clock_share
            - ready_queue
            - blast_radius
            - criticality_probability
            - fetch_build_overlap
            - duration_variability
            - leaf_analysis
        """
        if not self.normalized_tasks or not graph_analysis:
            return {}
        
        # Get blame chain and critical path from attribution/graph
        blame_chain = None
        if hasattr(self, '_blame_chain'):
            # P1-22: was str(t) - t is a BlameChainNode with no __str__
            # override, so this produced default object-repr strings
            # (e.g. "<BlameChainNode object at 0x...>") that could never
            # match a real task_key string anywhere downstream. Every
            # on_blame_chain check in DiagnosticsAnalyzer was structurally
            # always False as a result.
            blame_chain = [str(t.task_key) for t in self._blame_chain]
        
        critical_path = graph_analysis.get('critical_path', [])
        slack = graph_analysis.get('slack', {})
        
        # Convert occupancy segments
        occupancy_segments = []
        if 'segments' in occupancy_stats:
            for seg in occupancy_stats['segments']:
                # Segments are tuples: (start_us, end_us, active_tasks_set, resource_counts_dict)
                if isinstance(seg, tuple):
                    start_us, end_us, active_tasks, _ = seg
                else:
                    start_us = seg.start_us
                    end_us = seg.end_us
                    active_tasks = seg.active_tasks
                
                occupancy_segments.append({
                    'start_us': start_us,
                    'end_us': end_us,
                    'active_tasks': list(active_tasks),
                })
        
        # Resource capacities
        resource_caps = {}
        if self.run_context:
            resource_caps = self.run_context.resource_capacities or {}
        
        # Requested targets, from the graph's own requested_target markers.
        # Previously hardcoded to None, which made compute_leaf_analysis's
        # `if not requested_targets: reachable_from_targets = <everything>`
        # fallback fire unconditionally - every element was treated as
        # "required by target" regardless of what the graph actually
        # declared, so no leaf could ever be flagged deferrable (P1-11).
        requested_targets = None
        if self.graph:
            explicit_targets = {elem.uid for elem in self.graph.elements if elem.requested_target}
            requested_targets = explicit_targets or None
        
        # Historical durations (not available in single-run analysis)
        historical_durations = None
        
        # Run diagnostics analysis
        diag_result = analyze_diagnostics(
            normalized_tasks=self.normalized_tasks,
            graph_analysis=graph_analysis,
            blame_chain=blame_chain,
            critical_path=critical_path,
            slack=slack,
            occupancy_segments=occupancy_segments,
            resource_capacities=resource_caps,
            requested_targets=requested_targets,
            historical_durations=historical_durations,
        )
        
        # Store for later access
        self._diagnostics_result = diag_result
        
        # Convert to signals dict format
        signals = {}
        kind_by_uid = self._element_kind_lookup()
        
        # Wall-clock share (Part 20)
        if diag_result.wall_clock_shares:
            signals['wall_clock_share'] = {
                s.task_key: s.wall_clock_share_us for s in diag_result.wall_clock_shares
            }
        
        # Ready queue (Part 21)
        if diag_result.ready_queue:
            signals['ready_queue'] = {
                'average_depth': diag_result.ready_queue.average_depth,
                'peak_depth': diag_result.ready_queue.peak_depth,
                'nonzero_fraction': diag_result.ready_queue.nonzero_fraction,
            }
        
        # Blast radius (Part 25)
        if diag_result.blast_radius:
            signals['blast_radius'] = {
                br.element_uid: {
                    'downstream_count': br.downstream_count,
                    'weighted_duration_us': br.downstream_weighted_duration_us,
                    'is_leaf': br.is_leaf,
                    'risk_score': br.risk_score,
                    # P4-12 Direction 1/2 (non-spec, additive, presentation
                    # only - never changes downstream_count/risk_score
                    # above, which stay the real, directly-observed data).
                    'element_kind': kind_by_uid.get(br.element_uid, 'unknown'),
                    'is_structural_kind': kind_by_uid.get(br.element_uid) in STRUCTURAL_ELEMENT_KINDS,
                }
                for br in diag_result.blast_radius
            }
            signals['top_blast_radius'] = [
                br.element_uid for br in diag_result.top_blast_radius_elements[:5]
            ]
        
        # Criticality probability (Part 26)
        if diag_result.criticality_probabilities:
            signals['criticality_probability'] = {
                cp.element_uid: {
                    'probability': cp.probability,
                    'observed_critical': cp.observed_critical,
                    'slack_us': cp.observed_slack_us,
                    # P4-12 Direction 1/2 (non-spec, additive, presentation
                    # only) - see the blast_radius block above.
                    'element_kind': kind_by_uid.get(cp.element_uid, 'unknown'),
                    'is_structural_kind': kind_by_uid.get(cp.element_uid) in STRUCTURAL_ELEMENT_KINDS,
                }
                for cp in diag_result.criticality_probabilities
            }
        
        # Fetch/build overlap (Part 28)
        if diag_result.fetch_build_overlap:
            signals['fetch_build_overlap'] = {
                'overlap_us': diag_result.fetch_build_overlap.overlap_us,
                'fetch_prefix_us': diag_result.fetch_build_overlap.fetch_only_prefix_us,
                'build_suffix_us': diag_result.fetch_build_overlap.build_only_suffix_us,
                'fraction': diag_result.fetch_build_overlap.overlap_fraction,
            }
        
        # Leaf analysis (Part 24)
        if diag_result.leaf_analysis:
            signals['leaf_analysis'] = {
                'leaves': [
                    la.element_uid for la in diag_result.leaf_analysis if la.is_leaf
                ],
                'deferrable_count': len(diag_result.deferrable_leaves),
                # P4-12 Direction 2 / P4-15 Direction 2 (linked - see
                # docs/tasks/P4-12-element-kind-based-heuristics.md's
                # "Related tasks"): per-leaf element_kind, additive, never
                # changes is_leaf/is_potentially_deferrable above (which
                # stay real, directly-observed graph facts) - a `junction`/
                # `stack` leaf's own recorded duration (if any) isn't real
                # compute work, flagged here so a reader can weigh it
                # accordingly rather than bga silently doing so for them.
                'leaves_detail': {
                    la.element_uid: {
                        'element_kind': kind_by_uid.get(la.element_uid, 'unknown'),
                        'is_structural_kind': kind_by_uid.get(la.element_uid) in STRUCTURAL_ELEMENT_KINDS,
                        'is_potentially_deferrable': la.is_potentially_deferrable,
                    }
                    for la in diag_result.leaf_analysis if la.is_leaf
                },
            }
        
        return signals
    
    def _compute_structural_analysis(self) -> dict:
        """
        Compute structural analysis (M6, Parts 31-39).
        
        Returns:
            Dict containing structural metrics including:
            - metrics (graph topology, critical path structure, parallelism)
            - bottleneck (choke points, resource contention)
            - parallelism (level-by-level profile)
            - sensitivity (improvement opportunities)
            - deferrability (leaf deferral analysis)
        """
        if not self.graph or len(self.normalized_tasks) == 0:
            return {}
        
        # Create task dictionary keyed by element UID (extract from task_key)
        tasks_dict = {t.task_key.element_uid: t for t in self.normalized_tasks}
        
        # Initialize structural analyzer
        from bga.structural.analyzer import build_edg
        edg = build_edg(self.graph)
        structural_analyzer = StructuralAnalyzer(edg, tasks_dict)

        # Run full structural analysis
        result = structural_analyzer.run_full_analysis(historical_runs=None)

        # Stack-consolidation advisory (P4-15 Direction 1, non-spec
        # additive signal) - purely structural, no timing data used or
        # changed. See docs/tasks/P4-15-stack-consolidation-heuristic.md.
        from bga.structural.consolidation import find_consolidation_candidates
        consolidation_candidates = find_consolidation_candidates(self.graph)

        # Batch-opportunity map-reduce simulation (UX-20, non-spec
        # additive signal): partitions sensitivity's own top candidates
        # into independently-fixable groups (no ancestor/descendant
        # relationship) and simulates the *combined* effect of fixing
        # each group at once - distinct from sensitivity's own
        # per-element proxy scores, which never simulate a combined
        # effect. See bga/structural/batching.py's own module docstring.
        # UX-34: a `stack` or `import` element has no build commands, so
        # ranking it in a list titled "what to fix first" is not an
        # action a reader can take - and on real projects those two
        # kinds took the top two slots on every run tested, at
        # sensitivity 1.00, because a structural element sitting on the
        # critical path genuinely does have sensitivity 1.00 by the
        # metric's own definition. Key Findings already tags them
        # (`STRUCTURAL_ELEMENT_KINDS`, P4-12; the same tagging `UX-25`
        # applies to coverage violations); this applies it here, in the
        # one list explicitly about what to go and edit.
        #
        # Filtered, not dropped: the omitted entries move to their own
        # key rather than vanishing (`UX-26`'s house pattern), and
        # because `compute_sensitivity` returns ten candidates while
        # only five are published, filtering surfaces the next *real*
        # candidate instead of shortening the list.
        kind_by_uid = self._element_kind_lookup()
        actionable_opportunities = []
        omitted_structural_opportunities = []
        for entry in result.sensitivity.top_opportunities:
            uid = entry[0]
            if kind_by_uid.get(uid) in STRUCTURAL_ELEMENT_KINDS:
                omitted_structural_opportunities.append(
                    {'element': uid, 'element_kind': kind_by_uid.get(uid, 'unknown')}
                )
            elif len(actionable_opportunities) < 5:
                actionable_opportunities.append(entry)

        batch_opportunities = {'groups': [], 'omitted_zero_savings_groups': [], 'serialized_pairs': []}
        if self.replay_scheduler is not None:
            from bga.structural.batching import compute_batch_opportunities, serialize_batch_opportunities
            # Same UX-34 reasoning applies transitively to batching and
            # to its `serialized_pairs` byproduct, both of which are
            # derived purely from this candidate list: "fixing" a
            # structural element means eliminating a zero-duration task,
            # which by construction can never change the replayed
            # makespan.
            candidates = [key for key, _, _ in actionable_opportunities]
            element_to_task_key = {
                t.task_key.element_uid: str(t.task_key) for t in self.normalized_tasks
            }
            batch_result = compute_batch_opportunities(
                candidates=candidates, graph=self.graph,
                replay_scheduler=self.replay_scheduler,
                element_to_task_key=element_to_task_key,
            )
            batch_opportunities = serialize_batch_opportunities(batch_result)

        # Large serialization point detection (UX-22, non-spec additive
        # signal): elements combining a real per-element `max_jobs`
        # override near the full governing core count with a genuinely
        # long measured duration, where the graph shape and `builders`
        # value actually allow more than one such element to dispatch
        # concurrently - a real oversubscription risk
        # _check_process_oversubscription's own single-aggregate-demand
        # check can't see. See bga/structural/serialization_points.py's
        # own module docstring.
        serialization_point_risks = []
        if self.run_context:
            from bga.structural.serialization_points import detect_large_serialization_points
            builders = self.run_context.resource_capacities.get('PROCESS')
            cpu_budget = self.run_context.cpu_budget
            host_cpu_count = self.run_context.host_cpu_count
            governing_cores = cpu_budget if cpu_budget is not None else host_cpu_count
            serialization_analysis = detect_large_serialization_points(
                elements=self.graph.elements, tasks=tasks_dict, graph=self.graph,
                builders=builders, governing_cores=governing_cores,
            )
            serialization_point_risks = [
                {
                    'elements': risk.elements,
                    'element_max_jobs': risk.element_max_jobs,
                    'element_duration_us': risk.element_duration_us,
                    'builders': risk.builders,
                    'governing_cores': risk.governing_cores,
                    # UX-31
                    'notparallel': risk.notparallel,
                    'typical_max_jobs': risk.typical_max_jobs,
                    'downstream_count': risk.downstream_count,
                    'hint': risk.hint,
                }
                for risk in serialization_analysis.risks
            ]

        # Convert to serializable dict format
        return {
            'metrics': {
                'num_elements': result.metrics.num_elements,
                'num_edges': result.metrics.num_edges,
                'max_depth': result.metrics.max_depth,
                'avg_fanout': result.metrics.avg_fanout,
                'avg_fanin': result.metrics.avg_fanin,
                'critical_path_length': result.metrics.critical_path_length,
                'critical_path_ratio': result.metrics.critical_path_ratio,
                'max_parallelism': result.metrics.max_parallelism,
                'avg_parallelism': result.metrics.avg_parallelism,
                'cyclomatic_complexity': result.metrics.cyclomatic_complexity,
                'serialization_ratio': result.metrics.serialization_ratio,
            },
            'bottleneck': {
                'choke_points': result.bottleneck.choke_points,
                'choke_point_impact': result.bottleneck.choke_point_impact,
                'resource_contention': result.bottleneck.resource_contention,
                'longest_serial_chain': result.bottleneck.longest_serial_chain,
                'serial_chain_length': result.bottleneck.serial_chain_length,
                'high_fanin_elements': result.bottleneck.high_fanin_elements[:5],
                'high_fanout_elements': result.bottleneck.high_fanout_elements[:5],
            },
            'parallelism': {
                'levels': result.parallelism.levels,
                'width_at_level': result.parallelism.width_at_level,
                'max_width': result.parallelism.max_width,
                'min_width': result.parallelism.min_width,
                'mean_width': result.parallelism.mean_width,
                'parallelism_efficiency': result.parallelism.parallelism_efficiency,
            },
            'sensitivity': {
                # UX-34: structural-kind elements filtered out (see
                # above) and listed separately rather than silently
                # dropped.
                'top_opportunities': actionable_opportunities,
                'omitted_structural_opportunities': omitted_structural_opportunities,
                'total_improvable_time_us': result.sensitivity.total_improvable_time_us,
                'best_case_speedup': result.sensitivity.best_case_speedup,
                'critical_path_us': result.sensitivity.critical_path_us,
            },
            'batch_opportunities': batch_opportunities,
            'serialization_point_risks': serialization_point_risks,
            'deferrability': {
                'deferrable_leaves': result.deferrability.deferrable_leaves,
                'non_deferrable_leaves': result.deferrability.non_deferrable_leaves,
                'recommended_deferrals': result.deferrability.recommended_deferrals,
                'total_deferrable_work_us': result.deferrability.total_deferrable_work_us,
            },
            'summary': result.summary,
            # P4-15 Direction 1 (non-spec, additive, purely structural -
            # no timing data used) - see
            # docs/tasks/P4-15-stack-consolidation-heuristic.md. For a
            # real, measured comparison of a flagged candidate's actual
            # checkout cost, run the separate tools/bst_checkout_cost.py.
            'consolidation_candidates': consolidation_candidates,
        }
    
    def get_summary(self) -> str:
        """
        Generate a text summary of the analysis.
        
        Returns:
            Formatted text summary
        """
        if self.analysis_result is None:
            self.analyze()
        
        result = self.analysis_result
        
        lines = [
            "=" * 60,
            "BGA BUILD EFFICIENCY REPORT",
            "=" * 60,
            "",
            "RUN SUMMARY",
            f"  Task horizon: {result.occupancy.get('horizon_us', 0) / 1_000_000:.2f}s",
            f"  Recognized tasks: {len(self.normalized_tasks)}",
            f"  Average concurrency: {result.occupancy.get('average_concurrency', 0):.2f}",
            f"  Peak concurrency: {result.occupancy.get('peak_concurrency', 0)}",
            "",
            "STRUCTURAL FLOORS",
            f"  T∞ observed: {result.floors.get('t_infinity_observed', 0) / 1_000_000:.2f}s",
            f"  Lower bound (LB): {result.floors.get('lb', 0) / 1_000_000:.2f}s",
            f"  Certified headroom: {result.floors.get('certified_headroom', 0) / 1_000_000:.2f}s",
            "",
            "CRITICAL PATH",
        ]
        
        if result.signals and 'critical_path' in result.signals:
            critical_path = result.signals['critical_path']
            lines.append(f"  Length: {len(critical_path)} elements")
            if critical_path:
                lines.append(f"  Elements: {' -> '.join(critical_path[:5])}")
                if len(critical_path) > 5:
                    lines.append(f"          ... ({len(critical_path) - 5} more)")
        
        lines.extend([
            "",
            "TRACE QUALITY",
            f"  Ordering violations: {result.confidence.get('ordering_violations', 0)}",
            f"  Confidence: {result.confidence.get('primary', 0):.0%}",
            "",
            "=" * 60,
        ])
        
        return "\n".join(lines)


def analyze_run(run_dir: Path) -> AnalysisResult:
    """
    Convenience function to analyze a run directory.
    
    Args:
        run_dir: Path to run directory
        
    Returns:
        AnalysisResult with all computed metrics
    """
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    return analyzer.analyze()
