"""
Main analyzer module.

Orchestrates the complete analysis pipeline as specified in the v9 specification.
"""

from pathlib import Path
from typing import Optional, Tuple, Dict, List, Set
from collections import defaultdict

from .ingest.models import AnalysisResult, Graph, RunContext, Trace, PhaseSpan
from .ingest.loader import load_all
from .normalize.timestamps import normalize_trace
from .occupancy.sweep import compute_occupancy_stats, compute_task_horizon
from .graph.edg import analyze_graph
from .attribution.blame_chain import BlameChainAnalyzer, AttributionSegment
from .replay.scheduler import ReplayScheduler, compute_replay_makespan
from .utilisation import UtilizationAnalyzer, CPUAccounting, analyze_utilization
from .diagnostics import DiagnosticsAnalyzer, analyze_diagnostics, DiagnosticsResult
from .structural import StructuralAnalyzer, StructuralAnalysisResult


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
        """
        self.run_dir = run_dir
        self.capacity_override = capacity
        self.run_replay = run_replay
        self.replay_heuristic = replay_heuristic
        self.run_diagnostics = run_diagnostics
        self.verbose = verbose
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
        # LB = max(T∞,observed, max_p(W_p / C_p), serialization bounds)
        
        # Start with T∞ as baseline
        lb = t_infinity_observed
        
        # Add resource-area bounds if we have capacity info
        if self.run_context and hasattr(self.run_context, 'resource_capacities'):
            capacities = self.run_context.resource_capacities or {}
        else:
            capacities = {}
        
        # Compute work per resource type
        # Simplified: assume all tasks use PROCESS
        process_work = sum(t.dur_us for t in self.normalized_tasks)
        process_capacity = capacities.get('PROCESS', getattr(self.run_context, 'builders', 4) if self.run_context else 4)
        
        if process_capacity > 0:
            resource_lb = process_work // process_capacity
            lb = max(lb, resource_lb)
        
        # TODO: Add DOWNLOAD/UPLOAD work bounds
        # TODO: Add exclusive serialization bounds
        
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
        
        return {
            't_infinity_observed': t_infinity_observed,
            't_infinity_cold': None,  # Requires historical data (M6)
            'lb': lb,
            'certified_headroom': certified_headroom,
            't_c': t_c,
            'model_slack': model_slack,
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
        
        # Build explicit predecessor map from graph
        # In a full implementation, this would come from the graph structure
        explicit_predecessors: Dict[str, List[str]] = {}
        for dep in self.graph.dependencies:
            # Map element-level deps to task-level
            # Simplified: assume one task per element for now
            succ_key = None
            pred_key = None
            for task in self.normalized_tasks:
                if task.task_key.element_uid == dep.successor:
                    succ_key = str(task.task_key)
                if task.task_key.element_uid == dep.predecessor:
                    pred_key = str(task.task_key)
            
            if succ_key:
                if succ_key not in explicit_predecessors:
                    explicit_predecessors[succ_key] = []
                if pred_key:
                    explicit_predecessors[succ_key].append(pred_key)
        
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
        
        # Compute full attribution
        blame_chain, task_attributions, segments = self.blame_chain_analyzer.compute_full_attribution(
            explicit_predecessors,
            task_finish_times,
            task_depths,
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
        result.confidence = self._compute_confidence()
        
        self.analysis_result = result
        return result
    
    def _compute_confidence(self) -> dict:
        """
        Compute confidence metrics (Part 33).
        
        Returns:
            Dict containing confidence scores
        """
        # Count violations
        ordering_violations = sum(
            1 for v in self.violations if v.get('type') == 'ordering_violation'
        )
        
        # Basic coverage calculation
        total_tasks = len(self.normalized_tasks) if self.normalized_tasks else 0
        
        return {
            'primary': 1.0 if ordering_violations == 0 else 0.5,
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
        
        # Requested targets (would come from graph metadata)
        requested_targets = None
        
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
