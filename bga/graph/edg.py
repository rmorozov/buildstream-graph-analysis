"""
Static dependency graph analysis.

Implements Part 5: Static Dependency Graph including:
- Element Dependency Graph (EDG)
- Task graph
- Structural metrics (depth, reachability, dominators, critical path)
"""

import logging
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque

from ..ingest.models import Graph, Element, NormalizedTask, DependencyEdge
from ..exceptions import AnalysisError

logger = logging.getLogger(__name__)


def build_element_graph(graph: Graph) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Build adjacency lists for the Element Dependency Graph.
    
    Args:
        graph: Input graph with elements and dependencies
        
    Returns:
        Tuple of (predecessors, successors) adjacency lists
    """
    predecessors: Dict[str, List[str]] = defaultdict(list)
    successors: Dict[str, List[str]] = defaultdict(list)
    
    for dep in graph.dependencies:
        predecessors[dep.successor].append(dep.predecessor)
        successors[dep.predecessor].append(dep.successor)
    
    return dict(predecessors), dict(successors)


def compute_in_out_degree(
    graph: Graph,
) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    Compute in-degree and out-degree for all elements (Part 5.3).
    
    Args:
        graph: Input graph
        
    Returns:
        Tuple of (in_degree, out_degree) dictionaries
    """
    in_degree: Dict[str, int] = defaultdict(int)
    out_degree: Dict[str, int] = defaultdict(int)
    
    # Initialize all elements with zero degree
    for elem in graph.elements:
        in_degree[elem.uid] = 0
        out_degree[elem.uid] = 0
    
    for dep in graph.dependencies:
        out_degree[dep.predecessor] += 1
        in_degree[dep.successor] += 1
    
    return dict(in_degree), dict(out_degree)


def compute_unweighted_depth(graph: Graph) -> Dict[str, int]:
    """
    Compute unweighted depth for all elements (Part 5.3, 14.2).
    
    Depth is the longest path (in edges) from any source to the element.
    Sources have depth 0.
    
    Uses topological order via Kahn's algorithm.
    
    Args:
        graph: Input graph
        
    Returns:
        Dict mapping element uid to unweighted depth
        
    Raises:
        ValueError: If the graph contains a cycle
    """
    _, successors = build_element_graph(graph)
    in_degree, _ = compute_in_out_degree(graph)

    depth: Dict[str, int] = {}

    # Initialize sources with depth 0
    queue = deque()
    for elem_uid, deg in in_degree.items():
        if deg == 0:
            depth[elem_uid] = 0
            queue.append(elem_uid)

    processed_count = 0

    # Process in topological order - O(N+E): each edge is visited exactly
    # once via the precomputed successors adjacency list, instead of
    # rescanning the full flat graph.dependencies list per dequeued node.
    while queue:
        current = queue.popleft()
        current_depth = depth[current]
        processed_count += 1

        for successor in successors.get(current, []):
            # Update depth if this path is longer
            if successor not in depth:
                depth[successor] = 0
            depth[successor] = max(depth[successor], current_depth + 1)

            in_degree[successor] -= 1
            if in_degree[successor] == 0:
                queue.append(successor)

    # Check for cycles: if we didn't process all elements, there's a cycle
    if processed_count != len(graph.elements):
        # Find which elements are in cycles
        unprocessed = [elem.uid for elem in graph.elements if elem.uid not in depth]
        logger.error("Cycle detected involving elements: %s", ', '.join(unprocessed))
        raise AnalysisError(f"Graph contains a cycle involving elements: {', '.join(unprocessed)}")

    return depth


def compute_weighted_depth(
    graph: Graph,
    task_durations: Dict[str, int],
) -> Dict[str, int]:
    """
    Compute weighted depth for all elements.
    
    Weighted depth is the longest path (in duration) from any source.
    
    Args:
        graph: Input graph
        task_durations: Dict mapping element uid to duration in microseconds
        
    Returns:
        Dict mapping element uid to weighted depth (earliest finish time)
        
    Raises:
        ValueError: If the graph contains a cycle
    """
    _, successors = build_element_graph(graph)
    in_degree, _ = compute_in_out_degree(graph)

    # earliest_finish[elem] = earliest time elem can finish
    earliest_finish: Dict[str, int] = {}

    # Initialize sources
    queue = deque()
    processed_count = 0
    for elem_uid, deg in in_degree.items():
        if deg == 0:
            earliest_finish[elem_uid] = task_durations.get(elem_uid, 0)
            queue.append(elem_uid)

    # Process in topological order - O(N+E), see compute_unweighted_depth.
    while queue:
        current = queue.popleft()
        current_finish = earliest_finish[current]
        processed_count += 1

        for successor in successors.get(current, []):
            if successor not in earliest_finish:
                earliest_finish[successor] = 0

            # Successor can start when all predecessors finish
            earliest_start = current_finish
            earliest_finish[successor] = max(
                earliest_finish[successor],
                earliest_start + task_durations.get(successor, 0)
            )

            in_degree[successor] -= 1
            if in_degree[successor] == 0:
                queue.append(successor)
    
    # Check for cycles
    if processed_count != len(graph.elements):
        unprocessed = [elem.uid for elem in graph.elements if elem.uid not in earliest_finish]
        logger.error("Cycle detected involving elements: %s", ', '.join(unprocessed))
        raise AnalysisError(f"Graph contains a cycle involving elements: {', '.join(unprocessed)}")
    
    return earliest_finish


