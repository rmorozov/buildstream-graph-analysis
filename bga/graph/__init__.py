"""Graph module for dependency analysis."""

from .edg import (
    analyze_graph,
    build_element_graph,
    compute_critical_path,
    compute_dominators,
    compute_downstream_count,
    compute_in_out_degree,
    compute_reachability,
    compute_reverse_reachability_from_targets,
    compute_slack,
    compute_unweighted_depth,
    compute_weighted_depth,
    find_requested_targets,
    find_terminal_elements,
)

__all__ = [
    'build_element_graph',
    'compute_in_out_degree',
    'compute_unweighted_depth',
    'compute_weighted_depth',
    'compute_reachability',
    'compute_downstream_count',
    'find_terminal_elements',
    'find_requested_targets',
    'compute_reverse_reachability_from_targets',
    'compute_dominators',
    'compute_critical_path',
    'compute_slack',
    'analyze_graph',
]
