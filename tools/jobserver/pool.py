"""UX-901: the token pool - the FIFO, `PoolController`, `Broker`, and
the proxy/plan/PSI readers they act on. Imports stdlib and the shim
only, never the tracer or `bga` (the import boundary this package is
for): `cpu_sampler`/`pid_to_element_reader` below are the tracer's own
`/proc` and raw-log readers, bound here by the tracer at import time
rather than imported, so the pool never reaches back for them.
"""
import array
import errno
import fcntl
import json
import os
import re
import statistics
import termios
import threading
import time
from typing import Optional

from ..native_trace.bwrap_shim import JOBSERVER_PINNED
from ._jsonl import jsonl_rows

#: Bound by `bst_native_build_tracer` right after it defines its own
#: `/proc/stat` reader - `None` until then, which only matters to a
#: caller that never sets it (a guard scripts `_sample_busy_cores`
#: directly instead, the same way it always has).
cpu_sampler = None

#: Bound by `bst_native_build_tracer` right after it defines its own
#: raw-log pid map reader - same reach-back as `cpu_sampler` above, for
#: `Broker`'s live refresh (`_maybe_refresh_pid_to_element`).
pid_to_element_reader = None

_PSI_CPU_PATH = "/proc/pressure/cpu"
_PSI_MEMORY_PATH = "/proc/pressure/memory"
_PSI_SOME_AVG10_RE = re.compile(r"avg10=([\d.]+)")

#: UX-850: `/proc/meminfo`'s own path, parameterised so a guard scripts
#: it away from the host's own.
_MEMINFO_PATH = "/proc/meminfo"

#: UX-845 / Direction 20 argument 2: how often the pool is reconsidered -
#: an order of magnitude faster than `make -l`'s one-minute EMA, read
#: only at job start.
JOBSERVER_POOL_INTERVAL_S = 0.25

#: `some avg10` above this is "the machine is suffering", not just busy.
JOBSERVER_POOL_PSI_BOUND = 10.0

#: UX-850: memory's own bound, same reading, same threshold - a second
#: axis the CPU one says nothing about.
JOBSERVER_POOL_MEMORY_PSI_BOUND = 10.0

#: UX-852: how often outstanding wrapper tokens are audited against the
#: process table - decoupled from the pool's own 250ms cadence, since a
#: `kill(pid, 0)` sweep is a different concern at a different price.
JOBSERVER_AUDIT_INTERVAL_S = 1.0

#: UX-849: 100ms - an order of magnitude faster than `PoolController`'s
#: own 250ms tick, since a proxy grant only has to beat the sandbox that
#: is about to ask its own `make` to wait on it.
JOBSERVER_BROKER_INTERVAL_S = 0.1

try:
    _TICKS_PER_S = float(os.sysconf("SC_CLK_TCK"))
except (ValueError, OSError, AttributeError):  # pragma: no cover
    _TICKS_PER_S = 100.0

#: The shortest interval over which "cores busy" is a reading rather
#: than noise: one tick, the same derivation `read_cpu_sample`'s own
#: caller uses (`bst_native_build_tracer._CPU_MIN_INTERVAL_S`) -
#: computed again here from the same `os.sysconf` call rather than
#: imported, since this module never reaches the tracer.
_CPU_MIN_INTERVAL_S = 1.0 / _TICKS_PER_S


def open_jobserver(n: int, scratch: str, seed: Optional[int] = None) -> tuple[str, int, int]:
    """UX-841: make a FIFO under `scratch`, seed it with `+` tokens, and
    confirm the seed landed by reading the FIFO's own readable byte count
    back (`FIONREAD`) rather than trusting the write call. Returns the
    path, a host-side fd kept open for the FIFO's whole life (UX-679:
    its buffer is discarded once every fd on it closes), and the token
    count written. Cleans up after itself and raises on a mismatch.

    `seed` (UX-858): `n - 1` when omitted, `open_jobserver`'s own prior
    behaviour - `n` is the pool's ceiling (its capacity), not
    necessarily what it should open holding. Clamped at `n - 1`
    (never the full ceiling) so a hand-typed `--jobserver-seed` cannot
    fill the FIFO past what `PoolController` is willing to track.
    """
    path = os.path.join(scratch, "jobserver")
    os.mkfifo(path)
    fd = os.open(path, os.O_RDWR)
    tokens = n - 1 if seed is None else min(seed, n - 1)
    os.write(fd, b"+" * tokens)
    readable = array.array("i", [0])
    fcntl.ioctl(fd, termios.FIONREAD, readable, True)
    if readable[0] != tokens:
        os.close(fd)
        os.remove(path)
        raise RuntimeError(
            f"jobserver FIFO {path} holds {readable[0]} readable bytes "
            f"after seeding {tokens}")
    return path, fd, tokens


