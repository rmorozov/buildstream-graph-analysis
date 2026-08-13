"""
Advanced Diagnostics for bga.

Implements M5 milestone with high-value structural diagnostics:
- Wall-clock share (Part 20)
- Ready queue depth refinements (Part 21)
- Blast radius (Part 25)
- Churn × blast radius
- Criticality probability (Part 26)
- Fetch/build overlap (Part 28)
- Duration coefficient of variation (Part 29)
- Advanced leaf analysis (Part 24)
"""

import bisect
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
import random

from bga.ingest.models import TaskKind
from bga.graph.edg import build_element_graph, compute_in_out_degree

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WallClockShare:
    """
    Wall-clock share attribution for a task (Part 20).
    
    share(t) = ∫ execution(t) 1/n(τ) dτ
    where n(τ) = number of concurrently executing tasks at time τ
    """
    task_key: str
    execution_duration_us: int
    wall_clock_share_us: float  # Marginal share of active wall time
    concurrency_weighted: bool = True


@dataclass
class ReadyQueueMetrics:
    """
    Ready queue depth metrics over time (Part 21).
    
    Tracks tasks that are dependency-ready, resource-ready, but not executing.
    """
    average_depth: float
    peak_depth: int
    time_with_nonzero_queue_us: int
    total_horizon_us: int
    queue_depth_timeline: List[Tuple[int, int, int]] = field(default_factory=list)  # (start, end, depth)
    
    @property
    def nonzero_fraction(self) -> float:
        """Fraction of time with non-zero ready queue."""
        if self.total_horizon_us == 0:
            return 0.0
        return self.time_with_nonzero_queue_us / self.total_horizon_us


@dataclass
class BlastRadiusResult:
    """
    Blast radius analysis for an element/task (Part 25).
    
    reachable_downstream_count using reverse reachability.
    """
    element_uid: str
    downstream_count: int  # Number of downstream elements
    downstream_weighted_duration_us: int  # Sum of downstream task durations
    is_leaf: bool  # Whether this is a leaf element
    is_on_critical_path: bool  # Whether on observed critical path
    is_required_by_target: bool  # Whether reachable from requested targets
    
    @property
    def risk_score(self) -> int:
        """Simple risk score = downstream_count × is_on_critical_path."""
        return self.downstream_count if self.is_on_critical_path else 0


@dataclass
class CriticalityProbability:
    """
    Monte-Carlo criticality probability for an element (Part 26).
    
    P(element appears on longest path) under duration perturbations.
    """
    element_uid: str
    probability: float  # 0.0 to 1.0
    observed_critical: bool  # Whether on observed critical path
    observed_slack_us: int  # Observed slack in microseconds
    samples: int = 200  # Number of Monte-Carlo samples
    perturbation_pct: float = 0.1  # ±10% default perturbation


@dataclass
class FetchBuildOverlap:
    """
    Fetch/Build overlap analysis (Part 28).
    
    Measures temporal overlap between FETCH and BUILD phases.
    """
    fetch_start_us: int
    fetch_end_us: int
    build_start_us: int
    build_end_us: int
    overlap_us: int  # Actual overlap duration
    fetch_only_prefix_us: int  # Time with only fetch operations
    build_only_suffix_us: int  # Time with only build operations
    overlap_fraction: float = 0.0  # overlap / total_active_time
    
    def __post_init__(self):
        if self.__dict__.get('_computed', False):
            return
        
        total_active = max(self.build_end_us, self.fetch_end_us) - min(self.fetch_start_us, self.build_start_us)
        if total_active > 0:
            object.__setattr__(self, 'overlap_fraction', self.overlap_us / total_active)
        else:
            object.__setattr__(self, 'overlap_fraction', 0.0)


@dataclass
class DurationVariability:
    """
    Duration variability statistics (Part 29).
    
    Computed across historical runs for task classes.
    """
    task_class: str  # e.g., "BUILD", "FETCH"
    mean_us: float
    median_us: float
    p50_us: float
    p75_us: float
    p95_us: float
    coefficient_of_variation: float  # std_dev / mean
    sample_count: int
    high_variability_warning: bool = False
    
    def __post_init__(self):
        # High CV warning threshold
        if self.coefficient_of_variation > 0.3:  # 30% CV threshold
            object.__setattr__(self, 'high_variability_warning', True)


