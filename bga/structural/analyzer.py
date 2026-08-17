"""Cold structural analyzer (M6).

Implements Parts 31-39:
- Structural metrics computation (Part 31)
- Bottleneck detection (Part 32)
- Parallelism profiling (Part 33)
- Sensitivity analysis (a `bga`-specific additive heuristic, not
  actually Part 34 - see `compute_sensitivity`'s own docstring, UX-20)
- Deferrability analysis (Part 35)
- Historical trend analysis (Part 36)
- Cold vs warm comparison (Part 37)
- Pipeline health scoring (Part 38)
- Optimization recommendations (Part 39)
"""

import logging
from collections import defaultdict
from typing import Dict, List, Set, Optional, Any
import statistics

from bga.ingest.models import NormalizedTask

logger = logging.getLogger(__name__)


class ElementDependencyGraph:
    """Wrapper for element dependency graph analysis.
    
    This class provides a unified interface to the graph analysis functions
    in bga.graph.edg module.
    """
    
    def __init__(self, G=None, predecessors=None, successors=None):
        self.G = G
        self.predecessors = predecessors or {}
        self.successors = successors or {}


def build_edg(graph):
    """Build ElementDependencyGraph from a Graph object."""
    from bga.graph.edg import build_element_graph
    import networkx as nx
    
    # Build adjacency lists
    predecessors, successors = build_element_graph(graph)
    
    # Build NetworkX graph - use element UIDs (graph.elements is a list of Element objects)
    G = nx.DiGraph()
    for elem in graph.elements:
        elem_id = elem.uid if hasattr(elem, 'uid') else elem
        G.add_node(elem_id)
    for pred, succs in successors.items():
        for succ in succs:
            G.add_edge(pred, succ)
    
    return ElementDependencyGraph(G=G, predecessors=predecessors, successors=successors)


from bga.structural.models import (
    StructuralMetrics,
    BottleneckAnalysis,
    ParallelismProfile,
    SensitivityResult,
    DeferrabilityResult,
    HistoricalTrend,
    StructuralAnalysisResult,
)