def compute_reachability(graph: Graph) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """
    Compute reachability sets for all elements (Part 5.3).
    
    For each element:
        - reachable_downstream: all elements that can be reached from it
        - reachable_upstream: all elements that can reach it
    
    Uses reverse traversal with memoization for efficiency.
    
    Args:
        graph: Input graph
        
    Returns:
        Tuple of (reachable_downstream, reachable_upstream) dictionaries
    """
    _, successors = build_element_graph(graph)
    predecessors, _ = build_element_graph(graph)
    
    # Compute downstream reachability using reverse topological order
    reachable_downstream: Dict[str, Set[str]] = {}
    reachable_upstream: Dict[str, Set[str]] = {}
    
    # Get topological order
    in_degree, _ = compute_in_out_degree(graph)
    topo_order = []
    queue = deque([uid for uid, deg in in_degree.items() if deg == 0])
    temp_in_degree = dict(in_degree)
    
    while queue:
        current = queue.popleft()
        topo_order.append(current)
        
        for succ in successors.get(current, []):
            temp_in_degree[succ] -= 1
            if temp_in_degree[succ] == 0:
                queue.append(succ)
    
    # Process in reverse topological order for downstream
    for elem_uid in reversed(topo_order):
        reachable = set()
        for succ in successors.get(elem_uid, []):
            reachable.add(succ)
            reachable.update(reachable_downstream.get(succ, set()))
        reachable_downstream[elem_uid] = reachable
    
    # Process in topological order for upstream
    for elem_uid in topo_order:
        reachable = set()
        for pred in predecessors.get(elem_uid, []):
            reachable.add(pred)
            reachable.update(reachable_upstream.get(pred, set()))
        reachable_upstream[elem_uid] = reachable
    
    # Handle elements not in topological order (disconnected or cycles)
    for elem in graph.elements:
        if elem.uid not in reachable_downstream:
            reachable_downstream[elem.uid] = set()
        if elem.uid not in reachable_upstream:
            reachable_upstream[elem.uid] = set()
    
    return reachable_downstream, reachable_upstream


def compute_downstream_count(graph: Graph) -> Dict[str, int]:
    """
    Compute downstream count (blast radius) for all elements (Part 25).
    
    Args:
        graph: Input graph
        
    Returns:
        Dict mapping element uid to count of reachable downstream elements
    """
    reachable_downstream, _ = compute_reachability(graph)
    
    return {
        uid: len(reachable)
        for uid, reachable in reachable_downstream.items()
    }


def find_terminal_elements(graph: Graph) -> Set[str]:
    """
    Find terminal elements (elements with no successors).
    
    Used for leaf classification (Part 24).
    
    Args:
        graph: Input graph
        
    Returns:
        Set of terminal element UIDs
    """
    _, successors = build_element_graph(graph)
    
    terminals = set()
    for elem in graph.elements:
        if elem.uid not in successors or not successors[elem.uid]:
            terminals.add(elem.uid)
    
    return terminals


def find_requested_targets(graph: Graph) -> Set[str]:
    """
    Find requested target elements.
    
    Args:
        graph: Input graph
        
    Returns:
        Set of requested target element UIDs
    """
    return {elem.uid for elem in graph.elements if elem.requested_target}


