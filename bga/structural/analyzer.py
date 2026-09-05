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
import statistics
from collections import defaultdict
from typing import Any, Optional

from bga.ingest.models import NormalizedTask

logger = logging.getLogger(__name__)


class ElementDependencyGraph:
    """Wrapper for element dependency graph analysis.
    
    This class provides a unified interface to the graph analysis functions
    in bga.graph.edg module.
    """
    
    def __init__(self, G=None, predecessors=None, successors=None, G_full=None):
        # UX-52: `G` is the *gating* graph - `runtime`-only edges removed,
        # because they do not constrain build scheduling. `G_full` keeps
        # every edge, for the reachability questions that must count a
        # runtime edge just as much as a build one. See build_edg.
        self.G = G
        self.predecessors = predecessors or {}
        self.successors = successors or {}
        self.G_full = G_full if G_full is not None else G


def build_edg(graph):
    """Build ElementDependencyGraph from a Graph object.

    UX-52: builds **two** graphs, because this class's consumers want
    different ones and `build_element_graph`'s own docstring already says
    so:

    - the *gating* graph excludes `runtime`-only edges, since a runtime
      dependency's product "is not available to the element at build
      time" and therefore does not constrain build scheduling. Everything
      that models scheduling - critical path, depth, level decomposition,
      choke points, slack, the improvement ranking - must use it.
    - the *full* graph keeps every edge, for reachability questions
      (leaf/deferrability, Part 24/25) which must count a runtime edge.

    This previously built one unfiltered graph and used it for both. On a
    real project (`freedesktop-sdk`, 27 runtime edges among 502) that
    inflated the structural critical path from 28 elements to 32 - 14% -
    and skewed every graph-shape signal derived from it. It was invisible
    to every fixture in this repository, none of which contains a single
    runtime edge.
    """
    import networkx as nx

    from bga.graph.edg import build_element_graph

    def _nx_graph(successors_map):
        G = nx.DiGraph()
        for elem in graph.elements:
            elem_id = elem.uid if hasattr(elem, 'uid') else elem
            G.add_node(elem_id)
        for pred, succs in successors_map.items():
            for succ in succs:
                G.add_edge(pred, succ)
        return G

    predecessors, successors = build_element_graph(
        graph, exclude_dependency_types={"runtime"}
    )
    _, successors_full = build_element_graph(graph)

    return ElementDependencyGraph(
        G=_nx_graph(successors),
        predecessors=predecessors,
        successors=successors,
        G_full=_nx_graph(successors_full),
    )


from bga.structural.models import (
    BottleneckAnalysis,
    DeferrabilityResult,
    HistoricalTrend,
    LevelOccupancy,
    ParallelismProfile,
    SensitivityResult,
    StructuralAnalysisResult,
    StructuralMetrics,
    deferral_risk_for,
)

#: `UX-539` used `int.bit_count()`, which is **3.10+**, and
#: `requires-python` is `>=3.9`: 358 failed and 156 errored on the 3.9
#: job while every local run was green. Bound once at import so the
#: fast path stays a method call on the interpreters that have it.
_popcount = getattr(int, "bit_count", None) or (
    lambda value: bin(value).count("1"))


