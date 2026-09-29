"""UX-1013: admission's ranking source when no `--plan` was given - the
build time BuildStream's own local cache records per element (`bst
artifact log`, `CHUNK` elements per call), longest first, falling
back to the tracer's structural ranking when no log parses. Stdlib
only, like the rest of this package."""

import re
import subprocess
import sys
from typing import Callable, Optional

CHUNK = 200
_CACHED_SUCCESS = re.compile(r"\[(\d+):(\d{2}):(\d{2})\]\s+SUCCESS\s+(\S+):\s+Running commands")


def parse_cached_build_seconds(text: str, element: str) -> Optional[float]:
    """The elapsed stamp on the last `[HH:MM:SS] SUCCESS <element>:
    Running commands` line - `None` when no such line names *this*
    element."""
    seconds = None
    for match in _CACHED_SUCCESS.finditer(text):
        if match.group(4) == element:
            hours, minutes, secs = (int(match.group(i)) for i in (1, 2, 3))
            seconds = float(hours * 3600 + minutes * 60 + secs)
    return seconds


def read_cached_build_log(argv: list[str], project_dir: str) -> Optional[str]:
    """One `bst artifact log` run; `None` on a timeout, an OS error or a
    non-zero exit."""
    try:
        proc = subprocess.run(argv, cwd=project_dir, capture_output=True, text=True, check=False, timeout=120)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def cached_log_ranking(
    structural: dict[str, float], read_log: Callable[[list[str]], Optional[str]]
) -> tuple[Optional[dict[str, float]], int, int]:
    """`(slack_plan, tried, parsed)` - one `read_log(chunk)` per `CHUNK`
    elements, a failed chunk left unparsed; longest cached build first, ties
    and unparsed elements in `structural` order, every unparsed one
    below every parsed one; `None` when none parsed."""
    names, durations = list(structural), {}
    for start in range(0, len(names), CHUNK):
        chunk = names[start : start + CHUNK]
        text = read_log(chunk) or ""
        for element in chunk:
            seconds = parse_cached_build_seconds(text, element)
            if seconds is not None:
                durations[element] = seconds
    if not durations:
        return None, len(structural), 0
    parsed = sorted(durations, key=lambda e: (-durations[e], structural[e], e))
    rest = sorted((e for e in structural if e not in durations), key=lambda e: (structural[e], e))
    return {e: float(i) for i, e in enumerate(parsed + rest)}, len(structural), len(durations)


def rank_admission(
    plan: Optional[dict], structural: Optional[dict], read_log: Callable[[list[str]], Optional[str]]
) -> tuple[Optional[dict], Optional[str]]:
    """`(slack_plan, ranking_source)`: a `--plan`, else the cached logs,
    else `structural`, else nothing - printing which ranking ran."""
    if plan is not None:
        return plan, "plan"
    if not structural:
        return None, None
    cached, tried, parsed = cached_log_ranking(structural, read_log)
    if cached is None:
        print(f"admission ranking: structural (cached logs: 0 of {tried} parsed)", file=sys.stderr)
        return structural, "structural"
    top = ", ".join(sorted(cached, key=cached.__getitem__)[:3])
    print(f"admission ranking: cached-logs ({parsed} of {tried} parsed) | first: {top}", file=sys.stderr)
    return cached, "cached-logs"
