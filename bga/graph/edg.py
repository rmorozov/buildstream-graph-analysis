"""
Static dependency graph analysis.

Implements Part 5: Static Dependency Graph including:
- Element Dependency Graph (EDG)
- Task graph
- Structural metrics (depth, reachability, dominators, critical path)
"""

import logging
from typing import Dict, List, Sequence, Set, Tuple, Optional
from collections import defaultdict, deque

from ..ingest.models import Graph, NormalizedTask
from ..exceptions import AnalysisError

logger = logging.getLogger(__name__)


def build_element_graph(
    graph: Graph,
    exclude_dependency_types: Optional[Set[str]] = None,
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Build adjacency lists for the Element Dependency Graph.

    Args:
        graph: Input graph with elements and dependencies
        exclude_dependency_types: dependency_type values to omit from the
            adjacency lists (P4-11). None (the default) includes every
            edge, unfiltered - the right choice for purely structural
            queries (reachability, blast radius, leaf/deferrability, Part
            24/25), which must count a `runtime`-only edge just as much
            as a `build`-type one. Pass `{"runtime"}` for the *gating*
            chain specifically (compute_critical_path/compute_slack, Part
            14.1) - a `runtime`-only edge doesn't actually constrain
            build scheduling (BuildStream: "an element's runtime
            dependencies are not available to the element at build
            time"), so including it there would inflate T∞,observed
            past what Part 14.1 itself claims it certifies ("no schedule
            ... can complete faster than this value" - not true if the
            value counts a non-gating edge as if it were gating).

    Returns:
        Tuple of (predecessors, successors) adjacency lists
    """
    predecessors: Dict[str, List[str]] = defaultdict(list)
    successors: Dict[str, List[str]] = defaultdict(list)

    for dep in graph.dependencies:
        if exclude_dependency_types and dep.dependency_type in exclude_dependency_types:
            continue
        predecessors[dep.successor].append(dep.predecessor)
        successors[dep.predecessor].append(dep.successor)

    return dict(predecessors), dict(successors)


def compute_in_out_degree(
    graph: Graph,
    exclude_dependency_types: Optional[Set[str]] = None,
) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    Compute in-degree and out-degree for all elements (Part 5.3).

    Args:
        graph: Input graph
        exclude_dependency_types: see build_element_graph - must be
            passed identically wherever this and build_element_graph are
            used together for the same topological traversal (P4-11), or
            the in-degree counts won't match what the (possibly
            differently-filtered) adjacency lists actually decrement
            during the sort, breaking it silently.

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
        if exclude_dependency_types and dep.dependency_type in exclude_dependency_types:
            continue
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

    Only `build`-type edges gate this traversal (P4-11) - Part 14.1
    itself defines T∞,observed as a *certified* claim ("no schedule with
    unlimited relevant capacity can complete faster than this value"),
    which would be false if a `runtime`-only edge (not actually
    constraining build scheduling - BuildStream's own semantics) were
    counted as if it gated ordering: a real schedule could beat that
    inflated value by simply not waiting on it.

    Args:
        graph: Input graph
        task_durations: Dict mapping element uid to duration in microseconds

    Returns:
        Tuple of (critical_path_length, list of element UIDs on critical path)
    """
    predecessors, successors = build_element_graph(graph, exclude_dependency_types={"runtime"})
    in_degree, _ = compute_in_out_degree(graph, exclude_dependency_types={"runtime"})
    
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

    Must use the same gating-only (`build`-type) graph traversal as
    compute_critical_path (P4-11) - `critical_path_length` was computed
    over that filtered graph, so computing earliest/latest start here
    over a *different* (unfiltered) graph would produce internally
    inconsistent, meaningless slack values.

    Args:
        graph: Input graph
        task_durations: Dict mapping element uid to duration
        critical_path_length: Length of critical path

    Returns:
        Dict mapping element uid to slack in microseconds
    """
    predecessors, successors = build_element_graph(graph, exclude_dependency_types={"runtime"})
    in_degree, _ = compute_in_out_degree(graph, exclude_dependency_types={"runtime"})
    
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


# UX-70: how many candidates to evaluate. Each costs one longest-path
# recomputation, which is linear in the graph, so this is O(N * (V+E)).
# Bounded because the question only makes sense for elements a user might
# actually work on, and an unbounded sweep on a 10,000-element graph
# would be a surprising cost inside `analyze`.
REALIZABLE_SAVING_CANDIDATES = 8


def compute_realizable_savings(
    graph: Graph,
    durations: Dict[str, int],
    candidates: List[str],
) -> Dict[str, int]:
    """UX-70: what the critical path would actually lose if each
    candidate became instant.

    Share of the critical path answers "what is the chain made of". It
    does not answer "what happens if I change it", because it holds the
    rest of the graph fixed — and on a real `freedesktop-sdk` capture
    **97 of 126 elements have zero slack**, so the rest of the graph does
    not stay fixed at all. Measured there: `components/python3.bst` holds
    17.7% of the path and eliminating it entirely saves 114s of 3610s,
    **3.2%**, because a near-tie chain takes over the moment it shrinks.

    Zeroing rather than halving is deliberate: it is the *upper bound* on
    what optimizing this element can ever be worth, which is the number
    that stops a user spending a week for a minute. A saving far below
    the element's own duration is the signal — it says the graph, not
    this element, is what binds.

    Returns `{element_uid: saving_us}` for the candidates evaluated.
    """
    if not candidates:
        return {}
    baseline, _path = compute_critical_path(graph, durations)
    savings: Dict[str, int] = {}
    for uid in candidates[:REALIZABLE_SAVING_CANDIDATES]:
        if not durations.get(uid):
            continue
        hypothetical = dict(durations)
        hypothetical[uid] = 0
        shortened, _ = compute_critical_path(graph, hypothetical)
        savings[uid] = max(0, baseline - shortened)
    return savings


# UX-74: how many fix-and-recapture cycles the report projects ahead.
# Each step costs one longest-path recompute per candidate on the current
# path - 0.40 ms each on a real 126-element graph - against the ~60
# minutes a real re-capture costs. Bounded anyway: a projection five
# hypothetical fixes deep is arithmetic, not advice.
OPTIMIZATION_HORIZON_STEPS = 5


def compute_joint_saving(
    graph: Graph,
    durations: Dict[str, int],
    elements: Sequence[str],
) -> int:
    """What the build would lose if *all* of `elements` became instant.

    Not the sum of their individual savings, and not assumed to be: on a
    chain the savings compose, on parallel branches they take a maximum,
    and which of those holds is a property of this graph that only the
    simulation can answer (`UX-74`). Measured on a real
    `freedesktop-sdk` capture: the top three are worth 2605.8s together,
    exactly the sum - while `cmake-stage1` and `git-minimal`, on
    different chains, are worth 1569.8s together, exactly the larger of
    the two alone.
    """
    if not elements:
        return 0
    baseline, _path = compute_critical_path(graph, durations)
    hypothetical = dict(durations)
    for uid in elements:
        hypothetical[uid] = 0
    shortened, _ = compute_critical_path(graph, hypothetical)
    return max(0, baseline - shortened)


def compute_optimization_horizon(
    graph: Graph,
    durations: Dict[str, int],
    excluded: Optional[Set[str]] = None,
    steps: int = OPTIMIZATION_HORIZON_STEPS,
) -> List[dict]:
    """What becomes binding after each fix, projected from one capture.

    A user learns one element per capture today, and on a graph where
    77% of elements have zero slack the chain re-forms the moment
    anything shrinks - so the second finding costs another full build.
    Every number here is a longest-path recompute the tool already
    performs, and the whole projection runs in milliseconds against the
    ~60 minutes a real re-capture costs.

    Greedy by realizable saving at each step, which is the order a user
    would actually work in: the element worth most *now*, then the
    element worth most once that is done. `entering` names elements that
    were not on the previous step's critical path and are on this one -
    the latent heavies, worth nothing today and binding two fixes from
    now, which appear in no report the tool otherwise produces.

    `excluded` is the structural set: a `stack` or `import` has no build
    commands to make faster, so "fix it" is not a thing a reader can do
    (`UX-34`).

    This is a structural projection over *this run's* measured durations.
    "Fixed" means the element becomes instant - the same convention
    `compute_realizable_savings` and `best_case_speedup` already use - and
    it assumes nothing else about the build changes. It is not a
    forecast, and the caller is expected to say so.
    """
    excluded = excluded or set()
    baseline, path = compute_critical_path(graph, durations)
    if baseline <= 0:
        return []
    remaining = dict(durations)
    on_path = set(path)
    horizon: List[dict] = []
    for _step in range(max(0, steps)):
        candidates = [
            uid for uid in path
            if remaining.get(uid) and uid not in excluded
        ]
        if not candidates:
            break
        savings = compute_realizable_savings(
            graph, remaining, sorted(candidates, key=lambda u: -remaining[u])
        )
        best = max(savings, key=lambda u: savings[u], default=None)
        if best is None or savings[best] <= 0:
            break
        remaining[best] = 0
        makespan, path = compute_critical_path(graph, remaining)
        entering = [
            uid for uid in path
            if uid not in on_path and remaining.get(uid) and uid not in excluded
        ]
        on_path |= set(path)
        horizon.append({
            'element_uid': best,
            'saving_us': savings[best],
            'makespan_after_us': int(makespan),
            'cumulative_saving_us': int(baseline - makespan),
            # UX-74: the latent heavies. Sorted by their own duration,
            # because "which of these should I care about" is a size
            # question at the moment they appear.
            'entering': sorted(entering, key=lambda u: -remaining[u]),
        })
    return horizon


# UX-74: an off-path element below this share of the build is not a
# latent anything - it is rounding. `UX-65`'s own floor, reused.
LATENT_HEAVY_SHARE = 0.01

LATENT_HEAVIES_SHOWN = 5

# UX-74: how many of the horizon's steps the joint-saving figure covers.
# Three is what a reader can hold at once and what the report already
# ranks; the question "do these compose" is only interesting for a set
# small enough to actually plan around.
JOINT_SAVING_SET_SIZE = 3


def compute_latent_heavies(
    durations: Dict[str, int],
    critical_path: Sequence[str],
    total_us: int,
    excluded: Optional[Set[str]] = None,
    floor_share: float = LATENT_HEAVY_SHARE,
) -> List[dict]:
    """Heavy elements that are on no critical path and in no ranking.

    Their realizable saving today is genuinely 0, so every ranking the
    report produces is right to place them last - and that is exactly why
    they are invisible. On a real `freedesktop-sdk` capture
    `components/_private/git-minimal.bst` (547.7s) is the **4th heaviest
    element in the whole build** and `components/icu.bst` (430.8s) the
    6th, and neither appears anywhere in the report (`UX-74`).

    They are not a to-do list. They are the floor the chain is being
    shortened towards: fixing the critical path can only help until one
    of these becomes the constraint.
    """
    excluded = excluded or set()
    on_path = set(critical_path)
    floor = total_us * floor_share if total_us else 0
    latent = [
        {'element_uid': uid, 'duration_us': dur}
        for uid, dur in durations.items()
        if uid not in on_path and uid not in excluded and dur >= floor and dur > 0
    ]
    return sorted(latent, key=lambda e: -e['duration_us'])[:LATENT_HEAVIES_SHOWN]


def compute_element_durations(tasks: List[NormalizedTask]) -> Dict[str, int]:
    """The single per-element duration definition: the **longest** task
    the element ran.

    Every path computation in `bga` - `compute_critical_path`
    (`T∞,observed`, Part 14.1), `compute_slack`, `compute_weighted_depth`,
    and the whole structural plane - collapses an element's several tasks
    into one number, and they must all collapse it the *same* way or two
    quantities the report presents as the same thing disagree. `UX-53`
    is what happens when they do not.

    Why the longest task rather than their sum: `T∞,observed` is a
    *certified* claim - "no schedule with unlimited relevant capacity can
    complete faster than this value" - so it must never overstate. An
    element genuinely occupies at least its longest task, whatever the
    scheduler does, which makes the maximum safe. The sum is not: under
    unlimited capacity BuildStream's fetch queue runs an element's FETCH
    concurrently with other elements' builds, so `FETCH + BUILD` is not
    forced to be sequential on the chain, and charging both to the path
    can claim a floor a real schedule beats.

    Note what this deliberately does *not* settle: whether a long FETCH
    should contribute to a *build* chain's floor at all. That is a
    modelling question about Part 14.1, recorded in
    `docs/scenarios/UX-53-*.md`, not something to decide silently here.
    """
    durations: Dict[str, int] = {}
    for task in tasks:
        elem_uid = task.task_key.element_uid
        durations[elem_uid] = max(durations.get(elem_uid, 0), task.dur_us)
    return durations


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
    task_durations = compute_element_durations(tasks)

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