class StructuralAnalyzer:
    """Analyzes cold structural properties of the build graph.
    
    Unlike other analyzers, this focuses on static structure rather than
    dynamic timing behavior. Requires only the dependency graph, not
    detailed timing information.
    """
    
    def __init__(
        self,
        edg: ElementDependencyGraph,
        tasks: dict[str, NormalizedTask],
        element_durations: Optional[dict[str, int]] = None,
        element_head_durations: Optional[dict[str, int]] = None,
    ):
        """
        `element_durations` (UX-50) is the authoritative per-element
        duration in microseconds, summed across *all* of that element's
        tasks by the caller.

        It exists because `tasks` is keyed by element UID while a real
        BuildStream element has more than one task - at minimum a FETCH
        and a BUILD - so the caller's `{t.task_key.element_uid: t}`
        comprehension silently kept whichever arrived last. When that was
        the FETCH, this analyzer saw a zero-duration element: on one real
        capture the two *heaviest* elements in the build (`core.bst` at
        9.0s and `codegen.bst` at 6.0s) were both read as 0.00s, which
        dropped them from the improvement ranking entirely and understated
        the critical path by 9 seconds. It was data-order dependent, and
        so struck some real runs and not others.

        Summing across an element's tasks - rather than picking the BUILD
        - is deliberate: it is the total work attributable to the
        element, it stays correct if BuildStream grows another task kind,
        and it coincides with the BUILD duration whenever the other tasks
        are zero (which they are in every capture examined).

        `None` falls back to the old per-task lookup, which keeps this
        class usable from tests that construct one task per element.
        """
        self.edg = edg
        self.tasks = tasks
        self.element_durations = element_durations
        # UX-60: the per-element stage that waits on nothing (a FETCH,
        # which under unlimited capacity starts at t=0). Threaded here
        # for one reason: `sensitivity.critical_path_us` and
        # `floors.t_infinity_observed` are required to stay equal, and
        # they are computed by two different traversals. A model applied
        # to one of them is `UX-52` again.
        self.element_head_durations = element_head_durations or {}
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
        serialization_share = serial_count / n_elements if n_elements > 0 else 0.0
        
        return StructuralMetrics(
            num_elements=n_elements,
            num_edges=n_edges,
            max_depth=max_depth,
            avg_fanout=avg_fanout,
            avg_fanin=avg_fanin,
            critical_path_length=cp_length,
            critical_path_share=cp_ratio,
            max_parallelism=max_parallelism,
            avg_parallelism=avg_parallelism,
            cyclomatic_complexity=cyclomatic,
            serialization_share=serialization_share,
        )
    
    def _reachability_counts(self):
        """`(|descendants|, |ancestors|)` per node, from one closure.

        UX-539: the per-node walk this replaces is O(V*(V+E)); a bitset
        closure over the topological order is O(V*E/64) plus the OR per
        edge. `build_element_graph` rejects a cycle before the graph
        reaches this class, so a topological order always exists.
        """
        G = self._graph
        order = list(nx.topological_sort(G))
        index = {node: i for i, node in enumerate(order)}
        bit = [1 << i for i in range(len(order))]

        descendants = [0] * len(order)
        for node in reversed(order):
            mask = 0
            for succ in G.successors(node):
                j = index[succ]
                mask |= descendants[j] | bit[j]
            descendants[index[node]] = mask

        ancestors = [0] * len(order)
        for node in order:
            mask = 0
            for pred in G.predecessors(node):
                j = index[pred]
                mask |= ancestors[j] | bit[j]
            ancestors[index[node]] = mask

        return (
            {node: _popcount(descendants[i]) for node, i in index.items()},
            {node: _popcount(ancestors[i]) for node, i in index.items()},
        )

    def analyze_bottlenecks(self) -> BottleneckAnalysis:
        """Detect structural bottlenecks (Part 32).
        
        Identifies choke points, resource contention, and serialization chains.
        """
        G = self._graph
        
        # UX-43: a choke point is an element that *nothing else can
        # overlap with* - every other element in the build is either
        # strictly upstream of it or strictly downstream of it, so when
        # it runs, it runs alone. Equivalently `|ancestors| +
        # |descendants| == N - 1`.
        #
        # This replaces `in_degree >= 2 and out_degree >= 2`, a
        # placeholder that flagged 606 of 1202 elements (50.4%) on a
        # realistically-shaped graph - "has two parents and two
        # children" is simply the common case in any layered build.
        #
        # The comment that used to sit here proposed a dominator-based
        # definition. That was measured and rejected on real data:
        # dominance asks "does every *path* to B pass through A", which
        # is the right question for a control-flow graph where one path
        # is taken. BuildStream dependencies are conjunctive - every
        # predecessor must finish - so on the 1202-element fixture,
        # where each module depends directly on `toolchain.bst`, 1201 of
        # 1202 nodes have the virtual root as their immediate dominator
        # and the signal is vacuous. Overlap is the property that
        # actually matters for a build, and it is exact rather than
        # heuristic.
        #
        # UX-539: only the two *counts* are wanted, so they come from
        # one bitset closure over the topological order rather than
        # `nx.descendants`/`nx.ancestors` once per node - O(V*(V+E))
        # and 33.8s of a 24.7s-wall analysis under cProfile at 4,002.
        choke_points = []
        choke_impact = {}

        n_nodes = G.number_of_nodes()
        descendant_count, ancestor_count = self._reachability_counts()
        for node in G.nodes():
            downstream = descendant_count[node]
            if downstream + ancestor_count[node] == n_nodes - 1:
                choke_points.append(node)
                choke_impact[node] = downstream

        # Ranked by how much waits on them, so the report's own cap
        # shows the ones worth reading first rather than an arbitrary
        # graph-iteration order.
        choke_points.sort(key=lambda node: (-choke_impact[node], node))
        
        # Resource contention (structural - same resource type used by many elements)
        resource_usage = defaultdict(list)
        for key, task in self.tasks.items():
            if hasattr(task, 'resource_profile') and task.resource_profile:
                for res_type in task.resource_profile:
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
                width_uniformity=0.0,
            )
        
        level_nums = sorted(levels.keys())
        widths = [len(levels[l]) for l in level_nums]
        # UX-641: the uids this line used to discard. `sorted` because a
        # set's iteration order is not stable across processes and this
        # is a published, byte-compared document.
        occupancy = [
            LevelOccupancy(level=l, width=len(levels[l]),
                           elements=sorted(levels[l]))
            for l in level_nums
        ]

        # Cumulative work
        cumulative = []
        total = 0
        for w in widths:
            total += w
            cumulative.append(total)
        
        # UX-49: this ratio is level-width *uniformity*, and is named
        # for that now. It was called `parallelism_efficiency`, under
        # which a pure serial chain scored a perfect 1.000. See
        # ParallelismProfile.width_uniformity for why it was renamed
        # rather than redefined - `mean_width` right above already
        # answers "how parallel is this build".
        max_width = max(widths) if widths else 0
        mean_width = statistics.mean(widths) if widths else 0.0
        uniformity = mean_width / max_width if max_width > 0 else 0.0
        
        return ParallelismProfile(
            levels=occupancy,
            width_at_level=widths,
            max_width=max_width,
            min_width=min(widths) if widths else 0,
            mean_width=mean_width,
            cumulative_work=cumulative,
            width_uniformity=uniformity,
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
        durations = self._durations()
        makespan = self._longest_path_us()

        # An element with positive slack cannot move the finish at all -
        # that is what slack *means* - so its potential saving is 0, not
        # a small positive score. The old formula gave every non-CP
        # element a nonzero score and thereby ranked genuinely useless
        # work above genuinely useful work whenever the useless element
        # happened to be shorter.
        #
        # For a zero-slack (critical path) element, shortening it moves
        # the finish one-for-one only until some other path becomes
        # critical. The smallest positive slack in the graph is exactly
        # how much room there is before that happens, so it bounds the
        # saving from *any* single element - a global O(V) quantity
        # rather than a per-element second-longest-path search.
        positive_slacks = [s for s in slacks.values() if s > 0]
        next_binding_gap = min(positive_slacks) if positive_slacks else float('inf')

        potential_saving = {}
        for key in self.tasks:
            slack = max(slacks.get(key, 0), 0)
            if slack > 0:
                potential_saving[key] = 0.0
            else:
                potential_saving[key] = min(float(durations.get(key, 0)), next_binding_gap)

        # Score is the fraction of the finish this element could remove -
        # a real 0..1 quantity, and directly comparable across runs.
        sensitivity_scores = {
            key: (saving / makespan if makespan > 0 else 0.0)
            for key, saving in potential_saving.items()
        }

        # Rank by saving, breaking ties on duration: when many critical
        # path elements are capped by the same `next_binding_gap`, the
        # longer one is the better place to start, since it has more room
        # to give once the first bound is relieved.
        ranked = sorted(
            sensitivity_scores.items(),
            key=lambda item: (item[1], durations.get(item[0], 0)),
            reverse=True,
        )
        top_opportunities = [
            (key, score, score * 100)  # (key, score, impact_percentage)
            for key, score in ranked[:10]
            if score > 0
        ]

        # How much the finish could drop if every critical path element
        # were free. Computed by re-running the longest-path pass with
        # those nodes zeroed rather than by summing per-element savings,
        # which would double-count: the savings are not independent, and
        # removing one element exposes the next binding path.
        #
        # This is a *structural* bound - it knows only the graph and the
        # measured durations. It is not `certified_headroom`, which
        # certifies against this run's measured resource floors; the two
        # answer different questions and the report says so.
        zero_slack_nodes = {
            node for node, slack in slacks.items() if max(slack, 0) <= 0
        }
        residual = self._longest_path_us(zeroed=zero_slack_nodes)
        total_improvable = max(0, makespan - residual)
        # `residual == 0` means every element is on the critical path
        # (a pure chain, and every graph with a single path), so there is
        # no structural floor and the ratio is unbounded. Reporting 1.0
        # there - "no speedup available" - would state the opposite of
        # the truth, so it is reported as unknown instead, the same way
        # `t_infinity_cold`/`cold_confidence` already represent
        # genuinely-absent values.
        best_case = makespan / residual if residual > 0 else None

        # CP sensitivity (how much CP changes per unit duration change)
        cp_sensitivity = dict.fromkeys(cp_nodes, 1.0)  # Simplified: 1:1 for CP elements

        return SensitivityResult(
            sensitivity_scores=sensitivity_scores,
            top_opportunities=top_opportunities,
            total_improvable_time_us=int(total_improvable),
            best_case_speedup=best_case,
            critical_path_us=int(makespan),
            cp_sensitivity=cp_sensitivity,
        )
    
    def analyze_deferrability(self) -> DeferrabilityResult:
        """Analyze deferrability of leaf elements (Part 35).
        
        Determines which leaf elements could be deferred without blocking others.

        UX-52: uses the *full* graph. "Is anything downstream of this
        element" is a reachability question, and an element that only a
        `runtime` dependency points at is still depended upon - treating
        it as a leaf because the edge does not gate scheduling would be
        the wrong answer to a different question.
        """
        G = self.edg.G_full
        
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
            
            # UX-288: one rule, in `models.deferral_risk_for`, because
            # the leaf record publishes it too and two copies would be
            # two answers waiting to disagree.
            kind = getattr(task, 'kind', 'BUILD')
            risk = deferral_risk_for(kind, duration)
            if risk in ('low', 'medium'):
                deferrable.append(leaf)
                deferral_savings[leaf] = duration
            else:
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
        self, historical_runs: list[dict[str, Any]]
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
        self, historical_runs: Optional[list[dict[str, Any]]] = None
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
        
        # UX-535: the three facts this took from `metrics` are the ones
        # `graph_metrics` publishes from the same object, so they are read
        # there rather than repeated under a second spelling.
        summary = {
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
    
    def _compute_critical_path_nodes(self) -> list[str]:
        """Get nodes on the critical path."""
        # Use existing critical path computation from EDG module
        # The edg.G is a NetworkX DiGraph, we need to compute critical path using bga.graph.edg functions
        try:
            from bga.graph.edg import compute_critical_path as graph_compute_critical_path
            
            # UX-50: the same per-element durations every other path
            # computation in this class uses - not `self.tasks`, which
            # holds one arbitrary task per element.
            task_durations = dict(self._durations())
            
            # Build a Graph object from our NetworkX graph for the function
            from bga.ingest.models import DependencyEdge, Element, Graph
            elements = [Element(uid=node) for node in self._graph.nodes()]
            dependencies = []
            for pred, succ in self._graph.edges():
                dependencies.append(DependencyEdge(predecessor=pred, successor=succ))
            
            graph_obj = Graph(elements=elements, dependencies=dependencies)
            
            cp_length, cp_nodes = graph_compute_critical_path(
                graph_obj, task_durations,
                head_durations=self.element_head_durations,
            )
            return cp_nodes
        except Exception:
            logger.warning(
                "Structural critical-path computation failed; "
                "critical_path_length/max_depth will read as 0",
                exc_info=True,
            )
            return []
    
    def _compute_level_decomposition(self) -> dict[int, set[str]]:
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

        depths: dict[str, int] = {}
        for node in nx.topological_sort(G):
            preds = list(G.predecessors(node))
            depths[node] = 0 if not preds else 1 + max(depths[p] for p in preds)
            levels[depths[node]].add(node)

        return dict(levels)
    
    def _find_longest_serial_chain_from(self, start: str) -> list[str]:
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
    
    def _durations(self) -> dict[str, int]:
        """Duration in microseconds for every *graph* node.

        The graph and the task table need not agree: a node with no
        recorded task (or a structural element that ran no build
        command) contributes 0, which is the correct identity for every
        path computation below.

        UX-50: prefers the caller's summed per-element durations, which
        are the only source that accounts for an element having more
        than one task. See `__init__`.
        """
        if self.element_durations is not None:
            return {
                node: self.element_durations.get(node, 0) or 0
                for node in self._graph.nodes()
            }
        return {
            node: getattr(self.tasks.get(node), 'dur_us', 0) or 0
            for node in self._graph.nodes()
        }

    def _longest_path_us(self, zeroed: Optional[set[str]] = None) -> int:
        """Longest weighted path through the graph, in microseconds.

        `zeroed` treats the named nodes as instantaneous, which is how
        `compute_sensitivity` asks "what would the finish be if this
        work were free?" without mutating anything. O(V+E).
        """
        zeroed = zeroed or set()
        durations = self._durations()
        heads = self.element_head_durations
        finish: dict[str, int] = {}
        longest = 0
        for node in nx.topological_sort(self._graph):
            duration = 0 if node in zeroed else durations[node]
            # UX-60: an element's work cannot start before its own
            # sources arrive *or* before its dependencies finish. A
            # `zeroed` node is being asked "what if this work were free",
            # which is a question about its build, not about waiting for
            # its own sources - so the head stays.
            start = max(
                heads.get(node, 0),
                max((finish[p] for p in self._graph.predecessors(node)), default=0),
            )
            finish[node] = start + duration
            longest = max(longest, finish[node])
        return longest

    def _compute_all_slacks(self) -> dict[str, float]:
        """Total slack per element, from a real CPM forward/backward pass.

        UX-44: this used to be `task.dur_us * 0.5` for every element -
        a placeholder, under a docstring saying the full implementation
        "would use forward/backward pass". Because it was the sole input
        to `compute_sensitivity`, every quantity that function published
        was a function of duration alone: the improvement ranking came
        out strictly *inverted* by duration, and `best_case_speedup` was
        a near-constant ~2.0x for any graph.

        Slack here is the standard total float: how long an element
        could be delayed without pushing the project finish. Critical
        path elements get exactly 0 by construction, which is what makes
        the CP/non-CP distinction in `compute_sensitivity` derivable
        rather than something to be looked up separately.

        O(V+E). Keyed by graph node, and every task key is a graph node.
        """
        G = self._graph
        durations = self._durations()
        order = list(nx.topological_sort(G))

        earliest_start: dict[str, int] = {}
        for node in order:
            earliest_start[node] = max(
                (earliest_start[p] + durations[p] for p in G.predecessors(node)),
                default=0,
            )
        makespan = max(
            (earliest_start[node] + durations[node] for node in order), default=0
        )

        latest_finish: dict[str, int] = {}
        for node in reversed(order):
            latest_finish[node] = min(
                (latest_finish[s] - durations[s] for s in G.successors(node)),
                default=makespan,
            )

        return {
            node: float(latest_finish[node] - durations[node] - earliest_start[node])
            for node in order
        }
    
    def _compute_slope(self, x: list[float], y: list[float]) -> float:
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