def close_jobserver(path: Optional[str], fd: Optional[int]) -> None:
    """UX-841: `open_jobserver`'s pair - close the fd, then remove the FIFO."""
    if fd is not None:
        os.close(fd)
    if path is not None:
        os.remove(path)


def read_plan_slack(path: Optional[str]) -> dict:
    """UX-849: `--plan`'s `analyze.json`, reduced to `{element: slack_us}`
    - `report["elements"]["slack"]`, the per-element key `bga analyze`
    already publishes. `{}` on any failure (missing file, bad JSON, no
    `elements`/`slack` key) - the caller then runs with an empty plan,
    same as no `--plan` for every element's ordering."""
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    slack = data.get("elements", {}).get("slack", {})
    return dict(slack) if isinstance(slack, dict) else {}


def read_plan_peak_rss(path: Optional[str]) -> dict:
    """UX-850: the same `analyze.json` `read_plan_slack` reads, this time
    `{element: peak_rss_bytes}` from `elements.peak_rss_bytes`. `{}` on
    any failure or absence - the caller then withholds nothing, same
    posture as `read_plan_slack`."""
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    peak = data.get("elements", {}).get("peak_rss_bytes", {})
    return dict(peak) if isinstance(peak, dict) else {}


def read_mem_available_bytes(path: str = _MEMINFO_PATH) -> Optional[int]:
    """`MemAvailable` from `/proc/meminfo`, in bytes so it compares
    directly against `peak_rss_bytes`. `None` on any failure (missing
    file, unreadable, no `MemAvailable` line) - the caller then
    withholds nothing rather than guess."""
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def read_psi_some_avg10(path: str = _PSI_CPU_PATH) -> Optional[float]:
    """The `some` line's `avg10` field from `/proc/pressure/cpu`, or
    `None` where the file is absent (kernel < 4.20) or unreadable."""
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("some "):
                    match = _PSI_SOME_AVG10_RE.search(line)
                    if match:
                        return float(match.group(1))
    except OSError:
        return None
    return None


def create_jobserver_proxies(proxies_dir: str, elements: dict) -> dict:
    """UX-849: one FIFO per element named in `elements` (the kinds map -
    every element `bst show` resolved), under `proxies_dir`. Returns
    `{element: fd}`, each opened read-write and non-blocking so a
    withdrawal from an empty proxy never stalls the broker. Mirrors
    `open_jobserver`'s own O_RDWR-self-holding-fd shape, one FIFO
    per element instead of one FIFO for the whole build."""
    os.makedirs(proxies_dir, exist_ok=True)
    fds = {}
    for element in elements:
        path = os.path.join(proxies_dir, f"{element}.fifo")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        os.mkfifo(path)
        fd = os.open(path, os.O_RDWR)
        os.set_blocking(fd, False)
        fds[element] = fd
    return fds


def _outstanding_wrapper_holders(ledger_path: str) -> dict[int, tuple[str, int]]:
    """UX-852: `{pid: (tool, tokens)}` for every wrapper `acquire` row in
    `ledger_path` not yet closed by a `release` or a `leaked` row - the
    same skip-per-row tolerance the other ledger readers use for the
    shapes (`PoolController` ticks) this file also holds."""
    outstanding: dict[int, tuple[str, int]] = {}
    for row in jsonl_rows(ledger_path):
        try:
            event = row["event"]
            pid = int(row["pid"])
        except (ValueError, KeyError):
            continue
        if event == "acquire":
            outstanding[pid] = (row["tool"], int(row["tokens"]))
        elif event in ("release", "leaked"):
            outstanding.pop(pid, None)
    return outstanding


def _holder_is_gone(pid: int) -> bool:
    """UX-852: `kill(pid, 0)` raising `ProcessLookupError` is the
    liveness test - any other outcome (alive, or a signal this process
    may not send) is treated as "cannot tell", not as gone."""
    try:
        os.kill(pid, 0)
        return False
    except ProcessLookupError:
        return True
    except OSError:
        return False


