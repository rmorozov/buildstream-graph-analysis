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


#: v1 reports "no limit" as a page-rounded `LONG_MAX`; anything this large is no cap.
_V1_UNLIMITED = 1 << 62


def _read_int(path: str) -> Optional[int]:
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read().strip()
        return None if text == "max" else int(text)
    except (OSError, ValueError):
        return None


def _working_set(directory: str, usage_name: str, inactive_key: str) -> int:
    """Usage minus reclaimable `inactive_file` page cache (the kubelet's working set), else plain usage."""
    usage = _read_int(os.path.join(directory, usage_name)) or 0
    try:
        with open(os.path.join(directory, "memory.stat"), encoding="utf-8") as handle:
            stat = dict(line.split()[:2] for line in handle if len(line.split()) >= 2)
        return max(0, usage - int(stat[inactive_key]))
    except (OSError, ValueError, KeyError):
        return usage


def _cgroup_caps(cgroup_root: str, self_cgroup: str) -> list[tuple[int, int]]:
    """`(limit, working set)` bytes for every capped memory cgroup on this process's path, leaf to root."""
    try:
        with open(self_cgroup, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return []
    caps = []
    for line in lines:
        _hier, _, rest = line.partition(":")
        controllers, _, path = rest.partition(":")
        if controllers == "":
            base, names = cgroup_root, ("memory.max", "memory.current", "inactive_file")
        elif "memory" in controllers.split(","):
            base, names = (
                f"{cgroup_root}/memory",
                ("memory.limit_in_bytes", "memory.usage_in_bytes", "total_inactive_file"),
            )
        else:
            continue
        parts = [part for part in path.split("/") if part]
        for depth in range(len(parts), -1, -1):
            directory = os.path.join(base, *parts[:depth])
            limit = _read_int(os.path.join(directory, names[0]))
            if limit is not None and limit < _V1_UNLIMITED:
                caps.append((limit, _working_set(directory, *names[1:])))
    return caps


def read_cgroup_limit_bytes(
    cgroup_root: str = "/sys/fs/cgroup", self_cgroup: str = "/proc/self/cgroup"
) -> Optional[int]:
    """The tightest memory limit over this process's cgroup and every ancestor, else `None`."""
    caps = _cgroup_caps(cgroup_root, self_cgroup)
    return min(limit for limit, _usage in caps) if caps else None


def read_build_memory(
    meminfo: str = "/proc/meminfo", cgroup_root: str = "/sys/fs/cgroup", self_cgroup: str = "/proc/self/cgroup"
) -> tuple[Optional[int], str]:
    """`(bytes, bound_by)`: the lower of `MemAvailable` and the tightest cgroup limit minus working set."""
    available = None
    try:
        with open(meminfo, encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    available = int(line.split()[1]) * 1024
                    break
    except (OSError, ValueError, IndexError):
        available = None
    headroom = [max(0, limit - usage) for limit, usage in _cgroup_caps(cgroup_root, self_cgroup)]
    if headroom and (available is None or min(headroom) < available):
        return min(headroom), "cgroup"
    return available, "meminfo"


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
