"""UX-1274: the builder sweep's range, its published curve, and the knee-or-edge wording."""

import collections
from typing import Optional

from . import shown as qty
from .plural import plural

#: How far past the larger of builders and host cores the sweep reaches.
SWEEP_HEADROOM = 2
#: The most replays one analyze pays for the curve.
SWEEP_CAP = 32


def graph_width(signals: Optional[dict]) -> Optional[int]:
    """The widest dependency stage, `graph-width`'s own reading of `unweighted_depth`."""
    depth = (signals or {}).get('unweighted_depth') or {}
    return max(collections.Counter(depth.values()).values()) if depth else None


def sweep_top(builders: int, host_cores: int, width: Optional[int]) -> int:
    """min(max(builders x 2, host cores x 2, graph width), cap)."""
    return min(max(builders * SWEEP_HEADROOM, host_cores * SWEEP_HEADROOM, width or 0), SWEEP_CAP)


def curve(sweeps: list, resource: str = 'PROCESS') -> list:
    """Replayed wall per swept builder count, from 1 builder up, as one ordered series."""
    return [row['makespan_us'] for row in sorted(sweeps, key=lambda row: row['capacity'][resource])]


def at_edge(knee: Optional[int], top: Optional[int]) -> bool:
    return bool(knee and top and knee >= top)


def knee_reason(knee: int, top: Optional[int]) -> str:
    """The graph row's reason: a knee, or no knee within the range swept."""
    if at_edge(knee, top):
        return f"no knee within {plural(top, 'builder')}: the replay still gains at the top of the range swept"
    return f"the sweep's knee is at {plural(knee, 'builder')}"


def replayed_clause(recommendation: dict) -> str:
    """`the replay puts K builders at W (replayed, no contention)`, at the knee or the range's top; '' with no curve."""
    walls = recommendation.get('sweep') or []
    graph = next((c for c in recommendation.get('constraints') or [] if c.get('name') == 'graph'), None)
    if not walls or not graph:
        return ''
    count = min(graph['allows'], len(walls))
    return f"the replay puts {plural(count, 'builder')} at {qty.duration(walls[count - 1])} (replayed, no contention)"


def replayed_delta_us(recommendation: dict) -> Optional[int]:
    """The replayed wall at this run's builders minus at the clause's count; `None` without both points or a gain."""
    walls = recommendation.get('sweep') or []
    graph = next((c for c in recommendation.get('constraints') or [] if c.get('name') == 'graph'), None)
    builders = recommendation.get('builders')
    if not graph or not builders or builders > len(walls):
        return None
    delta = walls[builders - 1] - walls[min(graph['allows'], len(walls)) - 1]
    return delta if delta > 0 else None