class PoolController:
    """UX-845: the jobserver as a client of its own FIFO.

    Every `INTERVAL_S`, `tick()` samples `cpu_busy_cores` (the same
    `/proc/stat` jiffy delta `HostSampler._to_cores` computes, :883-904)
    and, where `/proc/pressure/cpu` exists, PSI's `some avg10`, and moves
    the pool by at most one token: two consecutive samples below
    `capacity - 1` write a `+`; a sample above `capacity`, or PSI above
    `JOBSERVER_POOL_PSI_BOUND`, reads one token back - non-blocking, so a
    tick where every token is held records `withdraw_held` and does
    nothing, and the pool shrinks on whichever later tick finds a token
    to read. `busy_cores`/`psi_some10` passed to `tick()` let a caller
    (the guard) script the series directly instead of reading `/proc`.

    UX-852: `start()` also runs `audit_leaks()` on its own
    `JOBSERVER_AUDIT_INTERVAL_S` cadence - a wrapper `SIGKILL`ed between
    its own `acquire` row and its trap's `release` never returns its
    tokens on its own; see `audit_leaks` for the liveness test.
    """

    def __init__(self, fd: int, ceiling: int, capacity: Optional[int] = None,
                 ledger_path: Optional[str] = None,
                 psi_paths: Optional[dict] = None):
        """`psi_paths` (UX-850's own arg-count cap, `Broker`'s `scratch`
        one class up): `{"cpu": path, "memory": path}`, both optional -
        `None`/absent resolves to the real `/proc/pressure/*` file, so a
        guard scripts either or both away from the host's own.
        `psi_paths["broker_owns_audit"]` (UX-854's verifier, same cap):
        `True` when a `Broker` exists for this same ledger/FIFO - one
        auditor per capture, so `audit_leaks` is a no-op and `start`
        never spins its thread, rather than the two racing the same
        ledger unlocked. `psi_paths["seed"]` (UX-858, same cap): where
        the pool starts - `ceiling - 1` when absent, matching
        `open_jobserver`'s own default seed."""
        psi_paths = psi_paths or {}
        self.broker_owns_audit = bool(psi_paths.get("broker_owns_audit"))
        self.fd = fd
        self.ceiling = ceiling
        self.capacity = capacity if capacity is not None else (os.cpu_count() or 1)
        # Resolved at call time so a guard can point it away from the
        # host's own file - CI's runner has PSI, this box does not.
        self.psi_path = psi_paths.get("cpu") or _PSI_CPU_PATH
        self.psi_present = os.path.exists(self.psi_path)
        self.psi_memory_path = psi_paths.get("memory") or _PSI_MEMORY_PATH
        self.psi_memory_present = os.path.exists(self.psi_memory_path)
        self.memory_psi_withdraws = 0
        self.interval_s = JOBSERVER_POOL_INTERVAL_S
        self.psi_bound = JOBSERVER_POOL_PSI_BOUND
        self.memory_psi_bound = JOBSERVER_POOL_MEMORY_PSI_BOUND
        # Matches what `open_jobserver` already seeded, and this is that
        # same count kept host-side - never below zero, never above
        # `ceiling - 1` (UX-858: the seed, not necessarily `ceiling - 1`).
        seed = psi_paths.get("seed")
        # UX-858's verifier: clamped, not refused - a hand-typed
        # --jobserver-seed above the ceiling must not start the pool
        # past the invariant every other guard holds (pool < ceiling).
        self.pool = ceiling - 1 if seed is None else min(seed, ceiling - 1)
        self.moves = 0
        self._below_streak = 0
        self._cpu = None  # (busy, total, t) - own delta state
        self._stop = threading.Event()
        self._thread = None
        self._audit_thread = None
        # A controller that never `start()`s is trivially stopped -
        # `fixed` mode's report reads this without ever constructing one.
        self.stopped = True
        self.ledger_path = ledger_path
        if ledger_path:
            open(ledger_path, "w", encoding="utf-8").close()  # truncate/create
        os.set_blocking(fd, False)  # a withdrawal must never block on a client

    def _sample_busy_cores(self) -> Optional[float]:
        sample = cpu_sampler() if cpu_sampler else None
        if not sample or "cpu_busy_jiffies" not in sample:
            return None
        busy, total = sample["cpu_busy_jiffies"], sample["cpu_total_jiffies"]
        t = time.monotonic()
        was_busy, was_total, at = self._cpu or (None, None, None)
        self._cpu = (busy, total, t)
        elapsed = t - at if at is not None else 0.0
        window = total - was_total if was_total is not None else 0
        if was_busy is None or elapsed < _CPU_MIN_INTERVAL_S or window <= 0:
            return None
        return round((busy - was_busy) * sample.get("cores", self.capacity) / window, 3)

    def _try_withdraw(self) -> bool:
        try:
            return bool(os.read(self.fd, 1))
        except BlockingIOError:
            return False
        except OSError as exc:
            if exc.errno == errno.EAGAIN:
                return False
            raise

    def _handle_overload(self, busy_cores: float, psi_some10: Optional[float],
                          psi_over: bool, psi_mem10: Optional[float] = None,
                          psi_mem_over: bool = False) -> tuple[str, str]:
        """`busy_cores`/PSI is over the bound - withdraw one token, unless
        the pool is already empty (the verifier's floor edge: nothing to
        read, so no attempt is made and no move is counted). UX-850:
        memory PSI is checked first so its reason - `_handle_overload`'s
        `memory psi` text - survives even when CPU is also over."""
        self._below_streak = 0
        if self.pool == 0:
            return "hold", "pool at floor"
        action = "withdraw_held"
        if self._try_withdraw():
            self.pool -= 1
            action = "withdraw"
        if psi_mem_over:
            reason = f"memory psi {psi_mem10}>{self.memory_psi_bound}"
        elif psi_over:
            reason = f"psi {psi_some10}>{self.psi_bound}"
        else:
            reason = f"busy {busy_cores}>capacity {self.capacity}"
        return action, reason

    def _handle_underload(self, busy_cores: float) -> tuple[str, str]:
        """Below `capacity - 1` - the two-sample hysteresis before a
        `+` lands, gated by the ceiling."""
        self._below_streak += 1
        if self._below_streak >= 2 and self.pool < self.ceiling - 1:
            os.write(self.fd, b"+")
            self.pool += 1
            return "add", f"busy {busy_cores}<capacity-1, streak 2"
        return "hold", f"busy {busy_cores}<capacity-1, streak {self._below_streak}"

    def tick(self, busy_cores: Optional[float] = None,
             psi_some10: Optional[float] = None,
             psi_mem10: Optional[float] = None) -> dict:
        """One control step - the whole decision, callable directly by
        the guard with a scripted `(busy_cores, psi_some10, psi_mem10)`
        triple, or by `run()` with all three left `None` to read `/proc`."""
        if busy_cores is None:
            busy_cores = self._sample_busy_cores()
        if psi_some10 is None and self.psi_present:
            psi_some10 = read_psi_some_avg10(self.psi_path)
        if psi_mem10 is None and self.psi_memory_present:
            psi_mem10 = read_psi_some_avg10(self.psi_memory_path)
        action, reason = "hold", "no sample yet"
        if busy_cores is not None:
            psi_over = psi_some10 is not None and psi_some10 > self.psi_bound
            psi_mem_over = psi_mem10 is not None and psi_mem10 > self.memory_psi_bound
            if busy_cores > self.capacity or psi_over or psi_mem_over:
                action, reason = self._handle_overload(
                    busy_cores, psi_some10, psi_over, psi_mem10, psi_mem_over)
            elif busy_cores < self.capacity - 1:
                action, reason = self._handle_underload(busy_cores)
            else:
                self._below_streak = 0
                reason = f"busy {busy_cores} within band"
        if action in ("add", "withdraw"):
            self.moves += 1
            if action == "withdraw" and psi_mem_over:
                self.memory_psi_withdraws += 1
        row = {"t_us": int(time.time() * 1_000_000), "busy_cores": busy_cores,
               "psi_some10": psi_some10, "psi_mem10": psi_mem10,
               "pool": self.pool, "action": action, "reason": reason}
        if self.ledger_path:
            with open(self.ledger_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")
        return row

    def audit_leaks(self) -> list[dict]:
        """UX-852: outstanding wrapper tokens vs. the process table.

        Rebuilt fresh from `ledger_path` every call: a wrapper `acquire`
        row is outstanding until a `release` *or a `leaked` row of this
        method's own* closes it, so a pid this call already refilled
        never surfaces again on a later read of the same file - no
        separate "already handled" state to keep in sync with it.
        `_holder_is_gone` is the liveness test. Returns the `leaked`
        rows this call wrote. A no-op when `broker_owns_audit` - the
        `Broker` this ledger also belongs to is the sole auditor.
        """
        if not self.ledger_path or self.broker_owns_audit:
            return []
        leaked_rows = []
        for pid, (tool, tokens) in _outstanding_wrapper_holders(self.ledger_path).items():
            if not _holder_is_gone(pid):
                continue  # alive, or a signal this process may not send
            try:
                os.write(self.fd, b"+" * tokens)
            except OSError:
                continue
            row = {"event": "leaked", "tool": tool, "pid": pid,
                  "tokens": tokens, "t": time.time()}
            with open(self.ledger_path, "a", encoding="utf-8") as ledger:
                ledger.write(json.dumps(row, separators=(",", ":")) + "\n")
            leaked_rows.append(row)
        return leaked_rows

    def _run(self) -> None:
        while not self._stop.is_set():
            self.tick()
            self._stop.wait(self.interval_s)

    def _run_audit(self) -> None:
        while not self._stop.is_set():
            self.audit_leaks()
            self._stop.wait(JOBSERVER_AUDIT_INTERVAL_S)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        if not self.broker_owns_audit:
            self._audit_thread = threading.Thread(target=self._run_audit, daemon=True)
            self._audit_thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval_s + 1.0)
            if self._thread.is_alive():
                # UX-845's verifier: the first join can be outlived by a
                # tick already in flight - `close_jobserver` removing the
                # FIFO under it is the hazard, so wait once more rather
                # than trust the first timeout.
                self._thread.join(timeout=2.0)
            self.stopped = not self._thread.is_alive()
        if self._audit_thread is not None:
            # UX-852's verifier: the audit writes the same fd, so it too
            # must be caught up before `close_jobserver` - two joins,
            # and its liveness folds into `stopped`.
            self._audit_thread.join(timeout=JOBSERVER_AUDIT_INTERVAL_S + 2.0)
            if self._audit_thread.is_alive():
                self._audit_thread.join(timeout=2.0)
            self.stopped = self.stopped and not self._audit_thread.is_alive()