def compute_reverse_reachability_from_targets(
    graph: Graph,
    targets: Optional[Set[str]] = None,
) -> Set[str]:
    """
    Compute elements reachable from any requested target (Part 24.2).
    
    Uses reverse reachability from targets.
    
    Args:
        graph: Input graph
        targets: Set of target element UIDs (defaults to requested_target elements)
        
    Returns:
        Set of element UIDs reachable from targets
    """
    if targets is None:
        targets = find_requested_targets(graph)
    
    if not targets:
        return set()
    
    predecessors, _ = build_element_graph(graph)
    reachable = set(targets)
    queue = deque(targets)
    
    while queue:
        current = queue.popleft()
        for pred in predecessors.get(current, []):
            if pred not in reachable:
                reachable.add(pred)
                queue.append(pred)
    
    return reachable


def compute_dominators(graph: Graph, start_elements: Optional[Set[str]] = None) -> Dict[str, Set[str]]:
    """
    Compute dominators for all elements (Part 5.3).
    
    An element A dominates B if every path from sources to B goes through A.
    
    Uses iterative dataflow algorithm.
    
    Args:
        graph: Input graph
        start_elements: Source elements (defaults to elements with in_degree 0)
        
    Returns:
        Dict mapping element uid to its set of dominators
    """
    predecessors, successors = build_element_graph(graph)
    in_degree, _ = compute_in_out_degree(graph)

    if start_elements is None:
        start_elements = {uid for uid, deg in in_degree.items() if deg == 0}

    # Initialize dominators
    dom: Dict[str, Set[str]] = {}

    # Topological sort - O(N+E), see compute_unweighted_depth.
    topo_order = []
    queue = deque(start_elements)
    temp_in_degree = {uid: deg for uid, deg in in_degree.items()}

    for start in start_elements:
        dom[start] = {start}

    while queue:
        current = queue.popleft()
        topo_order.append(current)

        for successor in successors.get(current, []):
            temp_in_degree[successor] -= 1
            if temp_in_degree[successor] == 0:
                queue.append(successor)
    
    # Iterative dominator computation
    changed = True
    while changed:
        changed = False
        for elem_uid in topo_order:
            if elem_uid in start_elements:
                continue
            
            preds = predecessors.get(elem_uid, [])
            if not preds:
                continue
            
            # Intersection of all predecessor dominators
            new_dom = set(dom.get(preds[0], {preds[0]}))
            for pred in preds[1:]:
                new_dom &= dom.get(pred, {pred})
            
            # Add self
            new_dom.add(elem_uid)
            
            if elem_uid not in dom or dom[elem_uid] != new_dom:
                dom[elem_uid] = new_dom
                changed = True
    
    return dom


def compute_critical_path(
    graph: Graph,
    task_durations: Dict[str, int],
) -> Tuple[int, List[str]]:
    """
    Compute observed critical path (Part 5.3, 14.1).
    
    The critical path is the longest weighted path through the graph.
    T∞,observed = weighted longest path using observed durations
    
    Args:
        graph: Input graph
        task_durations: Dict mapping element uid to duration in microseconds
        
    Returns:
        Tuple of (critical_path_length, list of element UIDs on critical path)
    """
    predecessors, successors = build_element_graph(graph)
    in_degree, _ = compute_in_out_degree(graph)
    
    # earliest_finish[elem] = earliest time elem can finish
    earliest_finish: Dict[str, int] = {}
    # predecessor_on_critical[elem] = predecessor that determines earliest finish
    pred_on_critical: Dict[str, Optional[str]] = {}
    
    # Topological sort with earliest finish computation
    queue = deque()
    for elem_uid, deg in in_degree.items():
        if deg == 0:
            earliest_finish[elem_uid] = task_durations.get(elem_uid, 0)
            pred_on_critical[elem_uid] = None
            queue.append(elem_uid)
    
    temp_in_degree = dict(in_degree)
    topo_order = []
    
    while queue:
        current = queue.popleft()
        topo_order.append(current)
        
        for succ in successors.get(current, []):
            # Update earliest finish for successor
            potential_finish = earliest_finish[current] + task_durations.get(succ, 0)
            
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
        return (0, [])
    
    # Find the terminal element with maximum finish time
    critical_length = 0
    critical_end = None
    
    for elem_uid in earliest_finish:
        # Check if this is a terminal element
        if elem_uid not in successors or not successors[elem_uid]:
            if earliest_finish[elem_uid] > critical_length:
                critical_length = earliest_finish[elem_uid]
                critical_end = elem_uid
    
    # If no terminal found, use maximum overall
    if critical_end is None:
        critical_length = max(earliest_finish.values())
        critical_end = max(earliest_finish, key=earliest_finish.get)
    
    # Reconstruct critical path by backtracking
    critical_path = []
    current = critical_end
    while current is not None:
        critical_path.append(current)
        current = pred_on_critical.get(current)
    
    critical_path.reverse()
    
    return (critical_length, critical_path)


