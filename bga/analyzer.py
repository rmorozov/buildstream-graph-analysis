"""
Main analyzer module.

Orchestrates the complete analysis pipeline as specified in the v9 specification.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Set
from collections import defaultdict

from .ingest.models import AnalysisResult, Graph, RunContext, Trace, PhaseSpan, TaskKind
from .ingest.loader import load_all
from .normalize.timestamps import normalize_trace
from .occupancy.sweep import compute_occupancy_stats, compute_task_horizon
from .graph.edg import analyze_graph, compute_critical_path
from .attribution.blame_chain import BlameChainAnalyzer, AttributionSegment
from .replay.scheduler import ReplayScheduler, compute_replay_makespan
from .utilisation import UtilizationAnalyzer, CPUAccounting, analyze_utilization
from .diagnostics import DiagnosticsAnalyzer, analyze_diagnostics, DiagnosticsResult
from .structural import StructuralAnalyzer, StructuralAnalysisResult

logger = logging.getLogger(__name__)


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
                measured attribution (I12) - see _compute_cold_floor.
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
        
        # Build active_tasks_at_time and concurrent_jobs_at_time for classification
        active_tasks_at_time: Dict[int, Set[str]] = defaultdict(set)
        concurrent_jobs_at_time: Dict[int, int] = defaultdict(int)
        
        for task in self.normalized_tasks:
            # Mark task as active during its execution [start_us, finish_us)
            active_tasks_at_time[task.start_us].add(str(task.task_key))
            # Track concurrent jobs at start time
            concurrent_jobs_at_time[task.start_us] += 1
        
        # Resource capacity from run context
        resource_capacity = {}
        if self.run_context:
            if hasattr(self.run_context, 'builders') and self.run_context.builders:
                from .ingest.models import Resource
                resource_capacity[Resource.PROCESS] = self.run_context.builders
        
        max_jobs = self.run_context.max_jobs if self.run_context else None
        
        self.blame_chain_analyzer = BlameChainAnalyzer(
            self.normalized_tasks,
            self.run_context,
            phase_spans,
            active_tasks_at_time=active_tasks_at_time,
            resource_capacity=resource_capacity,
            max_jobs=max_jobs,
            concurrent_jobs_at_time=concurrent_jobs_at_time,
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
            max_jobs = self.run_context.max_jobs
            # builders would come from run_context if available
            
            self.utilization_analyzer = UtilizationAnalyzer(
                cpu_accounting=cpu_accounting,
                wall_clock_us=wall_clock_us,
                max_jobs=max_jobs,
            )
    
    def _compute_floors(self) -> dict:
        """
        Compute certified and advisory floors (Part 14-17).
        
        Returns:
            Dict containing floor metrics including:
            - t_infinity_observed: Critical path length with observed durations
            - t_infinity_cold: Critical path with cold durations (advisory)
            - lb: Lower bound = max(T∞, resource bounds, serialization bounds)
            - certified_headroom: H - LB
            - t_c: Replay makespan (Part 18)
            - model_slack: T_C - LB
        """
        if not self.normalized_tasks:
            return {
                't_infinity_observed': None,
                't_infinity_cold': None,
                'lb': None,
                'certified_headroom': None,
                't_c': None,
                'model_slack': None,
            }
        
        # Get task horizon
        _, _, horizon_us = compute_task_horizon(self.normalized_tasks)
        
        # Get graph analysis
        graph_analysis = analyze_graph(self.graph, self.normalized_tasks)
        t_infinity_observed = graph_analysis['critical_path_length']
        
        # Compute capacity lower bound (Part 16)
        # LB = max(T∞,observed, max_p(W_p / C_p), exclusive-serialization bounds)

        # Start with T∞ as baseline
        lb = t_infinity_observed

        # Add resource-area bounds if we have capacity info
        if self.run_context and hasattr(self.run_context, 'resource_capacities'):
            capacities = self.run_context.resource_capacities or {}
        else:
            capacities = {}

        process_capacity = capacities.get(
            'PROCESS',
            self.run_context.max_jobs if self.run_context and self.run_context.max_jobs else 4,
        )
        default_capacity_by_resource = {
            'PROCESS': process_capacity,
            'DOWNLOAD': capacities.get('DOWNLOAD', 2),
            'UPLOAD': capacities.get('UPLOAD', 2),
        }
        exclusive_resources = set(
            self.run_context.exclusive_resources if self.run_context else []
        )

        # W_p: observed work per resource, over every resource type actually
        # used by any task (PROCESS/DOWNLOAD/UPLOAD/CACHE/OTHER - Part 31.2),
        # not just PROCESS. A task using more than one resource contributes
        # its full duration to each - each resource's own bound treats it as
        # occupying that resource for the whole span, matching how C_p is a
        # per-resource capacity independent of the others.
        resource_work_us: Dict[str, int] = defaultdict(int)
        for task in self.normalized_tasks:
            task_resources = task.resources or ([task.primary_resource] if task.primary_resource else [])
            for res in task_resources:
                resource_work_us[res.value] += task.dur_us

        for resource_name, work_us in resource_work_us.items():
            if resource_name in exclusive_resources:
                # Exclusive resources (Part 31.3) cannot overlap at all,
                # regardless of declared capacity - a hard serialization
                # floor equal to the full observed work for that resource.
                lb = max(lb, work_us)
                continue
            capacity = capacities.get(
                resource_name, default_capacity_by_resource.get(resource_name, 1)
            )
            if capacity > 0:
                lb = max(lb, work_us // capacity)

        certified_headroom = max(0, horizon_us - lb)
        
        # Compute replay makespan T_C (Part 18)
        t_c = None
        model_slack = None
        
        if self.replay_scheduler:
            # Use default capacities for replay
            default_caps = {
                'PROCESS': process_capacity,
                'DOWNLOAD': capacities.get('DOWNLOAD', getattr(self.run_context, 'fetchers', 2) if self.run_context else 2),
                'UPLOAD': capacities.get('UPLOAD', getattr(self.run_context, 'pushers', 2) if self.run_context else 2),
            }
            
            replay_result = self.replay_scheduler.replay(default_caps)
            t_c = replay_result.makespan_us
            
            # Model slack = T_C - LB (Part 18)
            model_slack = max(0, t_c - lb)
        
        # Advisory cold structural floor (Part 15) - fully isolated from
        # everything above (I12): computed independently, from observed
        # durations already finalized (lb/certified_headroom/t_c/model_slack
        # never read cold_floor, and cold_floor never reads them back).
        cold_floor = self._compute_cold_floor()

        return {
            't_infinity_observed': t_infinity_observed,
            't_infinity_cold': cold_floor['t_infinity_cold'],
            'cold_partial': cold_floor['cold_partial'],
            'cold_confidence': cold_floor['cold_confidence'],
            'lb': lb,
            'certified_headroom': certified_headroom,
            't_c': t_c,
            'model_slack': model_slack,
        }

    def _compute_cold_floor(self) -> dict:
        """
        Compute the advisory cold structural floor T∞,cold (Part 15).

        Duration source hierarchy per task (Part 15.2), in priority order:
        1. same cache_key historical execution (median if multiple)
        2. same element_uid+task_kind+phase historical execution (median)
        3. cohort (task_kind+phase) median across all historical runs
        4. declared metadata estimate - no ingest schema field currently
           carries one, so this level is checked in principle but always
           falls through in practice given today's input data.
        5. unavailable

        Publication gate (Part 15.3): if the resulting cold critical path
        touches any element whose duration came back unavailable,
        T∞,cold reports as unavailable unless allow_partial_cold is set,
        in which case it publishes with partial=true/confidence=low.

        Fully independent of LB/certified_headroom/primary confidence/
        measured attribution (I12) - reads only self.graph/
        self.normalized_tasks/self.historical_runs, and its output is
        merged into floors under cold-prefixed keys only.
        """
        if not self.cold or not self.historical_runs or not self.graph:
            return {'t_infinity_cold': None, 'cold_partial': False, 'cold_confidence': None}

        def _median(values: List[int]) -> int:
            ordered = sorted(values)
            n = len(ordered)
            mid = n // 2
            if n % 2 == 1:
                return ordered[mid]
            return (ordered[mid - 1] + ordered[mid]) // 2

        # Candidate duration pools from historical runs, at decreasing
        # specificity (Part 15.2). Raw observed span durations are used
        # directly (not run through full normalization) - these are
        # advisory estimate sources, not measured values themselves.
        by_cache_key: Dict[Tuple[str, str, str], List[int]] = defaultdict(list)
        by_element_kind_phase: Dict[Tuple[str, str, str], List[int]] = defaultdict(list)
        by_cohort: Dict[Tuple[str, str], List[int]] = defaultdict(list)

        for hist_context, hist_graph, hist_trace in self.historical_runs:
            cache_key_by_element = {elem.uid: elem.cache_key for elem in hist_graph.elements}
            for span in hist_trace.spans:
                kind = span.task_key.task_kind.value
                phase = span.task_key.phase
                elem_uid = span.task_key.element_uid
                by_element_kind_phase[(elem_uid, kind, phase)].append(span.dur_us)
                by_cohort[(kind, phase)].append(span.dur_us)
                cache_key = cache_key_by_element.get(elem_uid)
                if cache_key:
                    by_cache_key[(cache_key, kind, phase)].append(span.dur_us)

        element_cache_key = {elem.uid: elem.cache_key for elem in self.graph.elements}
        tasks_by_element: Dict[str, List] = defaultdict(list)
        for task in self.normalized_tasks:
            tasks_by_element[task.task_key.element_uid].append(task)

        cold_duration_by_element: Dict[str, int] = {}
        unavailable_elements: Set[str] = set()

        for elem in self.graph.elements:
            elem_uid = elem.uid
            tasks = tasks_by_element.get(elem_uid, [])
            if not tasks:
                unavailable_elements.add(elem_uid)
                continue

            # Element duration = max across its own task kinds, mirroring
            # analyze_graph's own observed task_durations aggregation, so
            # cold and observed critical paths are computed the same way.
            resolved_us = 0
            any_unavailable = False
            cache_key = element_cache_key.get(elem_uid)
            for task in tasks:
                kind = task.task_key.task_kind.value
                phase = task.task_key.phase
                duration = None
                if cache_key and by_cache_key.get((cache_key, kind, phase)):
                    duration = _median(by_cache_key[(cache_key, kind, phase)])
                elif by_element_kind_phase.get((elem_uid, kind, phase)):
                    duration = _median(by_element_kind_phase[(elem_uid, kind, phase)])
                elif by_cohort.get((kind, phase)):
                    duration = _median(by_cohort[(kind, phase)])
                # Priority 4 (declared metadata estimate): never populated
                # by any current ingest schema field - falls through.

                if duration is None:
                    any_unavailable = True
                else:
                    resolved_us = max(resolved_us, duration)

            if any_unavailable:
                unavailable_elements.add(elem_uid)
            cold_duration_by_element[elem_uid] = resolved_us

        # Weighted longest path using resolved cold durations - reuse the
        # same algorithm as T∞,observed (Part 15.1).
        cold_length, cold_path = compute_critical_path(self.graph, cold_duration_by_element)

        path_has_unavailable = any(uid in unavailable_elements for uid in cold_path)

        if path_has_unavailable and not self.allow_partial_cold:
            logger.info(
                "Cold floor unavailable: %d element(s) on cold critical path lack a "
                "resolvable duration (pass allow_partial_cold to publish anyway)",
                sum(1 for uid in cold_path if uid in unavailable_elements),
            )
            return {'t_infinity_cold': None, 'cold_partial': False, 'cold_confidence': None}

        if path_has_unavailable:
            logger.info("Cold floor published as partial (confidence=low)")

        return {
            't_infinity_cold': cold_length,
            'cold_partial': bool(path_has_unavailable),
            'cold_confidence': 'low' if path_has_unavailable else 'high',
        }

    def _compute_attribution(self) -> dict:
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
        # just its BUILD task - matching bga/normalize/timestamps.py's
        # compute_ready_times, which already gates every task kind of a
        # dependent element on its predecessors' finish (not just BUILD).
        # Without this, a TRACK/FETCH task's real cross-element wait had no
        # explicit_predecessors entry, so the blame-chain walk had no way to
        # continue into the actual responsible predecessor once it reached
        # such a task - it just stopped, silently dropping the segment that
        # should have explained the wait.
        build_task_by_element: Dict[str, str] = {}
        tasks_by_element: Dict[str, List[str]] = defaultdict(list)
        for task in self.normalized_tasks:
            key_str = str(task.task_key)
            tasks_by_element[task.task_key.element_uid].append(key_str)
            if task.task_key.task_kind == TaskKind.BUILD:
                build_task_by_element[task.task_key.element_uid] = key_str

        explicit_predecessors: Dict[str, List[str]] = {}
        for dep in self.graph.dependencies:
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

        # Build result with all categories
        result = {
            'execution_on_chain_us': reconciled.get('EXECUTION_ON_CHAIN', 0),
            'dependency_wait_us': reconciled.get('DEPENDENCY_WAIT', 0),
            'resource_wait_us': reconciled.get('RESOURCE_WAIT', 0),
            'scheduler_wait_us': reconciled.get('SCHEDULER_WAIT', 0),
            'idle_us': reconciled.get('IDLE', 0),
            'retry_wait_us': reconciled.get('RETRY_WAIT', 0),
            'untracked_head_us': 0,  # Would need wall_start comparison
            'untracked_tail_us': 0,  # Would need wall_end comparison
        }

        # I4 reconciliation check (Part 33/34): Sigma attribution must equal
        # the task horizon H exactly. P1-03/P1-04/P1-19/P1-20 closed every
        # known undercounting gap, so this should never fire today - but per
        # the spec's "no silent correction" philosophy (ordering violations
        # are reported, not hidden; resource ambiguity is UNKNOWN, not
        # invented), any future residual must be reported, not silently
        # absorbed. Never pad or truncate to force the sum to match.
        _, _, horizon_us = compute_task_horizon(self.normalized_tasks)
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
        
        # Set run_id and total_duration from context/trace
        if self.run_context:
            result.run_id = getattr(self.run_context, 'run_id', '') or getattr(self.run_context, 'uuid', '')
        
        # Compute horizon for total duration
        occupancy_stats = compute_occupancy_stats(self.normalized_tasks)
        result.total_duration_us = occupancy_stats.get('horizon_us', 0)
        
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
        
        # Graph analysis (M1)
        if self.graph:
            graph_analysis = analyze_graph(self.graph, self.normalized_tasks)
            result.signals = {
                'critical_path': graph_analysis['critical_path'],
                'critical_path_length': graph_analysis['critical_path_length'],
                'downstream_count': graph_analysis['downstream_count'],
                'slack': graph_analysis['slack'],
                'unweighted_depth': graph_analysis['unweighted_depth'],
            }
        
        # Floors (M3)
        result.floors = self._compute_floors()
        
        # Attribution (M2)
        result.attribution = self._compute_attribution()
        
        # CPU Utilization (M4)
        result.utilisation = self._compute_utilization(occupancy_stats)
        
        # Advanced Diagnostics (M5)
        result.signals.update(self._compute_diagnostics(occupancy_stats, graph_analysis))
        
        # Structural Analysis (M6)
        result.structural = self._compute_structural_analysis()
        
        # Violations
        result.violations = self.violations
        
        # Confidence (Part 33)
        result.confidence = self._compute_confidence(graph_analysis, result.attribution, result.floors)
        
        self.analysis_result = result
        return result
    
    def _compute_confidence(self, graph_analysis: Optional[dict], attribution: dict, floors: dict) -> dict:
        """
        Compute confidence metrics (Part 33).

        Hard gates (33.1): ordering_violations == 0, critical_path_coverage
        == 1.0, dominator_coverage == 1.0, blame_chain_coverage == 1.0.
        Soft gates (33.2, defaults): task_coverage >= 0.95, duration_coverage
        >= 0.98 - these reduce confidence (via coverage_score's min, below)
        rather than hard-failing.

        confidence = min(provenance_score, coverage_score, model_score,
        attribution_score) (33.4). The spec names these four sub-scores and
        gives attribution_score's exact inputs, but does not spell out
        provenance_score/coverage_score/model_score's formulas - each is
        grounded in the one other place the spec actually defines the
        relevant concept (see inline comments), not guessed from nothing.

        cold_confidence stays fully separate (already lives in floors,
        from _compute_cold_floor - never read or written here).
        """
        graph_analysis = graph_analysis or {}
        ordering_violations = sum(
            1 for v in self.violations if v.get('type') == 'ordering_violation'
        )
        reconciliation_violations = [
            v for v in self.violations if v.get('type') == 'attribution_reconciliation'
        ]

        total_tasks = len(self.normalized_tasks) if self.normalized_tasks else 0
        _, _, horizon_us = compute_task_horizon(self.normalized_tasks) if self.normalized_tasks else (0, 0, 0)

        # --- Coverage metrics ---
        critical_path = graph_analysis.get('critical_path', [])
        elements_with_tasks = {t.task_key.element_uid for t in self.normalized_tasks}
        if critical_path:
            resolved = sum(1 for uid in critical_path if uid in elements_with_tasks)
            critical_path_coverage = resolved / len(critical_path)
        else:
            critical_path_coverage = 1.0

        dominators = graph_analysis.get('dominators', {})
        total_elements = len(self.graph.elements) if self.graph else 0
        dominator_coverage = (len(dominators) / total_elements) if total_elements > 0 else 1.0

        attribution_sum_us = sum(attribution.get(k, 0) for k in (
            'execution_on_chain_us', 'dependency_wait_us', 'resource_wait_us',
            'scheduler_wait_us', 'idle_us', 'retry_wait_us',
        ))
        blame_chain_coverage = (attribution_sum_us / horizon_us) if horizon_us > 0 else 1.0

        declared_task_count = len(self.trace.spans) if self.trace else 0
        task_coverage = (total_tasks / declared_task_count) if declared_task_count > 0 else 1.0

        declared_duration_us = sum(s.dur_us for s in self.trace.spans) if self.trace else 0
        accounted_duration_us = sum(t.dur_us for t in self.normalized_tasks)
        duration_coverage = (
            accounted_duration_us / declared_duration_us if declared_duration_us > 0 else 1.0
        )

        # --- Hard gates (33.1) ---
        hard_gates = {
            'ordering_violations_zero': ordering_violations == 0,
            'critical_path_coverage_full': critical_path_coverage >= 1.0,
            'dominator_coverage_full': dominator_coverage >= 1.0,
            'blame_chain_coverage_full': blame_chain_coverage >= 1.0,
        }
        # Only critical_path_coverage/dominator_coverage failures need a new
        # violation entry - ordering violations are already individually
        # reported by normalize_trace, and blame_chain_coverage < 1.0 is
        # exactly the condition P1-05's attribution_reconciliation violation
        # already reports. Adding another entry for either would just
        # duplicate an existing, more specific one.
        if not hard_gates['critical_path_coverage_full']:
            self.violations.append({
                'type': 'hard_gate_failed', 'gate': 'critical_path_coverage',
                'value': critical_path_coverage,
            })
        if not hard_gates['dominator_coverage_full']:
            self.violations.append({
                'type': 'hard_gate_failed', 'gate': 'dominator_coverage',
                'value': dominator_coverage,
            })
        for gate_name, passed in hard_gates.items():
            if not passed:
                logger.warning("Hard gate failed: %s", gate_name)
        if all(hard_gates.values()):
            logger.info("All hard gates passed (%d tasks checked)", total_tasks)

        # --- Soft gates (33.2) - logged, not hard-failed; the actual
        # confidence reduction comes from coverage_score's min() below.
        TASK_COVERAGE_THRESHOLD = 0.95
        DURATION_COVERAGE_THRESHOLD = 0.98
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
        if self.run_context and self.run_context.wall_start_us is not None and self.run_context.wall_end_us is not None:
            provenance_score = 1.0
        else:
            provenance_score = 0.5

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
            for seg in getattr(self, '_attribution_segments', [])
            if seg.category.value == 'RESOURCE_WAIT'
            and seg.metadata.get('holder_info', {}).get('ambiguous')
        )
        violation_us = sum(
            abs(v.get('gap_us', 0)) for v in self.violations if v.get('type') == 'ordering_violation'
        )
        violation_us += sum(abs(v.get('residual_us', 0)) for v in reconciliation_violations)

        penalized_us = untracked_us + ambiguous_wait_us + violation_us
        attribution_score = max(0.0, 1.0 - (penalized_us / horizon_us)) if horizon_us > 0 else 1.0

        confidence = min(provenance_score, coverage_score, model_score, attribution_score)

        return {
            'primary': confidence,
            'provenance_score': provenance_score,
            'coverage_score': coverage_score,
            'model_score': model_score,
            'attribution_score': attribution_score,
            'critical_path_coverage': critical_path_coverage,
            'dominator_coverage': dominator_coverage,
            'blame_chain_coverage': blame_chain_coverage,
            'task_coverage': task_coverage,
            'duration_coverage': duration_coverage,
            'hard_gates': hard_gates,
            'ordering_violations': ordering_violations,
            'task_count': total_tasks,
        }
    
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
        
        # Build task intervals with CPU usage
        # For now, assume each task uses 100% of one CPU during execution
        # In a full implementation, this would come from actual CPU accounting
        task_intervals = []
        for task in self.normalized_tasks:
            interval = {
                'task_key': str(task.task_key),
                'start_us': task.start_us,
                'end_us': task.finish_us,
                'cpu_usage_us': task.dur_us,  # Assume 100% CPU usage
                'concurrent_tasks': [str(task.task_key)],
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
        
        # Run utilization analysis
        util_result = self.utilization_analyzer.analyze(
            task_intervals=task_intervals,
            occupancy_segments=occupancy_segments,
            retry_tasks=set(),  # Would need retry detection
            rebuild_tasks=set(),  # Would need rebuild detection
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
            blame_chain = [str(t) for t in self._blame_chain]
        
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
        from bga.structural.analyzer import build_edg, ElementDependencyGraph
        edg = build_edg(self.graph)
        structural_analyzer = StructuralAnalyzer(edg, tasks_dict)
        
        # Run full structural analysis
        result = structural_analyzer.run_full_analysis(historical_runs=None)
        
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
                'top_opportunities': result.sensitivity.top_opportunities[:5],
                'total_improvable_time_us': result.sensitivity.total_improvable_time_us,
                'best_case_speedup': result.sensitivity.best_case_speedup,
            },
            'deferrability': {
                'deferrable_leaves': result.deferrability.deferrable_leaves,
                'non_deferrable_leaves': result.deferrability.non_deferrable_leaves,
                'recommended_deferrals': result.deferrability.recommended_deferrals,
                'total_deferrable_work_us': result.deferrability.total_deferrable_work_us,
            },
            'summary': result.summary,
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