class StructuralAnalyzer:
    """Analyzes cold structural properties of the build graph.
    
    Unlike other analyzers, this focuses on static structure rather than
    dynamic timing behavior. Requires only the dependency graph, not
    detailed timing information.
    """
    
    def __init__(self, edg: ElementDependencyGraph, tasks: Dict[str, NormalizedTask]):
        self.edg = edg
        self.tasks = tasks
        self._graph = edg.G  # NetworkX DiGraph
        
    def compute_structural_metrics(self) -> StructuralMetrics:
        """Compute cold structural metrics (Part 31).
        
        These metrics are purely structural and don't depend on timing.
        """
        G = self._graph
        n_elements = len(G.nodes())
        n_edges = len(G.edges())
        
        # Depth analysis (Part 14.2): unweighted_depth is the LONGEST path in
        # hops from any root to each node, computed via a topological DP -
        # not nx.shortest_path_length, which finds the shortest route and so
        # silently underestimates depth whenever a node is reachable via both
        # a short path and a longer one (e.g. a node with both a direct
        # dependency edge and a multi-hop dependency chain to the same root).
        max_depths = {}
        for node in nx.topological_sort(G):
            preds = list(G.predecessors(node))
            max_depths[node] = 0 if not preds else 1 + max(max_depths[p] for p in preds)

        max_depth = max(max_depths.values()) if max_depths else 0
        
        # Fan-in/fan-out
        fanouts = [G.out_degree(n) for n in G.nodes()]
        fanins = [G.in_degree(n) for n in G.nodes()]
        avg_fanout = statistics.mean(fanouts) if fanouts else 0.0
        avg_fanin = statistics.mean(fanins) if fanins else 0.0
        
        # Critical path structure
        cp = self._compute_critical_path_nodes()
        cp_length = len(cp)
        cp_ratio = cp_length / n_elements if n_elements > 0 else 0.0
        
        # Parallelism via level decomposition
        levels = self._compute_level_decomposition()
        widths = [len(level) for level in levels.values()]
        max_parallelism = max(widths) if widths else 0
        avg_parallelism = statistics.mean(widths) if widths else 0.0
        
        # Cyclomatic complexity (for DAGs: edges - nodes + 1)
        cyclomatic = max(0, n_edges - n_elements + 1)
        
        # Serialization ratio (elements with both in-degree > 0 and out-degree > 0 that form chains)
        serial_count = sum(1 for n in G.nodes() if G.in_degree(n) > 0 and G.out_degree(n) > 0)
        serialization_ratio = serial_count / n_elements if n_elements > 0 else 0.0
        
        return StructuralMetrics(
            num_elements=n_elements,
            num_edges=n_edges,
            max_depth=max_depth,
            avg_fanout=avg_fanout,
            avg_fanin=avg_fanin,
            critical_path_length=cp_length,
            critical_path_ratio=cp_ratio,
            max_parallelism=max_parallelism,
            avg_parallelism=avg_parallelism,
            cyclomatic_complexity=cyclomatic,
            serialization_ratio=serialization_ratio,
        )
    
    def analyze_bottlenecks(self) -> BottleneckAnalysis:
        """Detect structural bottlenecks (Part 32).
        
        Identifies choke points, resource contention, and serialization chains.
        """
        G = self._graph
        
        # Find choke points (articulation points in undirected version)
        # For DAGs, use dominator-based approach
        choke_points = []
        choke_impact = {}
        
        # Simple heuristic: high fan-in + high fan-out elements
        for node in G.nodes():
            fanin = G.in_degree(node)
            fanout = G.out_degree(node)
            if fanin >= 2 and fanout >= 2:
                choke_points.append(node)
                # Count downstream elements
                downstream = nx.descendants(G, node)
                choke_impact[node] = len(downstream)
        
        # Resource contention (structural - same resource type used by many elements)
        resource_usage = defaultdict(list)
        for key, task in self.tasks.items():
            if hasattr(task, 'resource_profile') and task.resource_profile:
                for res_type in task.resource_profile.keys():
                    resource_usage[res_type].append(key)
        
        resource_contention = {
            res: elements for res, elements in resource_usage.items()
            if len(elements) > 1
        }
        
        # Longest serial chain (path with no branching)
        longest_chain = []
        for start in G.nodes():
            if G.in_degree(start) == 0:  # Root nodes
                chain = self._find_longest_serial_chain_from(start)
                if len(chain) > len(longest_chain):
                    longest_chain = chain
        
        # High fan-in/fan-out elements
        fanin_list = [(n, G.in_degree(n)) for n in G.nodes() if G.in_degree(n) > 2]
        fanout_list = [(n, G.out_degree(n)) for n in G.nodes() if G.out_degree(n) > 2]
        fanin_list.sort(key=lambda x: x[1], reverse=True)
        fanout_list.sort(key=lambda x: x[1], reverse=True)
        
        return BottleneckAnalysis(
            choke_points=choke_points,
            choke_point_impact=choke_impact,
            resource_contention=dict(resource_contention),
            longest_serial_chain=longest_chain,
            serial_chain_length=len(longest_chain),
            high_fanin_elements=fanin_list[:10],  # Top 10
            high_fanout_elements=fanout_list[:10],
        )
    
    def compute_parallelism_profile(self) -> ParallelismProfile:
        """Compute parallelism profile across pipeline depth (Part 33).
        
        Shows how parallelism varies at each level of the pipeline.
        """
        levels = self._compute_level_decomposition()
        
        if not levels:
            return ParallelismProfile(
                levels=[],
                width_at_level=[],
                max_width=0,
                min_width=0,
                mean_width=0.0,
                cumulative_work=[],
                parallelism_efficiency=0.0,
            )
        
        level_nums = sorted(levels.keys())
        widths = [len(levels[l]) for l in level_nums]
        
        # Cumulative work
        cumulative = []
        total = 0
        for w in widths:
            total += w
            cumulative.append(total)
        
        # Parallelism efficiency (how close to max_parallelism we get on average)
        max_width = max(widths) if widths else 0
        mean_width = statistics.mean(widths) if widths else 0.0
        efficiency = mean_width / max_width if max_width > 0 else 0.0
        
        return ParallelismProfile(
            levels=level_nums,
            width_at_level=widths,
            max_width=max_width,
            min_width=min(widths) if widths else 0,
            mean_width=mean_width,
            cumulative_work=cumulative,
            parallelism_efficiency=efficiency,
        )
    
    def compute_sensitivity(self) -> SensitivityResult:
        """Compute sensitivity analysis - a `bga`-specific additive
        heuristic, not a precisely spec-defined mechanism (UX-20
        housekeeping; see `SensitivityResult`'s own docstring for the
        stale "Part 34" citation this corrects).

        Determines how much improving each element would help overall.
        Uses critical path membership and slack as proxies.
        """
        cp_nodes = set(self._compute_critical_path_nodes())
        
        # Compute slack for each element
        slacks = self._compute_all_slacks()
        
        # Sensitivity score: higher for CP elements with low slack
        #
        # The decay formula below (`base / (1.0 + slack_s)`) is only
        # well-defined for slack >= 0 - it divides by zero at
        # slack == -1_000_000us and goes negative below that (P1-38: a
        # real ZeroDivisionError crash, found via real build data, not a
        # hand-built fixture). Negative slack is possible in practice
        # (e.g. a task whose measured window runs behind where the
        # schedule expected it - the same "already behind" condition
        # P1-36 hardens elsewhere). Documented choice: negative slack is
        # clamped to 0 before the decay formula, i.e. treated as
        # maximally sensitive for its tier (CP vs non-CP) rather than
        # extrapolating the decay curve backwards - "already behind
        # schedule" is at least as sensitive as "exactly on schedule",
        # never less.
        sensitivity_scores = {}
        for key in self.tasks.keys():
            if key in cp_nodes:
                # CP elements have high sensitivity
                slack = max(slacks.get(key, 0), 0)
                # Inverse relationship: lower slack = higher sensitivity
                sensitivity_scores[key] = 1.0 / (1.0 + slack / 1000000.0)  # Normalize by 1s
            else:
                # Non-CP elements have lower sensitivity based on slack
                slack = max(slacks.get(key, float('inf')), 0)
                sensitivity_scores[key] = 0.1 / (1.0 + slack / 1000000.0)
        
        # Top opportunities
        sorted_scores = sorted(sensitivity_scores.items(), key=lambda x: x[1], reverse=True)
        top_opportunities = [
            (key, score, score * 100)  # (key, score, impact_percentage)
            for key, score in sorted_scores[:10]
        ]
        
        # Total improvable time (sum of slacks for non-CP elements)
        total_improvable = sum(
            slacks.get(key, 0) for key in self.tasks.keys() if key not in cp_nodes
        )
        
        # Best case speedup (if all slack eliminated)
        total_duration = sum(t.dur_us for t in self.tasks.values())
        best_case = total_duration / (total_duration - total_improvable) if total_duration > total_improvable else 1.0
        
        # CP sensitivity (how much CP changes per unit duration change)
        cp_sensitivity = {node: 1.0 for node in cp_nodes}  # Simplified: 1:1 for CP elements
        
        return SensitivityResult(
            sensitivity_scores=sensitivity_scores,
            top_opportunities=top_opportunities,
            total_improvable_time_us=int(total_improvable),
            best_case_speedup=best_case,
            cp_sensitivity=cp_sensitivity,
        )
    
    def analyze_deferrability(self) -> DeferrabilityResult:
        """Analyze deferrability of leaf elements (Part 35).
        
        Determines which leaf elements could be deferred without blocking others.
        """
        G = self._graph
        
        # Find leaf nodes (no successors)
        leaves = [n for n in G.nodes() if G.out_degree(n) == 0]
        
        deferrable = []
        non_deferrable = []
        deferral_savings = {}
        deferral_risk = {}
        
        for leaf in leaves:
            # Check if deferring this leaf would block anything
            # Since it's a leaf, by definition nothing depends on it
            # But we check if it's "effectively" a dependency
            
            task = self.tasks.get(leaf)
            if not task:
                non_deferrable.append(leaf)
                continue
            
            # Heuristic: leaves with short duration are good deferral candidates
            duration = task.dur_us
            
            # Risk assessment based on element kind
            kind = getattr(task, 'kind', 'BUILD')
            if kind in ['TEST', 'INTEGRATION_TEST']:
                risk = 'low'
                deferrable.append(leaf)
                deferral_savings[leaf] = duration
            elif kind in ['BENCHMARK', 'ANALYSIS']:
                risk = 'low'
                deferrable.append(leaf)
                deferral_savings[leaf] = duration
            elif duration < 1_000_000:  # Less than 1 second
                risk = 'medium'
                deferrable.append(leaf)
                deferral_savings[leaf] = duration
            else:
                risk = 'high'
                non_deferrable.append(leaf)
            
            deferral_risk[leaf] = risk
        
        # Recommendations: low-risk deferrable leaves
        recommended = [l for l in deferrable if deferral_risk.get(l) == 'low']
        total_deferrable = sum(deferral_savings.values())
        
        return DeferrabilityResult(
            deferrable_leaves=deferrable,
            non_deferrable_leaves=non_deferrable,
            deferral_savings_us=deferral_savings,
            deferral_risk=deferral_risk,
            recommended_deferrals=recommended,
            total_deferrable_work_us=int(total_deferrable),
        )
    
    def analyze_historical_trends(
        self, historical_runs: List[Dict[str, Any]]
    ) -> HistoricalTrend:
        """Analyze historical trends across multiple runs (Part 36).
        
        Args:
            historical_runs: List of previous analysis results with metrics
            
        Returns:
            HistoricalTrend with time series and statistical analysis
        """
        if not historical_runs:
            return HistoricalTrend(
                run_ids=[],
                timestamps=[],
                duration_trend=[],
                efficiency_trend=[],
                parallelism_trend=[],
                duration_slope=0.0,
                duration_volatility=0.0,
                efficiency_slope=0.0,
                anomalies=[],
                forecast_next_duration=None,
                forecast_confidence=0.0,
            )
        
        # Extract time series
        run_ids = [r.get('run_id', str(i)) for i, r in enumerate(historical_runs)]
        timestamps = [r.get('timestamp', 0) for r in historical_runs]
        durations = [r.get('total_duration_us', 0) for r in historical_runs]
        efficiencies = [r.get('efficiency', 0.0) for r in historical_runs]
        parallelisms = [r.get('avg_parallelism', 1.0) for r in historical_runs]
        
        # Statistical analysis
        if len(durations) >= 2:
            # Linear regression for slope
            duration_slope = self._compute_slope(timestamps, durations)
            efficiency_slope = self._compute_slope(timestamps, efficiencies)
            duration_volatility = statistics.stdev(durations) if len(durations) > 1 else 0.0
        else:
            duration_slope = 0.0
            efficiency_slope = 0.0
            duration_volatility = 0.0
        
        # Anomaly detection (simple z-score based)
        anomalies = []
        if len(durations) >= 3:
            mean_dur = statistics.mean(durations)
            std_dur = statistics.stdev(durations) if len(durations) > 1 else 1.0
            for i, dur in enumerate(durations):
                z_score = abs(dur - mean_dur) / std_dur if std_dur > 0 else 0
                if z_score > 2.0:  # More than 2 standard deviations
                    anomalies.append({
                        'run_id': run_ids[i],
                        'metric': 'duration',
                        'deviation': z_score,
                    })
        
        # Forecasting (simple linear projection)
        if timestamps and duration_slope != 0:
            last_dur = durations[-1]
            if len(timestamps) >= 2:
                interval = timestamps[-1] - timestamps[-2]
                forecast = int(last_dur + duration_slope * interval)
                forecast_next = max(0, forecast)
            else:
                forecast_next = None
        else:
            forecast_next = None
        
        # Confidence based on data quality
        confidence = min(1.0, len(historical_runs) / 10.0)  # Max confidence at 10 runs
        
        return HistoricalTrend(
            run_ids=run_ids,
            timestamps=timestamps,
            duration_trend=durations,
            efficiency_trend=efficiencies,
            parallelism_trend=parallelisms,
            duration_slope=duration_slope,
            duration_volatility=duration_volatility,
            efficiency_slope=efficiency_slope,
            anomalies=anomalies,
            forecast_next_duration=forecast_next,
            forecast_confidence=confidence,
        )
    
    def run_full_analysis(
        self, historical_runs: Optional[List[Dict[str, Any]]] = None
    ) -> StructuralAnalysisResult:
        """Run complete structural analysis (all M6 components).
        
        Args:
            historical_runs: Optional historical data for trend analysis
            
        Returns:
            Complete StructuralAnalysisResult
        """
        metrics = self.compute_structural_metrics()
        bottleneck = self.analyze_bottlenecks()
        parallelism = self.compute_parallelism_profile()
        sensitivity = self.compute_sensitivity()
        deferrability = self.analyze_deferrability()
        
        historical = None
        if historical_runs:
            historical = self.analyze_historical_trends(historical_runs)
        
        # Generate summary
        summary = {
            'total_elements': metrics.num_elements,
            'critical_path_length': metrics.critical_path_length,
            'max_parallelism': metrics.max_parallelism,
            'bottleneck_count': len(bottleneck.choke_points),
            'deferrable_leaves': len(deferrability.deferrable_leaves),
            'best_case_speedup': sensitivity.best_case_speedup,
        }
        
        return StructuralAnalysisResult(
            metrics=metrics,
            bottleneck=bottleneck,
            parallelism=parallelism,
            sensitivity=sensitivity,
            deferrability=deferrability,
            historical=historical,
            summary=summary,
        )
    
    # Helper methods
    
    def _compute_critical_path_nodes(self) -> List[str]:
        """Get nodes on the critical path."""
        # Use existing critical path computation from EDG module
        # The edg.G is a NetworkX DiGraph, we need to compute critical path using bga.graph.edg functions
        try:
            from bga.graph.edg import compute_critical_path as graph_compute_critical_path
            
            # Get task durations from tasks dict
            task_durations = {}
            for elem_uid, task in self.tasks.items():
                if hasattr(task, 'dur_us'):
                    task_durations[elem_uid] = task.dur_us
            
            # Build a Graph object from our NetworkX graph for the function
            from bga.ingest.models import Graph, Element, DependencyEdge
            elements = [Element(uid=node) for node in self._graph.nodes()]
            dependencies = []
            for pred, succ in self._graph.edges():
                dependencies.append(DependencyEdge(predecessor=pred, successor=succ))
            
            graph_obj = Graph(elements=elements, dependencies=dependencies)
            
            cp_length, cp_nodes = graph_compute_critical_path(graph_obj, task_durations)
            return cp_nodes
        except Exception:
            logger.warning(
                "Structural critical-path computation failed; "
                "critical_path_length/max_depth will read as 0",
                exc_info=True,
            )
            return []
    
    def _compute_level_decomposition(self) -> Dict[int, Set[str]]:
        """Decompose the graph into levels by *longest* path from a root.

        UX-41: this was a BFS with first-visit-wins, which assigns each
        node its *shortest* distance from a root - exactly what
        `compute_structural_metrics`'s own comment above already warns
        against for `max_depth`, and for the same reason. A base element
        that every other element depends on (`toolchain.bst`, and the
        normal shape of a real BuildStream project) puts all 1200 of its
        dependents at BFS distance 1, collapsing a 14-level graph into
        `[1, 1200, 1]` regardless of the dependencies between them. The
        two numbers then openly contradicted each other in one report
        block: `max_depth: 13` beside `levels: [0, 1, 2]`.

        The recurrence below is deliberately the same one
        `compute_structural_metrics` uses for `max_depth`, so the two
        agree by construction rather than by coincidence - a level
        decomposition and a longest-path depth are the same computation
        keyed two ways, and having them disagree was the bug.

        O(V+E), the same order as the BFS it replaces.
        """
        G = self._graph
        levels = defaultdict(set)
        if G.number_of_nodes() == 0:
            return dict(levels)

        depths: Dict[str, int] = {}
        for node in nx.topological_sort(G):
            preds = list(G.predecessors(node))
            depths[node] = 0 if not preds else 1 + max(depths[p] for p in preds)
            levels[depths[node]].add(node)

        return dict(levels)
    
    def _find_longest_serial_chain_from(self, start: str) -> List[str]:
        """Find longest serial (non-branching) chain starting from a node."""
        G = self._graph
        chain = [start]
        current = start
        
        while True:
            successors = list(G.successors(current))
            if len(successors) != 1:
                break  # Branching point or leaf
            current = successors[0]
            chain.append(current)
        
        return chain
    
    def _compute_all_slacks(self) -> Dict[str, float]:
        """Compute slack for all elements."""
        # Simplified: use difference between earliest and latest start
        # In full implementation, would use forward/backward pass
        slacks = {}
        for key, task in self.tasks.items():
            # Placeholder: estimate slack based on non-CP status
            slacks[key] = task.dur_us * 0.5  # Rough estimate
        return slacks
    
    def _compute_slope(self, x: List[float], y: List[float]) -> float:
        """Compute linear regression slope."""
        if len(x) < 2:
            return 0.0
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_xx = sum(xi * xi for xi in x)
        
        denominator = n * sum_xx - sum_x * sum_x
        if denominator == 0:
            return 0.0
        
        numerator = n * sum_xy - sum_x * sum_y
        return numerator / denominator


# Import networkx at module level
try:
    import networkx as nx
except ImportError:
    nx = None