class Broker:
    """UX-849: `PoolController`'s sibling - it never resizes the global
    pool, it only moves tokens already in it into the proxy of whichever
    *running* element has the least slack (`plan`, `{element: slack_us}`
    from `--plan`'s `analyze.json`). An element `plan` does not name gets
    the plan's own median slack, so an unplanned element is treated as
    "average", neither starved nor favoured. A tie is broken by name -
    deterministic, not insertion order.

    `note_running`/`note_done` are the broker's view of which sandboxes
    are alive, fed by the caller from the shim's own decision rows and
    `.done` markers (never `/proc`). `tick()` is the distribution step,
    callable directly by a guard exactly like `PoolController.tick()`;
    `poll()` is what `_run()` calls, folding the decisions-file/`.done`
    scan in front of it for the real capture.
    """

    def __init__(self, global_fd: int, proxy_fds: dict, plan: dict,
                 ledger_path: Optional[str] = None,
                 scratch: Optional[dict] = None):
        """`scratch` (UX-849's own arg-count cap, the `kind_context`
        shape `_resolve_kind_and_probe` already uses one module over):
        `{"decisions": path, "proxies_dir": path, "peak_rss": {element:
        bytes}, "meminfo_path": path, "raw_log_path": path}` - UX-850
        added the peak-RSS pair, UX-854 the raw log path `poll()` rereads
        for `pid_to_element` once a second; all optional (`{}`/the real
        file) for a guard driving `tick()`/`note_running`/`note_done`
        directly."""
        scratch = scratch or {}
        self.global_fd = global_fd
        self.proxy_fds = dict(proxy_fds)
        self.plan = dict(plan)
        self.median_slack = statistics.median(self.plan.values()) if self.plan else 0
        self.element_max_jobs: dict = {}
        self.running: set = set()
        self.granted = dict.fromkeys(self.proxy_fds, 0)
        self.grants = 0
        self.drains = 0
        # UX-854: leaks refilled either at `note_done` (proxy remainder
        # to the global FIFO) or on `tick()` (a dead wrapper holder's
        # tokens back to the still-running element's proxy).
        self.leaks = 0
        self.tokens_refilled = 0
        self.ledger_path = ledger_path
        self.decisions_path = scratch.get("decisions")
        self.proxies_dir = scratch.get("proxies_dir")
        # UX-850: memory is a second resource the pool reads - withheld
        # when granting would push an element's held tokens past what
        # its own planned peak RSS leaves room for.
        self.peak_rss = dict(scratch.get("peak_rss") or {})
        self.meminfo_path = scratch.get("meminfo_path") or _MEMINFO_PATH
        self.memory_withheld = 0
        self.raw_log_path = scratch.get("raw_log_path")
        self.pid_to_element: dict = {}
        self._pid_map_interval_s = 1.0
        self._pid_map_read_at = 0.0
        self._decisions_read = 0
        self._done_seen: set = set()
        self.interval_s = JOBSERVER_BROKER_INTERVAL_S
        self._stop = threading.Event()
        self._thread = None
        self.stopped = True
        os.set_blocking(global_fd, False)

    def slack_for(self, element: str):
        return self.plan.get(element, self.median_slack)

    def _peak_for(self, element: str, median_peak) -> int:
        """The element's own planned peak, or `median_peak` (the plan's
        median, over `self.peak_rss`'s own values) for one `note_running`
        named but `--plan` did not (UX-853)."""
        peak = self.peak_rss.get(element)
        return median_peak if peak is None else peak

    def _memory_gate(self, element: str, grant_n: int,
                      mem_available: Optional[int]) -> int:
        """UX-850/853: `grant_n` if granting it still fits under
        `MemAvailable` once every *running* element's own peak RSS times
        its held tokens (`reserved`) is set aside first, else 0 and a
        ledger row carrying `reserved`. Whole-or-nothing per tick - a
        shrunk grant is still a decision this tick's later elements
        would have to re-derive room for. `reserved` is read fresh each
        call, so an element already granted earlier this tick counts at
        its new total, not its start-of-tick one."""
        if not self.peak_rss or mem_available is None:
            return grant_n
        median_peak = statistics.median(self.peak_rss.values())
        candidate_peak = self._peak_for(element, median_peak)
        reserved = sum(self._peak_for(running, median_peak)
                       * (1 + self.granted[running])
                       for running in self.running)  # +1 each: implicit
        if mem_available - reserved - candidate_peak * grant_n >= 0:
            return grant_n
        self.memory_withheld += 1
        self._log({"event": "memory_withheld", "element": element,
                   "tokens": grant_n, "mem_available": mem_available,
                   "peak_rss": candidate_peak, "reserved": reserved,
                   "t": time.time()})
        return 0

    def _cap_for(self, element: str) -> Optional[int]:
        max_jobs = self.element_max_jobs.get(element)
        return None if max_jobs is None else max(0, max_jobs - 1)

    def _log(self, row: dict) -> None:
        if self.ledger_path:
            with open(self.ledger_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")

    def note_running(self, element: str, max_jobs: Optional[int] = None) -> None:
        """A sandbox for `element` started (the shim's own decision row)."""
        if element not in self.proxy_fds:
            return  # no proxy was pre-created for it - nothing to grant
        self.running.add(element)
        if max_jobs is not None:
            self.element_max_jobs[element] = max_jobs

    def note_done(self, element: str) -> None:
        """`element`'s sandbox exited - drain its proxy back to the
        global FIFO, non-blocking, one `read` per byte held. UX-854:
        whatever `granted` still exceeds the drained bytes was held by a
        wrapper holder now gone with the sandbox - written back to the
        global FIFO too, as a `leaked` row (`pid: null`, the holders are
        gone or unknown) rather than left to shrink the pool."""
        self.running.discard(element)
        fd = self.proxy_fds.get(element)
        if fd is None:
            return
        drained = 0
        while True:
            try:
                if not os.read(fd, 1):
                    break
            except BlockingIOError:
                break
            drained += 1
        if drained:
            os.write(self.global_fd, b"+" * drained)
            self.granted[element] = max(0, self.granted[element] - drained)
            self.drains += 1
            self._log({"event": "drain", "element": element,
                       "tokens": drained, "t": time.time()})
        leaked = self.granted[element]
        if leaked > 0:
            os.write(self.global_fd, b"+" * leaked)
            self.granted[element] = 0
            self.leaks += 1
            self.tokens_refilled += leaked
            self._log({"event": "leaked", "element": element, "pid": None,
                       "tokens": leaked, "t": time.time()})

    def _drain_global(self) -> int:
        moved = 0
        while True:
            try:
                if not os.read(self.global_fd, 1):
                    break
            except BlockingIOError:
                break
            moved += 1
        return moved

    def _audit_wrapper_leaks(self, pid_to_element: dict) -> None:
        """UX-854's verifier (point 1): when a `Broker` exists, it is the
        *sole* auditor of wrapper holders on this ledger -
        `PoolController.audit_leaks` stays off (`broker_owns_audit`), so
        the two never race the same file unlocked. A gone pid mapped to
        a *running* element goes back to that element's own proxy (it
        may take the tokens again); anything else - unmapped, or mapped
        to an element not running - goes back to the global FIFO with
        `PoolController.audit_leaks`'s own row shape plus `element:
        null`. A pid this call already closed with a `leaked` row does
        not resurface: the next read of `ledger_path` pops it."""
        if not self.ledger_path:
            return
        for pid, (tool, tokens) in _outstanding_wrapper_holders(self.ledger_path).items():
            if not _holder_is_gone(pid):
                continue
            element = pid_to_element.get(pid)
            if element is not None and element in self.running:
                fd = self.proxy_fds.get(element)
                if fd is None:
                    continue
                os.write(fd, b"+" * tokens)
                self.leaks += 1
                self.tokens_refilled += tokens
                self._log({"event": "leaked", "element": element, "pid": pid,
                           "tokens": tokens, "t": time.time()})
            else:
                try:
                    os.write(self.global_fd, b"+" * tokens)
                except OSError:
                    continue
                self.leaks += 1
                self.tokens_refilled += tokens
                self._log({"event": "leaked", "tool": tool, "pid": pid,
                           "tokens": tokens, "element": None, "t": time.time()})

    def tick(self, pid_to_element: Optional[dict] = None) -> None:
        """One control step: whatever is readable on the global FIFO
        right now is handed to the running element with the least slack
        first, filling it to its own cap before moving to the next -
        never round-robin, so the element that most needs a core gets
        every token it can use before the next one sees any. UX-854's
        wrapper-leak audit runs every call, independent of whether the
        global FIFO had anything to distribute this tick."""
        self._audit_wrapper_leaks(pid_to_element or {})
        moved = self._drain_global()
        if moved == 0:
            return
        order = sorted((self.running & self.proxy_fds.keys()),
                       key=lambda element: (self.slack_for(element), element))
        # UX-850: read once per tick, not per element - `MemAvailable`
        # moves on the host's own clock, not the broker's ordering.
        mem_available = (read_mem_available_bytes(self.meminfo_path)
                         if self.peak_rss else None)
        remaining = moved
        for element in order:
            if remaining <= 0:
                break
            cap = self._cap_for(element)
            room = remaining if cap is None else max(0, cap - self.granted[element])
            grant_n = min(remaining, room)
            if grant_n <= 0:
                continue
            grant_n = self._memory_gate(element, grant_n, mem_available)
            if grant_n <= 0:
                continue
            os.write(self.proxy_fds[element], b"+" * grant_n)
            self.granted[element] += grant_n
            self.grants += 1
            remaining -= grant_n
            self._log({"event": "grant", "element": element,
                       "tokens": grant_n, "t": time.time()})
        if remaining > 0:
            # No running element in the plan could take the rest (every
            # proxy at its cap, or nothing running yet) - hand it back
            # rather than let it sit lost in this tick's own read.
            os.write(self.global_fd, b"+" * remaining)

    def _scan_decisions(self) -> None:
        if not self.decisions_path:
            return
        try:
            with open(self.decisions_path, encoding="utf-8") as handle:
                lines = handle.readlines()
        except OSError:
            return
        for line in lines[self._decisions_read:]:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            element, decision = row.get("element"), row.get("decision")
            if element and decision and decision != JOBSERVER_PINNED:
                self.note_running(element, row.get("max_jobs"))
        self._decisions_read = len(lines)

    def _scan_done(self) -> None:
        if not self.proxies_dir:
            return
        try:
            names = os.listdir(self.proxies_dir)
        except OSError:
            return
        for name in names:
            if not name.endswith(".done"):
                continue
            element = name[:-len(".done")]
            if element not in self._done_seen:
                self._done_seen.add(element)
                self.note_done(element)

    def _maybe_refresh_pid_to_element(self) -> None:
        """UX-854: the tracer's own `read_pid_to_element` re-streams the
        whole raw log - once a second, not once a 100ms tick, is the cap
        the task set. Bound as `pid_to_element_reader` at import time
        (this module never reaches the tracer for it directly)."""
        if not self.raw_log_path or not pid_to_element_reader:
            return
        now = time.monotonic()
        if now - self._pid_map_read_at < self._pid_map_interval_s:
            return
        self._pid_map_read_at = now
        self.pid_to_element = pid_to_element_reader(self.raw_log_path)

    def poll(self) -> None:
        """`_run()`'s own step: learn who is running or done, then
        distribute. Split from `tick()` so a guard can drive the
        distribution directly against a scripted population instead of
        real decision/`.done` files."""
        self._scan_decisions()
        self._scan_done()
        self._maybe_refresh_pid_to_element()
        self.tick(self.pid_to_element)

    def _run(self) -> None:
        while not self._stop.is_set():
            self.poll()
            self._stop.wait(self.interval_s)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval_s + 1.0)
            if self._thread.is_alive():
                self._thread.join(timeout=2.0)
            self.stopped = not self._thread.is_alive()


