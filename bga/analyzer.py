"""
Main analyzer module.

Orchestrates the complete analysis pipeline as specified in the v9 specification.
"""

from pathlib import Path
from typing import Optional, Tuple

from .ingest.models import AnalysisResult, Graph, RunContext, Trace
from .ingest.loader import load_all
from .normalize.timestamps import normalize_trace
from .occupancy.sweep import compute_occupancy_stats, compute_task_horizon
from .graph.edg import analyze_graph


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
    
    def __init__(self, run_dir: Optional[Path] = None):
        """
        Initialize the analyzer.
        
        Args:
            run_dir: Path to the run directory containing input files
        """
        self.run_dir = run_dir
        self.run_context: Optional[RunContext] = None
        self.graph: Optional[Graph] = None
        self.trace: Optional[Trace] = None
        self.normalized_tasks = []
        self.violations = []
        self.analysis_result: Optional[AnalysisResult] = None
    
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
    
    def _compute_floors(self) -> dict:
        """
        Compute certified and advisory floors (Part 14-16).
        
        Returns:
            Dict containing floor metrics
        """
        if not self.normalized_tasks:
            return {
                't_infinity_observed': None,
                't_infinity_cold': None,
                'lb': None,
                'certified_headroom': None,
            }
        
        # Get task horizon
        _, _, horizon_us = compute_task_horizon(self.normalized_tasks)
        
        # Get graph analysis
        graph_analysis = analyze_graph(self.graph, self.normalized_tasks)
        t_infinity_observed = graph_analysis['critical_path_length']
        
        # Compute capacity lower bound (simplified - Part 16)
        # LB = max(T∞,observed, max_p(W_p / C_p), serialization bounds)
        lb = t_infinity_observed
        
        # For now, just use T∞ as LB
        # Full implementation would add resource-area bounds
        
        certified_headroom = max(0, horizon_us - lb)
        
        return {
            't_infinity_observed': t_infinity_observed,
            't_infinity_cold': None,  # Requires historical data (M6)
            'lb': lb,
            'certified_headroom': certified_headroom,
        }
    
    def _compute_attribution(self) -> dict:
        """
        Compute measured attribution (Part 11, M2).
        
        Currently returns placeholder - full blame-chain implementation
        is part of M2 milestone.
        
        Returns:
            Dict containing attribution by category
        """
        # Placeholder for M2 implementation
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
    
    def analyze(self) -> AnalysisResult:
        """
        Perform complete analysis.
        
        Executes the full pipeline:
        1. Trace normalization (M0)
        2. Occupancy analysis (M0)
        3. Graph analysis (M1)
        4. Attribution (M2)
        5. Floors computation (M3)
        
        Returns:
            AnalysisResult with all computed metrics
        """
        if self.normalized_tasks is None or len(self.normalized_tasks) == 0:
            self.normalize()
        
        result = AnalysisResult()
        
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
        
        # Attribution (M2 - placeholder)
        result.attribution = self._compute_attribution()
        
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