@dataclass
class LeafAnalysis:
    """
    Advanced leaf analysis result (Part 24).
    
    Identifies leaf elements that are potentially deferrable.
    """
    element_uid: str
    is_leaf: bool  # Terminal in element graph
    is_on_blame_chain: bool
    is_on_critical_path: bool
    is_reachable_from_target: bool
    is_potentially_deferrable: bool  # Leaf AND not reachable from target
    recommendation: Optional[str] = None  # Deferral recommendation if applicable
    
    def __post_init__(self):
        if self.is_leaf and not self.is_reachable_from_target:
            object.__setattr__(self, 'is_potentially_deferrable', True)
            if not self.__dict__.get('recommendation'):
                object.__setattr__(self, 'recommendation', "Consider deferring or decoupling from main build")
        elif self.__dict__.get('recommendation') is None:
            object.__setattr__(self, 'recommendation', "Required by target or not a leaf")


@dataclass
class DiagnosticsResult:
    """
    Complete advanced diagnostics result (M5).
    """
    # Wall-clock share
    wall_clock_shares: List[WallClockShare] = field(default_factory=list)
    total_active_wall_time_us: int = 0
    
    # Ready queue
    ready_queue: Optional[ReadyQueueMetrics] = None
    
    # Blast radius
    blast_radius: List[BlastRadiusResult] = field(default_factory=list)
    top_blast_radius_elements: List[BlastRadiusResult] = field(default_factory=list)
    
    # Criticality probability
    criticality_probabilities: List[CriticalityProbability] = field(default_factory=list)
    high_criticality_elements: List[CriticalityProbability] = field(default_factory=list)
    
    # Fetch/build overlap
    fetch_build_overlap: Optional[FetchBuildOverlap] = None
    
    # Duration variability (requires historical data)
    duration_variability: List[DurationVariability] = field(default_factory=list)
    
    # Leaf analysis
    leaf_analysis: List[LeafAnalysis] = field(default_factory=list)
    deferrable_leaves: List[LeafAnalysis] = field(default_factory=list)
    
    # Churn × blast radius (requires historical churn data)
    churn_blast_radius: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to analysis/v9 compatible dictionary."""
        return {
            "wall_clock_share": {
                "shares": [{"task_key": s.task_key, "share_us": s.wall_clock_share_us} 
                          for s in self.wall_clock_shares],
                "total_active_us": self.total_active_wall_time_us,
            },
            "ready_queue": {
                "average_depth": self.ready_queue.average_depth if self.ready_queue else None,
                "peak_depth": self.ready_queue.peak_depth if self.ready_queue else None,
                "nonzero_fraction": self.ready_queue.nonzero_fraction if self.ready_queue else None,
            } if self.ready_queue else None,
            "blast_radius": [
                {
                    "element_uid": br.element_uid,
                    "downstream_count": br.downstream_count,
                    "weighted_duration_us": br.downstream_weighted_duration_us,
                    "is_leaf": br.is_leaf,
                    "risk_score": br.risk_score,
                }
                for br in self.blast_radius
            ],
            "criticality_probability": {
                cp.element_uid: {
                    "probability": cp.probability,
                    "observed_critical": cp.observed_critical,
                    "slack_us": cp.observed_slack_us,
                }
                for cp in self.criticality_probabilities
            },
            "fetch_build_overlap": {
                "overlap_us": self.fetch_build_overlap.overlap_us,
                "fetch_prefix_us": self.fetch_build_overlap.fetch_only_prefix_us,
                "build_suffix_us": self.fetch_build_overlap.build_only_suffix_us,
                "fraction": self.fetch_build_overlap.overlap_fraction,
            } if self.fetch_build_overlap else None,
            "duration_variability": [
                {
                    "task_class": dv.task_class,
                    "mean_us": dv.mean_us,
                    "cv": dv.coefficient_of_variation,
                    "warning": dv.high_variability_warning,
                }
                for dv in self.duration_variability
            ],
            "leaf_analysis": {
                "leaves": [
                    {
                        "element_uid": la.element_uid,
                        "deferrable": la.is_potentially_deferrable,
                        "recommendation": la.recommendation,
                    }
                    for la in self.leaf_analysis if la.is_leaf
                ],
                "deferrable_count": len(self.deferrable_leaves),
            },
        }


class DiagnosticsAnalyzer:
    """
    Advanced diagnostics analyzer implementing M5.
    
    Provides high-value structural diagnostics based on established primitives.
    All diagnostics are deterministic (except Monte-Carlo which uses seeded RNG).
    """
    
    DEFAULT_MC_SAMPLES = 200
    DEFAULT_PERTURBATION_PCT = 0.1
    MC_RANDOM_SEED = 42  # Deterministic Monte-Carlo
    
    def __init__(
        self,
        normalized_tasks: List[object],
        graph_analysis: dict,
        blame_chain: Optional[List[str]] = None,
        critical_path: Optional[List[str]] = None,
        slack: Optional[Dict[str, int]] = None,
    ):
        """
        Initialize diagnostics analyzer.
        
        Args:
            normalized_tasks: List of normalized task objects
            graph_analysis: Graph analysis results from EDG analyzer
            blame_chain: Blame chain task keys (optional)
            critical_path: Critical path task keys (optional)
            slack: Task slack values (optional)
        """
        self.tasks = normalized_tasks
        self.graph_analysis = graph_analysis or {}
        self.blame_chain = set(blame_chain or [])
        self.critical_path = set(critical_path or [])
        self.slack = slack or {}
        
        # Extract graph data for structural analysis
        self.graph = graph_analysis.get('graph', {}) if graph_analysis else {}
        self.predecessors = graph_analysis.get('predecessors', {}) if graph_analysis else {}
        self.successors = graph_analysis.get('successors', {}) if graph_analysis else {}
        
        # Build task maps
        self.task_map: Dict[str, object] = {
            str(t.task_key): t for t in self.tasks
        }
        
        # Element-level maps
        self.element_tasks: Dict[str, List[str]] = defaultdict(list)
        for task in self.tasks:
            elem_uid = task.task_key.element_uid
            self.element_tasks[elem_uid].append(str(task.task_key))
        
        # Extract element durations from graph_analysis for perturbed critical path computation
        self._element_durations = graph_analysis.get('task_durations', {}) if graph_analysis else {}

        # Sorted once, O(N log N), for _estimate_ready_count's O(log N)
        # binary-search queries (P1-21) instead of an O(N) rescan of
        # self.tasks per occupancy segment (O(N*segments) overall, the
        # single largest hotspot found while profiling P1-16).
        self._sorted_ready_times = sorted(t.ready_us for t in self.tasks)
        self._sorted_start_times = sorted(t.start_us for t in self.tasks)
    
    def compute_wall_clock_shares(self) -> List[WallClockShare]:
        """
        Compute wall-clock share for each task (Part 20).
        
        share(t) = ∫ execution(t) 1/n(τ) dτ
        where n(τ) = concurrent task count at time τ
        
        Uses sweep-line algorithm over task intervals.
        """
        if not self.tasks:
            return []
        
        # Build events: (timestamp, +1 for start/-1 for end, task_key)
        events = []
        for task in self.tasks:
            task_key = str(task.task_key)
            events.append((task.start_us, 1, task_key))
            events.append((task.finish_us, -1, task_key))
        
        # Sort by timestamp, ends before starts at same time
        events.sort(key=lambda x: (x[0], x[1]))
        
        # Sweep to compute concurrent count at each point
        shares: Dict[str, float] = defaultdict(float)
        active_tasks: Set[str] = set()
        prev_time = events[0][0] if events else 0
        
        for timestamp, delta, task_key in events:
            # Process interval from prev_time to timestamp
            if timestamp > prev_time and active_tasks:
                concurrent_count = len(active_tasks)
                interval_duration = timestamp - prev_time
                share_per_task = interval_duration / concurrent_count
                
                for active_task in active_tasks:
                    shares[active_task] += share_per_task
            
            # Update active set
            if delta > 0:
                active_tasks.add(task_key)
            else:
                active_tasks.discard(task_key)
            
            prev_time = timestamp
        
        # Build result objects
        result = []
        for task in self.tasks:
            task_key = str(task.task_key)
            result.append(WallClockShare(
                task_key=task_key,
                execution_duration_us=task.dur_us,
                wall_clock_share_us=shares.get(task_key, 0.0),
            ))
        
        return result
    
    def compute_ready_queue_metrics(
        self,
        occupancy_segments: List[dict],
        resource_capacities: Optional[Dict[str, int]] = None,
    ) -> ReadyQueueMetrics:
        """
        Compute ready queue depth metrics (Part 21).
        
        Ready queue = tasks that are dependency-ready, resource-ready, but not executing.
        
        Args:
            occupancy_segments: Occupancy step function segments
            resource_capacities: Resource capacity limits
        """
        if not occupancy_segments:
            return ReadyQueueMetrics(
                average_depth=0.0,
                peak_depth=0,
                time_with_nonzero_queue_us=0,
                total_horizon_us=0,
            )
        
        resource_capacities = resource_capacities or {}
        
        # For each segment, estimate ready queue depth
        # Simplified: assume tasks become ready immediately after predecessors finish
        # Full implementation would track detailed task states
        
        timeline = []
        total_weighted_depth = 0
        total_duration = 0
        max_depth = 0
        nonzero_time = 0
        
        for seg in occupancy_segments:
            start_us = seg.get('start_us', 0)
            end_us = seg.get('end_us', 0)
            active_tasks = seg.get('active_tasks', set())
            duration = end_us - start_us
            
            if duration <= 0:
                continue
            
            # Estimate ready queue: tasks whose deps are done but not yet started
            # This is a simplified heuristic
            ready_count = self._estimate_ready_count(start_us, active_tasks)
            
            timeline.append((start_us, end_us, ready_count))
            total_weighted_depth += ready_count * duration
            total_duration += duration
            max_depth = max(max_depth, ready_count)
            
            if ready_count > 0:
                nonzero_time += duration
        
        avg_depth = total_weighted_depth / total_duration if total_duration > 0 else 0.0
        
        return ReadyQueueMetrics(
            average_depth=avg_depth,
            peak_depth=max_depth,
            time_with_nonzero_queue_us=nonzero_time,
            total_horizon_us=total_duration,
            queue_depth_timeline=timeline,
        )
    
    def _estimate_ready_count(self, time_us: int, active_tasks: Set[str]) -> int:
        """
        Estimate number of ready but not executing tasks at given time:
        tasks with ready_us <= time_us < start_us.

        Simplified heuristic based on graph structure.

        Answered via binary search over self._sorted_ready_times/
        _sorted_start_times (O(log N), P1-21) instead of an O(N) scan of
        self.tasks per call - this was the single largest hotspot found
        while profiling P1-16's fix, called once per occupancy segment
        (O(N*segments) overall).

        active_tasks and finish_us were checked by the original O(N)
        version but are provably redundant for this condition: a task
        satisfying ready_us <= time_us < start_us cannot simultaneously
        be "active" (which requires start_us <= time_us < finish_us -
        contradicts start_us > time_us), and start_us > time_us already
        guarantees finish_us >= start_us > time_us (a task can't finish
        before it starts), so the "not yet finished" check can never
        exclude anything the ready-vs-started counts don't already rule
        out. active_tasks is kept as a parameter for interface stability
        (the caller still passes it) but is no longer consulted.
        """
        ready_so_far = bisect.bisect_right(self._sorted_ready_times, time_us)
        started_so_far = bisect.bisect_right(self._sorted_start_times, time_us)
        return max(0, ready_so_far - started_so_far)
    
    def compute_blast_radius(self) -> List[BlastRadiusResult]:
        """
        Compute blast radius for all elements (Part 25).
        
        Uses reverse reachability from graph analysis.
        """
        downstream_counts = self.graph_analysis.get('downstream_count', {})

        # Get reachable from targets from graph analysis
        reachable_from_targets = set(self.graph_analysis.get('reachable_from_targets', []))

        # Actual downstream element sets, already computed once for the
        # whole graph by analyze_graph's O(N+E) reverse traversal (Part 41)
        # - reused here rather than re-traversing per element.
        reachable_downstream = self.graph_analysis.get('reachable_downstream', {})

        # Build element duration map
        element_durations: Dict[str, int] = defaultdict(int)
        for task in self.tasks:
            elem_uid = task.task_key.element_uid
            element_durations[elem_uid] += task.dur_us

        # Element UIDs on the critical path, precomputed once - O(1)
        # membership check per element below instead of an any(...) scan
        # over self.critical_path per element (O(N) work per element,
        # O(N^2) overall; the single largest hotspot found while
        # profiling P1-16's fix, P1-21).
        critical_path_element_uids = {
            self.task_map[tk].task_key.element_uid
            for tk in self.critical_path
            if self.task_map.get(tk)
        }

        results = []
        for elem_uid in downstream_counts.keys():
            downstream_count = downstream_counts[elem_uid]

            # Weighted downstream duration = sum of the *actual* downstream
            # elements' own durations, not a global average multiplied by
            # count (two elements with the same downstream_count but very
            # different real downstream workloads must not report the same
            # weighted_duration).
            downstream_uids = reachable_downstream.get(elem_uid, [])
            weighted_duration = sum(element_durations.get(uid, 0) for uid in downstream_uids)

            # Check if leaf (no downstream)
            is_leaf = downstream_count == 0

            # Check if on critical path
            elem_on_cp = elem_uid in critical_path_element_uids

            # Check if required by target (reachable from requested targets)
            # If no targets specified, assume all are required
            is_required = elem_uid in reachable_from_targets or not reachable_from_targets
            
            results.append(BlastRadiusResult(
                element_uid=elem_uid,
                downstream_count=downstream_count,
                downstream_weighted_duration_us=weighted_duration,
                is_leaf=is_leaf,
                is_on_critical_path=elem_on_cp,
                is_required_by_target=is_required,
            ))
        
        # Sort by downstream count descending
        results.sort(key=lambda x: x.downstream_count, reverse=True)
        
        return results
    
    def compute_criticality_probability(
        self,
        num_samples: int = DEFAULT_MC_SAMPLES,
        perturbation_pct: float = DEFAULT_PERTURBATION_PCT,
    ) -> List[CriticalityProbability]:
        """
        Compute Monte-Carlo criticality probability (Part 26).
        
        Perturbs task durations and recomputes critical path multiple times.
        
        Args:
            num_samples: Number of Monte-Carlo samples (default 200)
            perturbation_pct: Duration perturbation percentage (default ±10%)
        """
        if not self.tasks:
            return []
        
        # Seed RNG for determinism
        rng = random.Random(self.MC_RANDOM_SEED)
        
        # Get base durations
        base_durations: Dict[str, int] = {
            str(t.task_key): t.dur_us for t in self.tasks
        }
        
        # Track critical path appearances
        critical_counts: Dict[str, int] = defaultdict(int)
        
        for _ in range(num_samples):
            # Perturb durations
            perturbed = {}
            for task_key, duration in base_durations.items():
                # Apply ±perturbation_pct uniformly
                factor = 1.0 + rng.uniform(-perturbation_pct, perturbation_pct)
                perturbed[task_key] = int(duration * factor)

            # Recompute the critical path with these perturbed durations -
            # a genuine per-sample resample, not a cached/unperturbed
            # approximation. Returns element UIDs (critical path is
            # defined on the element graph, Part 24.1), not task keys.
            perturbed_cp = self._compute_perturbed_critical_path(perturbed)

            for elem_uid_on_path in perturbed_cp:
                critical_counts[elem_uid_on_path] += 1

        # Build results
        results = []
        for task in self.tasks:
            task_key = str(task.task_key)
            elem_uid = task.task_key.element_uid

            # critical_counts is keyed by element UID (see above) - looking
            # this up by the full task_key string always missed, silently
            # collapsing every probability to 0.0 regardless of how many
            # samples actually landed on this element's critical path.
            count = critical_counts.get(elem_uid, 0)
            probability = count / num_samples if num_samples > 0 else 0.0
            
            # Get observed slack
            obs_slack = self.slack.get(task_key, 0)

            # self.critical_path is a set of element UIDs (compute_critical_path
            # operates on the element graph, Part 5.3/14.1), not task_key
            # strings - same key-format mismatch as critical_counts above,
            # which silently made this always False regardless of the
            # element's real observed criticality.
            obs_critical = elem_uid in self.critical_path
            
            results.append(CriticalityProbability(
                element_uid=elem_uid,
                probability=probability,
                observed_critical=obs_critical,
                observed_slack_us=obs_slack,
                samples=num_samples,
                perturbation_pct=perturbation_pct,
            ))
        
        return results
    
    def _compute_perturbed_critical_path(self, perturbed_durations: Dict[str, int]) -> Set[str]:
        """
        Compute critical path with perturbed durations.
        
        Re-runs the longest path algorithm using the perturbed durations
        to get a genuine Monte Carlo sample.
        """
        # Build task graph with perturbed durations
        # Use the same algorithm as compute_critical_path but with perturbed values
        
        # Get element UIDs from task keys
        elem_durations: Dict[str, int] = {}
        for task_key_str, duration in perturbed_durations.items():
            # Extract element_uid from task_key string (format: element_uid|kind|phase|attempt)
            elem_uid = task_key_str.split('|')[0]
            # Aggregate if multiple tasks per element
            if elem_uid in elem_durations:
                elem_durations[elem_uid] += duration
            else:
                elem_durations[elem_uid] = duration
        
        # Run longest path algorithm with perturbed durations
        predecessors, successors = build_element_graph(self.graph)
        in_degree, _ = compute_in_out_degree(self.graph)
        
        earliest_finish: Dict[str, int] = {}
        pred_on_critical: Dict[str, Optional[str]] = {}
        
        queue = deque()
        for elem_uid, deg in in_degree.items():
            if deg == 0:
                earliest_finish[elem_uid] = elem_durations.get(elem_uid, 0)
                pred_on_critical[elem_uid] = None
                queue.append(elem_uid)
        
        temp_in_degree = dict(in_degree)
        
        while queue:
            current = queue.popleft()
            
            for succ in successors.get(current, []):
                potential_finish = earliest_finish[current] + elem_durations.get(succ, 0)
                
                if succ not in earliest_finish:
                    earliest_finish[succ] = potential_finish
                    pred_on_critical[succ] = current
                elif potential_finish > earliest_finish[succ]:
                    earliest_finish[succ] = potential_finish
                    pred_on_critical[succ] = current
                
                temp_in_degree[succ] -= 1
                if temp_in_degree[succ] == 0:
                    queue.append(succ)
        
        if not earliest_finish:
            return set()
        
        # Find terminal with maximum finish time
        critical_length = 0
        critical_end = None
        
        for elem_uid, finish in earliest_finish.items():
            if elem_uid not in successors or not successors[elem_uid]:
                if finish > critical_length:
                    critical_length = finish
                    critical_end = elem_uid
        
        if critical_end is None:
            critical_length = max(earliest_finish.values())
            critical_end = max(earliest_finish, key=earliest_finish.get)
        
        # Reconstruct critical path
        critical_path = []
        current = critical_end
        while current is not None:
            critical_path.append(current)
            current = pred_on_critical.get(current)
        
        return set(critical_path)
    
    def compute_fetch_build_overlap(self) -> Optional[FetchBuildOverlap]:
        """
        Compute fetch/build overlap analysis (Part 28).
        
        Measures temporal overlap between FETCH and BUILD task kinds.
        """
        if not self.tasks:
            return None
        
        # Separate FETCH and BUILD tasks
        fetch_tasks = [t for t in self.tasks if t.task_key.task_kind == TaskKind.FETCH]
        build_tasks = [t for t in self.tasks if t.task_key.task_kind == TaskKind.BUILD]
        
        if not fetch_tasks or not build_tasks:
            return None
        
        # Compute fetch interval
        fetch_start = min(t.start_us for t in fetch_tasks)
        fetch_end = max(t.finish_us for t in fetch_tasks)
        
        # Compute build interval
        build_start = min(t.start_us for t in build_tasks)
        build_end = max(t.finish_us for t in build_tasks)
        
        # Compute overlap
        overlap_start = max(fetch_start, build_start)
        overlap_end = min(fetch_end, build_end)
        overlap_us = max(0, overlap_end - overlap_start)
        
        # Compute exclusive intervals
        fetch_only_prefix = max(0, overlap_start - fetch_start)
        build_only_suffix = max(0, build_end - overlap_end)
        
        return FetchBuildOverlap(
            fetch_start_us=fetch_start,
            fetch_end_us=fetch_end,
            build_start_us=build_start,
            build_end_us=build_end,
            overlap_us=overlap_us,
            fetch_only_prefix_us=fetch_only_prefix,
            build_only_suffix_us=build_only_suffix,
        )
    
    def compute_leaf_analysis(
        self,
        requested_targets: Optional[Set[str]] = None,
    ) -> List[LeafAnalysis]:
        """
        Compute advanced leaf analysis (Part 24).
        
        Identifies leaf elements and their deferrability.
        
        Args:
            requested_targets: Set of requested target element UIDs
        """
        downstream_counts = self.graph_analysis.get('downstream_count', {})

        # Get reachability from targets using graph analysis
        reachable_from_targets = set(self.graph_analysis.get('reachable_from_targets', []))

        # If no requested_targets specified, assume all elements are reachable
        if not requested_targets:
            reachable_from_targets = set(downstream_counts.keys())

        # Element UIDs on the blame chain / critical path, precomputed
        # once - O(1) membership check per element below instead of an
        # any(...) scan per element (P1-21, same fix as compute_blast_radius).
        blame_chain_element_uids = {
            self.task_map[tk].task_key.element_uid
            for tk in self.blame_chain
            if self.task_map.get(tk)
        }
        critical_path_element_uids = {
            self.task_map[tk].task_key.element_uid
            for tk in self.critical_path
            if self.task_map.get(tk)
        }

        results = []
        for elem_uid, downstream_count in downstream_counts.items():
            is_leaf = downstream_count == 0
            on_blame_chain = elem_uid in blame_chain_element_uids
            on_critical_path = elem_uid in critical_path_element_uids
            is_reachable = elem_uid in reachable_from_targets
            
            # Compute deferrability
            is_potentially_deferrable = is_leaf and not is_reachable
            recommendation = None
            if is_potentially_deferrable:
                recommendation = "Consider deferring or decoupling from main build"
            else:
                recommendation = "Required by target or not a leaf"
            
            results.append(LeafAnalysis(
                element_uid=elem_uid,
                is_leaf=is_leaf,
                is_on_blame_chain=on_blame_chain,
                is_on_critical_path=on_critical_path,
                is_reachable_from_target=is_reachable,
                is_potentially_deferrable=is_potentially_deferrable,
                recommendation=recommendation,
            ))
        
        return results
    
    def compute_duration_variability(
        self,
        historical_durations: Optional[Dict[str, List[int]]] = None,
    ) -> List[DurationVariability]:
        """
        Compute duration variability statistics (Part 29).
        
        Requires historical duration data from previous runs.
        
        Args:
            historical_durations: Dict mapping task_class to list of durations
        """
        if not historical_durations:
            return []
        
        results = []
        for task_class, durations in historical_durations.items():
            if not durations:
                continue
            
            sorted_dur = sorted(durations)
            n = len(sorted_dur)
            
            mean_us = sum(durations) / n
            median_us = sorted_dur[n // 2]
            p50_us = sorted_dur[int(n * 0.50)]
            p75_us = sorted_dur[int(n * 0.75)]
            p95_us = sorted_dur[int(n * 0.95)]
            
            # Compute coefficient of variation
            variance = sum((d - mean_us) ** 2 for d in durations) / n
            std_dev = variance ** 0.5
            cv = std_dev / mean_us if mean_us > 0 else 0.0
            
            results.append(DurationVariability(
                task_class=task_class,
                mean_us=mean_us,
                median_us=median_us,
                p50_us=p50_us,
                p75_us=p75_us,
                p95_us=p95_us,
                coefficient_of_variation=cv,
                sample_count=n,
            ))
        
        return results
    
    def run_full_diagnostics(
        self,
        occupancy_segments: Optional[List[dict]] = None,
        resource_capacities: Optional[Dict[str, int]] = None,
        requested_targets: Optional[Set[str]] = None,
        historical_durations: Optional[Dict[str, List[int]]] = None,
    ) -> DiagnosticsResult:
        """
        Run complete M5 diagnostics suite.
        
        Args:
            occupancy_segments: Occupancy step function segments
            resource_capacities: Resource capacity configuration
            requested_targets: Requested build targets
            historical_durations: Historical duration data for variability analysis
            
        Returns:
            DiagnosticsResult with all computed metrics
        """
        result = DiagnosticsResult()
        
        # Wall-clock share (Part 20)
        shares = self.compute_wall_clock_shares()
        result.wall_clock_shares = shares
        result.total_active_wall_time_us = sum(s.execution_duration_us for s in shares)
        
        # Ready queue (Part 21)
        if occupancy_segments:
            result.ready_queue = self.compute_ready_queue_metrics(
                occupancy_segments,
                resource_capacities,
            )
        
        # Blast radius (Part 25)
        blast_results = self.compute_blast_radius()
        result.blast_radius = blast_results
        result.top_blast_radius_elements = blast_results[:10]  # Top 10
        
        # Criticality probability (Part 26)
        crit_probs = self.compute_criticality_probability()
        result.criticality_probabilities = crit_probs
        result.high_criticality_elements = [
            cp for cp in crit_probs if cp.probability >= 0.5
        ]
        
        # Fetch/build overlap (Part 28)
        result.fetch_build_overlap = self.compute_fetch_build_overlap()
        
        # Duration variability (Part 29)
        result.duration_variability = self.compute_duration_variability(historical_durations)
        
        # Leaf analysis (Part 24)
        leaf_results = self.compute_leaf_analysis(requested_targets)
        result.leaf_analysis = leaf_results
        result.deferrable_leaves = [la for la in leaf_results if la.is_potentially_deferrable]
        
        # Churn × blast radius (would require historical churn data)
        # Placeholder for future implementation
        result.churn_blast_radius = {}
        
        return result


def analyze_diagnostics(
    normalized_tasks: List[object],
    graph_analysis: dict,
    blame_chain: Optional[List[str]] = None,
    critical_path: Optional[List[str]] = None,
    slack: Optional[Dict[str, int]] = None,
    occupancy_segments: Optional[List[dict]] = None,
    resource_capacities: Optional[Dict[str, int]] = None,
    requested_targets: Optional[Set[str]] = None,
    historical_durations: Optional[Dict[str, List[int]]] = None,
) -> DiagnosticsResult:
    """
    Convenience function to run full diagnostics analysis.
    
    Args:
        normalized_tasks: List of normalized task objects
        graph_analysis: Graph analysis results
        blame_chain: Blame chain task keys
        critical_path: Critical path task keys
        slack: Task slack values
        occupancy_segments: Occupancy segments for ready queue analysis
        resource_capacities: Resource capacities
        requested_targets: Requested build targets
        historical_durations: Historical data for variability
        
    Returns:
        DiagnosticsResult with complete M5 analysis
    """
    analyzer = DiagnosticsAnalyzer(
        normalized_tasks=normalized_tasks,
        graph_analysis=graph_analysis,
        blame_chain=blame_chain,
        critical_path=critical_path,
        slack=slack,
    )
    
    result = analyzer.run_full_diagnostics(
        occupancy_segments=occupancy_segments,
        resource_capacities=resource_capacities,
        requested_targets=requested_targets,
        historical_durations=historical_durations,
    )
    logger.info("Diagnostics computed for %d tasks", len(normalized_tasks))
    return result