class AdmissionBroker:
    """UX-1005 track C, the Decision's own mechanism: ranks the shims
    *waiting to start* by slack, least first, rather than letting the
    kernel wake admission-pool FIFO readers in no order at all. `Broker`'s
    sibling - same slack/median/tie-by-arrival shape - but over waiting
    requests instead of running elements' token draw.

    A waiting shim (`bwrap_shim._admitted_via_broker`) appends its own
    `{element, pid, t}` row to `requests_path` and blocks on its own
    per-element FIFO (`proxy_fds`, `create_jobserver_proxies`'s same
    shape); `tick()` reads whatever is new there, ranks every request
    still pending by `(slack_for(element), t)` - `t` is arrival order,
    the fallback for an element `plan` never named - and grants one
    admission-pool token per ranked request until the pool (drained from
    `global_fd`) runs out, returning the rest to it unspent. A request
    naming an element with no FIFO (no `--plan`, or a kind table miss)
    is left pending forever here - harmless, because the shim itself
    times out and falls back to the raw global FIFO on its own.
    """

    def __init__(self, global_fd: int, proxy_fds: dict, plan: dict,
                 requests_path: str, ledger_path: Optional[str] = None):
        self.global_fd = global_fd
        self.proxy_fds = dict(proxy_fds)
        self.plan = dict(plan)
        self.median_slack = statistics.median(self.plan.values()) if self.plan else 0
        self.requests_path = requests_path
        self.ledger_path = ledger_path
        self._requests_read = 0
        self._pending: list[dict] = []
        self.grants = 0
        self.interval_s = JOBSERVER_BROKER_INTERVAL_S
        self._stop = threading.Event()
        self._thread = None
        self.stopped = True
        os.set_blocking(global_fd, False)

    def slack_for(self, element: str):
        return self.plan.get(element, self.median_slack)

    def _log(self, row: dict) -> None:
        if self.ledger_path:
            with open(self.ledger_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")

    def _scan_requests(self) -> None:
        try:
            with open(self.requests_path, encoding="utf-8") as handle:
                lines = handle.readlines()
        except OSError:
            return
        for line in lines[self._requests_read:]:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            element, pid = row.get("element"), row.get("pid")
            if element is None or pid is None:
                continue
            self._pending.append({"element": element, "pid": pid,
                                  "t": row.get("t", 0.0)})
        self._requests_read = len(lines)

    def _drain_global(self) -> int:
        moved = 0
        while True:
            try:
                if not os.read(self.global_fd, 1):
                    break
            except BlockingIOError:
                break
            moved += 1
        return moved

    def tick(self) -> None:
        """One control step: rank everything still pending by slack (ties,
        and anything `plan` never named, by arrival - `t`), then hand out
        whatever the global pool has to the front of that order. The
        mutation this guards against is exactly "sort by arrival" alone -
        a later, least-slack arrival would then never overtake an
        earlier, high-slack one."""
        self._scan_requests()
        if not self._pending:
            return
        remaining = self._drain_global()
        if remaining <= 0:
            return
        order = sorted(self._pending,
                       key=lambda request: (self.slack_for(request["element"]),
                                            request["t"]))
        granted = []
        for request in order:
            if remaining <= 0:
                break
            fd = self.proxy_fds.get(request["element"])
            if fd is None:
                continue
            os.write(fd, b"+")
            remaining -= 1
            self.grants += 1
            granted.append(request)
            self._log({"event": "admission_grant", "element": request["element"],
                       "pid": request["pid"], "t": time.time()})
        for request in granted:
            self._pending.remove(request)
        if remaining > 0:
            os.write(self.global_fd, b"+" * remaining)

    def _run(self) -> None:
        while not self._stop.is_set():
            self.tick()
            self._stop.wait(self.interval_s)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval_s + 1.0)
            if self._thread.is_alive():
                self._thread.join(timeout=2.0)
            self.stopped = not self._thread.is_alive()
