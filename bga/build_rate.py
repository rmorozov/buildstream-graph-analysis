"""UX-1276: the project's declared build rate, `.bga/config`'s hand-edited `builds_per_day`, or `None`."""

from typing import Optional

from . import run_store

CONFIG_KEY = "builds_per_day"
SOURCE = "declared in .bga/config"


def build_rate(project: str) -> Optional[dict]:
    """`{per_day, source}` for a positive declared rate; `None` when undeclared or not a number."""
    declared = run_store.read_config(project).get(CONFIG_KEY)
    if isinstance(declared, bool) or not isinstance(declared, (int, float)) or declared <= 0:
        return None
    return {"per_day": declared, "source": SOURCE}


def agent_hours_per_day(saving_us: float, per_day: float) -> float:
    """A saving of one build, in agent-hours a day at the declared rate."""
    return saving_us / 1e6 * per_day / 3600
