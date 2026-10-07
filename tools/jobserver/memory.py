"""UX-1134: the pool's memory gate with no plan - measured RSS, not a
`--plan`'s `peak_rss_bytes`, decides whether one more token fits.

Finished peaks are the hook's END lines' `maxrss_kb` per `element=`,
read from the live trace log from a saved offset; live RSS is a
`/proc/*/stat` walk of each running sandbox's host-pid descendants,
the pid the shim writes into its decision row. Stdlib only.
"""

import json
import os
from typing import Callable, Optional

try:
    _PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")
except (ValueError, OSError, AttributeError):  # pragma: no cover
    _PAGE_SIZE = 4096

# Jobs' worth of memory kept free past the one being added: at 11 x 2.8 GB on 31 GB cc1 was OOM-killed.
# `bga.correlate.MEMORY_RESERVE_JOBS` is the advice's copy; a guard holds them equal.
MEMORY_RESERVE_JOBS = 1


def _end_fields(line: str) -> Optional[tuple[str, int]]:
    """`(element, maxrss_bytes)` from one hook END line, else `None`."""
    if not line.startswith("END "):
        return None
    head = line.split(" cmd=", 1)[0]
    fields = dict(token.split("=", 1) for token in head.split(" ")[1:] if "=" in token)
    try:
        return fields["element"], int(fields["maxrss_kb"]) * 1024
    except (KeyError, ValueError):
        return None


def _proc_table(proc_root: str) -> dict[int, tuple[int, int]]:
    """`{pid: (ppid, rss_bytes)}` over every readable `<proc_root>/<pid>/stat`."""
    table: dict[int, tuple[int, int]] = {}
    try:
        names = os.listdir(proc_root)
    except OSError:
        return table
    for name in names:
        if not name.isdigit():
            continue
        try:
            with open(os.path.join(proc_root, name, "stat"), encoding="utf-8", errors="replace") as handle:
                stat = handle.read()
            fields = stat[stat.rindex(")") + 2 :].split()
            table[int(name)] = (int(fields[1]), int(fields[21]) * _PAGE_SIZE)
        except (OSError, ValueError, IndexError):
            continue
    return table


def _descendants(root: int, children: dict[int, list[int]]) -> list[int]:
    found, stack = [], list(children.get(root, ()))
    while stack:
        pid = stack.pop()
        found.append(pid)
        stack.extend(children.get(pid, ()))
    return found


class MemoryGate:
    """`withhold(pool)` is `None` when one more token fits, else the
    ledger reason (`rss ...`) it is held for."""

    def __init__(
        self, trace_log: str, decisions: str, mem_available: Callable[[], Optional[int]], proc_root: str = "/proc"
    ):
        self.trace_log = trace_log
        self.decisions = decisions
        self.mem_available = mem_available
        self.proc_root = proc_root
        self.finished_peak: dict[str, int] = {}
        self._offset = 0

    def _read_finished(self) -> None:
        try:
            with open(self.trace_log, "rb") as handle:
                handle.seek(self._offset)
                chunk = handle.read()
        except OSError:
            return
        complete = chunk[: chunk.rfind(b"\n") + 1]
        self._offset += len(complete)
        for raw in complete.decode("utf-8", errors="replace").splitlines():
            parsed = _end_fields(raw)
            if parsed:
                element, peak = parsed
                self.finished_peak[element] = max(peak, self.finished_peak.get(element, 0))

    def _sandboxes(self) -> dict[int, str]:
        sandboxes: dict[int, str] = {}
        try:
            with open(self.decisions, encoding="utf-8") as handle:
                lines = handle.readlines()
        except OSError:
            return sandboxes
        for line in lines:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row.get("pid"), int) and row.get("element"):
                sandboxes[row["pid"]] = row["element"]
        return sandboxes

    def withhold(self, pool: int) -> Optional[str]:
        table = _proc_table(self.proc_root)
        children: dict[int, list[int]] = {}
        for pid, (ppid, _rss) in table.items():
            children.setdefault(ppid, []).append(pid)
        live_max: dict[str, int] = {}
        live_total = 0
        for root, element in self._sandboxes().items():
            if root not in table:
                continue  # that sandbox has exited
            rss = [table[pid][1] for pid in _descendants(root, children)]
            live_total += sum(rss)
            live_max[element] = max([*rss, live_max.get(element, 0)])
        if not live_max:
            return None
        self._read_finished()
        for element in sorted(live_max):
            if live_max[element] > self.finished_peak.get(element, 0):
                return f"rss unsettled {element} live {live_max[element]}>finished {self.finished_peak.get(element, 0)}"
        available = self.mem_available()
        if available is None:
            return None
        per_job = max(max(live_max[e], self.finished_peak.get(e, 0)) for e in live_max)
        jobs = pool + len(live_max) + 1 + MEMORY_RESERVE_JOBS
        if per_job * jobs > available + live_total:
            return f"rss {per_job}x{jobs}>{available}+{live_total}"
        return None


def _task_children(pid: int, proc_root: str) -> Optional[list[int]]:
    """`pid`'s children from `task/*/children`; `None` where the kernel has no such file."""
    try:
        kids: list[int] = []
        for tid in os.listdir(f"{proc_root}/{pid}/task"):
            with open(f"{proc_root}/{pid}/task/{tid}/children", encoding="utf-8") as handle:
                kids.extend(int(token) for token in handle.read().split())
    except (OSError, ValueError):
        return None
    return kids


class _TaskChildren:
    """`_descendants`' `children` mapping, read from `task/*/children` one pid at a time."""

    def __init__(self, proc_root: str):
        self.proc_root = proc_root

    def get(self, pid: int, default=()):
        kids = _task_children(pid, self.proc_root)
        return default if kids is None else kids


def sandbox_children(root: int, proc_root: str = "/proc"):
    """UX-1314: the children mapping a tick walks - `task/*/children` where `root` has it, else one ppid scan."""
    if _task_children(root, proc_root) is not None:
        return _TaskChildren(proc_root)
    children: dict[int, list[int]] = {}
    for pid, (ppid, _rss) in _proc_table(proc_root).items():
        children.setdefault(ppid, []).append(pid)
    return children


def sandbox_tree(root: int, children) -> list[int]:
    """`root` and its host descendants, root first."""
    return [root, *_descendants(root, children)]


def follow_sandbox_roots(decisions: str, offset: int) -> tuple[dict[int, str], int]:
    """UX-1314: `({host root pid: element}, offset)` from the decision rows past `offset`; a partial last line waits."""
    try:
        with open(decisions, "rb") as handle:
            handle.seek(offset)
            chunk = handle.read()
    except OSError:
        return {}, offset
    complete = chunk[: chunk.rfind(b"\n") + 1]
    roots: dict[int, str] = {}
    for line in complete.decode("utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and isinstance(row.get("pid"), int) and row.get("element"):
            roots[row["pid"]] = row["element"]
    return roots, offset + len(complete)