def compute_slack(
    graph: Graph,
    task_durations: Dict[str, int],
    critical_path_length: int,
) -> Dict[str, int]:
    """
    Compute slack for all elements (Part 5.3).
    
    Slack = latest_start - earliest_start
    Elements on critical path have zero slack.
    
    Args:
        graph: Input graph
        task_durations: Dict mapping element uid to duration
        critical_path_length: Length of critical path
        
    Returns:
        Dict mapping element uid to slack in microseconds
    """
    predecessors, successors = build_element_graph(graph)
    in_degree, _ = compute_in_out_degree(graph)
    
    # Compute earliest start times
    earliest_start: Dict[str, int] = {}
    queue = deque()
    for elem_uid, deg in in_degree.items():
        if deg == 0:
            earliest_start[elem_uid] = 0
            queue.append(elem_uid)
    
    temp_in_degree = dict(in_degree)
    topo_order = []
    
    while queue:
        current = queue.popleft()
        topo_order.append(current)
        
        for succ in successors.get(current, []):
            potential_start = earliest_start[current] + task_durations.get(current, 0)
            if succ not in earliest_start:
                earliest_start[succ] = potential_start
            else:
                earliest_start[succ] = max(earliest_start[succ], potential_start)
            
            temp_in_degree[succ] -= 1
            if temp_in_degree[succ] == 0:
                queue.append(succ)
    
    # Compute latest start times (reverse pass)
    latest_start: Dict[str, int] = {}
    
    # Initialize terminal elements
    for elem_uid in reversed(topo_order):
        if elem_uid not in successors or not successors[elem_uid]:
            latest_start[elem_uid] = critical_path_length - task_durations.get(elem_uid, 0)
    
    # Backward pass
    for elem_uid in reversed(topo_order):
        if elem_uid not in latest_start:
            latest_start[elem_uid] = float('inf')
        
        for succ in successors.get(elem_uid, []):
            if succ in latest_start:
                potential_latest = latest_start[succ] - task_durations.get(elem_uid, 0)
                latest_start[elem_uid] = min(latest_start[elem_uid], potential_latest)
    
    # Compute slack
    slack = {}
    for elem_uid in earliest_start:
        if elem_uid in latest_start and latest_start[elem_uid] != float('inf'):
            slack[elem_uid] = latest_start[elem_uid] - earliest_start[elem_uid]
        else:
            slack[elem_uid] = 0
    
    return slack


def analyze_graph(
    graph: Graph,
    tasks: List[NormalizedTask],
) -> dict:
    """
    Perform comprehensive graph analysis.
    
    Args:
        graph: Input graph
        tasks: List of normalized tasks
        
    Returns:
        Dict containing all graph metrics
    """
    # Build task duration map
    task_durations: Dict[str, int] = {}
    for task in tasks:
        elem_uid = task.task_key.element_uid
        if elem_uid not in task_durations:
            task_durations[elem_uid] = task.dur_us
        else:
            task_durations[elem_uid] = max(task_durations[elem_uid], task.dur_us)
    
    # Compute all metrics
    in_degree, out_degree = compute_in_out_degree(graph)
    unweighted_depth = compute_unweighted_depth(graph)
    weighted_depth = compute_weighted_depth(graph, task_durations)
    reachable_downstream, reachable_upstream = compute_reachability(graph)
    downstream_count = compute_downstream_count(graph)
    terminals = find_terminal_elements(graph)
    requested_targets = find_requested_targets(graph)
    reachable_from_targets = compute_reverse_reachability_from_targets(graph)
    dominators = compute_dominators(graph)
    critical_path_length, critical_path = compute_critical_path(graph, task_durations)
    slack = compute_slack(graph, task_durations, critical_path_length)
    
    return {
        'graph': graph,
        'in_degree': in_degree,
        'out_degree': out_degree,
        'unweighted_depth': unweighted_depth,
        'weighted_depth': weighted_depth,
        'reachable_downstream': {k: list(v) for k, v in reachable_downstream.items()},
        'reachable_upstream': {k: list(v) for k, v in reachable_upstream.items()},
        'downstream_count': downstream_count,
        'terminal_elements': list(terminals),
        'requested_targets': list(requested_targets),
        'reachable_from_targets': list(reachable_from_targets),
        'dominators': {k: list(v) for k, v in dominators.items()},
        'critical_path_length': critical_path_length,
        'critical_path': critical_path,
        'slack': slack,
        'task_durations': task_durations,
    }
