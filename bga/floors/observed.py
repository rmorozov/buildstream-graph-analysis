"""
T-infinity,observed - the observed structural floor (Part 14.1): the
weighted longest path through the graph using observed durations. The
actual longest-path algorithm lives in bga/graph/edg.py::compute_critical_path
(reused, not duplicated, for the advisory cold floor too - Part 15.1);
this module just names the floor concept and extracts it from an
already-computed analyze_graph(...) result.
"""


def compute_t_infinity_observed(graph_analysis: dict) -> int:
    """Extract T-infinity,observed from a pre-computed analyze_graph(...) result."""
    return graph_analysis['critical_path_length']
