"""UX-901: the token ledger - the raw rows `PoolController`/`Broker`
write and the wrapper `acquire`/`release` rows beside them, reduced to
what a report reads. `report_block()` is the one crossing the boundary
back to `bst_native_build_tracer`: every `jobserver*` report key, built
from inputs the tracer already had to read (the wrapper probe, the raw
log's pid map) rather than re-read here - this module imports stdlib
only, never the tracer or `bga`.
"""
import json
import os
import statistics
from typing import Optional

from ._jsonl import jsonl_rows
from .pool import _PSI_CPU_PATH, _PSI_MEMORY_PATH

#: `UX-892`: how many points one element's width series may publish.
#: `UX-297`'s rule - the report carries reductions and the raw rows stay
#: in the ledger, which the snapshot keeps either way.
JOBSERVER_SERIES_CAP = 200


def read_jobserver_decisions(path: Optional[str]) -> list:
    """UX-842: the shim's `jobserver_decisions.jsonl` folded into a list
    of `{element, max_jobs, decision}` for the report. `[]` when the
    path is absent or unreadable, or a line is malformed - the same
    tolerant posture `read_host_samples` takes for an interrupted
    capture's truncated last line."""
    return jsonl_rows(path)


def read_jobserver_ledger(path: Optional[str]) -> list:
    """UX-847: the raw ledger, one dict per line, for `report["jobserver_
    ledger"]`. Two row shapes share this file - `PoolController.tick`'s
    (`action`, `pool`, `busy_cores`, ...) and UX-846's wrapper rows
    (`event`, `tool`, `pid`, `tokens`, `t`) - and both are kept
    unmodified: this is the raw list `analyze/v6`'s `jobserver` block
    reads, not a summary. Same tolerant posture as
    `read_jobserver_decisions`."""
    return jsonl_rows(path)


def tokens_by_element(ledger_rows: list, pid_to_element: dict) -> tuple:
    """UX-847: UX-846's wrapper `acquire` rows, joined to the element
    that owned the pid - `{element: [(t, tokens), ...]}`, and the count
    of `acquire` rows no element owns (`unmapped`), for
    `jobserver_tokens_unmapped`.

    `UX-892`: `release` rows are kept, because a `release` closes an
    interval - the wrapper stamps every row with `date +%s.%N` and this
    reader used to drop it, so "four tokens for two seconds of a
    ninety-second element" and "four tokens throughout" reduced to the
    same pair. A malformed row is skipped, not raised on - the same
    posture every other ledger reader takes.
    """
    per_element: dict = {}
    unmapped = 0
    for row in ledger_rows or []:
        if not isinstance(row, dict):
            continue
        event = row.get("event")
        if event not in ("acquire", "release"):
            continue
        pid, tokens = row.get("pid"), row.get("tokens")
        if pid is None or tokens is None:
            continue
        element = (pid_to_element or {}).get(pid)
        if element is None:
            if event == "acquire":
                unmapped += 1
            continue
        per_element.setdefault(element, []).append((event, pid, row.get("t"), tokens))
    return per_element, unmapped


def admission_wait_by_element(ledger_rows: list) -> dict:
    """UX-1005 track B: `{element: wait_us}`, summed across every
    `admission_wait` row - the shim's own record of time blocked on a
    real token before `bwrap` started (`bwrap_shim.run_admitted`). Keyed
    by `element` directly - unlike `tokens_by_element`'s wrapper rows,
    the shim always knows which element it is admitting, so no pid map
    is needed. A malformed row is skipped, the same posture every other
    ledger reader here takes."""
    totals: dict = {}
    for row in ledger_rows or []:
        if not isinstance(row, dict) or row.get("event") != "admission_wait":
            continue
        element, wait_us = row.get("element"), row.get("wait_us")
        if element is None or wait_us is None:
            continue
        totals[element] = totals.get(element, 0) + int(wait_us)
    return totals


def _width_series(events: list, end_us: Optional[int] = None) -> tuple:
    """`UX-892`: one element's held-token width over time, and how many
    intervals never closed.

    A step function, not a sample: an `acquire` opens an interval at the
    count it read and a `release` closes it, so the published point is
    the element's total holding *after* that event. A `release` with no
    paired `acquire` is skipped rather than driving the sum negative; a
    wrapper killed before its trap (`UX-852`'s leak) never releases, so
    its interval is closed at the element's span end when one is known
    and counted as open either way.
    """
    ordered = sorted(
        ((int(float(t) * 1_000_000), event, pid, tokens)
         for event, pid, t, tokens in events if t is not None),
        key=lambda row: row[0])
    held: dict = {}
    series: list = []
    for t_us, event, pid, tokens in ordered:
        if event == "acquire":
            held[pid] = tokens
        elif pid in held:
            del held[pid]
        else:
            continue
        series.append([t_us, sum(held.values())])
    open_intervals = len(held)
    if held and end_us is not None:
        series.append([int(end_us), 0])
    return series, open_intervals


def summarize_jobserver_tokens_by_element(
        ledger_rows: list, pid_to_element: dict,
        tool_pids_by_element: Optional[dict] = None,
        element_end_us: Optional[dict] = None) -> tuple:
    """UX-847: `tokens_by_element`'s raw rows, reduced to what
    `analyze/v6`'s per-element table reads - `({element: {...}},
    unmapped)`, the shape `report["jobserver_tokens_by_element"]`
    publishes.

    `UX-892` adds the width series beside the two scalars, and the
    share of this element's token-holding tools that wrote the rows it
    is built from. Only wrapped tools write them: a real `make` reads
    the jobserver pipe itself and holds tokens nobody logs, so the
    series covers the wrapped share and says which - never a series
    that reads as the whole element.

    `tool_pids_by_element` is `{element: {pid, ...}}` over
    `JOBSERVER_TOOLS` (the denominator); `element_end_us` is
    `{element: t_us}` for closing a leaked interval. Both optional: the
    share is `None` without the first, which is the honest answer, not
    1.0.
    """
    raw, unmapped = tokens_by_element(ledger_rows, pid_to_element)
    tool_pids = tool_pids_by_element or {}
    by_element: dict = {}
    for element in sorted(set(raw) | set(tool_pids)):
        events = raw.get(element) or []
        acquired = [tokens for event, _pid, _t, tokens in events
                    if event == "acquire"]
        wrapped_pids = {pid for event, pid, _t, _tokens in events
                        if event == "acquire"}
        tools = tool_pids.get(element)
        record: dict = {
            "tokens_held_p50": statistics.median(acquired) if acquired else None,
            "tokens_held_max": max(acquired) if acquired else None,
            # The wrapped share, as a number, the way `UX-891` publishes
            # `lb_cpu_coverage`. `None` where the tools are unknown.
            "tokens_series_coverage": (
                len(wrapped_pids & tools) / len(tools) if tools else None),
        }
        series, open_intervals = _width_series(
            events, (element_end_us or {}).get(element))
        # Absent rather than empty: a zero-width series reads as an
        # element that held nothing, and a row with no `t` at all is a
        # row this series cannot be built from - the scalars above
        # still stand.
        if series:
            record["tokens_held_series"] = series[:JOBSERVER_SERIES_CAP]
            record["tokens_series_truncated"] = len(series) > JOBSERVER_SERIES_CAP
            record["tokens_series_open"] = open_intervals
        by_element[element] = record
    return by_element, unmapped


def jobserver_auth_style(requested: str, make_version_output: Optional[str] = None) -> str:
    """`requested` is `fd`, `fifo`, or `auto`; returns `fd` or `fifo`.

    UX-876: `auto` is always `fd` - no host `make --version` probe. A
    mixed toolchain's recipe can invoke a sandbox-built make below 4.4
    by absolute path (`UX-876`'s cmake element), and there is no way to
    know that ahead of the build; `fd` is accepted by every GNU Make
    from 4.2 up. `fifo` stays available as an explicit opt-in for an
    operator whose whole sandbox toolchain is known to be >= 4.4
    (`bwrap_shim.style_for_make_version`, UX-874, narrows an explicit
    `fifo` to `fd` per element when the sandbox make is older).
    `make_version_output` is unused by `auto` now; kept so an explicit
    `fd`/`fifo` caller (and existing tests) can still pass it.
    """
    if requested != "auto":
        return requested
    return "fd"


def summarize_jobserver_ledger(path: str, ceiling: int) -> tuple[int, int, int]:
    """`(moves, pool_min, pool_max)` from a `PoolController` ledger.

    `moves` counts only `add`/`withdraw` - `hold` and `withdraw_held`
    changed nothing. A ledger with no rows (the build was shorter than
    one tick) reports the pool it started at, `ceiling - 1`.

    UX-846: a wrapper's own `acquire`/`release` rows share this same
    file (`event`/`tool`/`pid` keys, no `pool`) - skipped per-row rather
    than aborting the whole read, which the previous single `try` around
    the loop did on the first row missing `"pool"`.
    """
    moves, pool_min, pool_max = 0, ceiling - 1, ceiling - 1
    seen = False
    for row in jsonl_rows(path):
        try:
            pool = row["pool"]
            action = row["action"]
        except KeyError:
            continue
        pool_min = pool if not seen else min(pool_min, pool)
        pool_max = pool if not seen else max(pool_max, pool)
        seen = True
        if action in ("add", "withdraw"):
            moves += 1
    return moves, pool_min, pool_max


def summarize_jobserver_leaks(path: str) -> tuple[int, int]:
    """`(leaks, tokens_refilled)` from a `PoolController` ledger's own
    `leaked` rows (UX-852) - the same skip-per-row tolerance as
    `summarize_jobserver_ledger` for the shapes this file shares."""
    leaks, tokens_refilled = 0, 0
    for row in jsonl_rows(path):
        try:
            if row["event"] != "leaked":
                continue
            tokens_refilled += int(row["tokens"])
        except (ValueError, KeyError):
            continue
        leaks += 1
    return leaks, tokens_refilled


def report_block(capture: dict) -> dict:
    """UX-901: the tracer's own `jobserver*` report keys (`analyze/v6`),
    formerly nine bare `report[...] =` lines at the capture's call site -
    `cache_key_set` and `project_max_jobs` are not `jobserver*` and stay
    there. One dict argument (`PLR0913`, the same `scratch`/`psi_paths`
    shape `Broker`/`PoolController` already take), keyed: `jobserver`,
    `jobserver_seed`, `jobserver_auth`, `jobserver_pool_mode`, `capacity`,
    `jobserver_ledger_path`, `jobserver_status_path`, `plan_path`,
    `broker_status_path`, `element_kinds_present`,
    `jobserver_decisions_path`, `jobserver_wrappers`, `pid_to_element`,
    `tool_pids`, `element_ends`, `psi_withdraw_counter` - the last four
    optional. Everything this module cannot read itself (the wrapper
    probe, the raw log's pid/tool maps, the memory-PSI withdraw count)
    is passed in already read, since this module never reaches the
    tracer or `bga` for them."""
    jobserver = capture["jobserver"]
    jobserver_seed = capture["jobserver_seed"]
    jobserver_pool_mode = capture["jobserver_pool_mode"]
    capacity = capture["capacity"]
    jobserver_ledger_path = capture["jobserver_ledger_path"]
    jobserver_status_path = capture["jobserver_status_path"]
    plan_path = capture["plan_path"]
    broker_status_path = capture["broker_status_path"]
    jobserver_decisions_path = capture["jobserver_decisions_path"]
    pid_to_element = capture.get("pid_to_element")
    tool_pids = capture.get("tool_pids")
    element_ends = capture.get("element_ends")
    psi_withdraw_counter = capture.get("psi_withdraw_counter")
    block = {
        "jobserver": jobserver,
        "jobserver_seed": jobserver_seed,
        "jobserver_auth": capture["jobserver_auth"],
    }
    if jobserver:
        controller_stopped = True
        leaks, tokens_refilled = 0, 0
        psi_memory_withdraws, memory_withheld = 0, 0
        if jobserver_pool_mode == "dynamic" and jobserver_ledger_path:
            moves, pool_min, pool_max = summarize_jobserver_ledger(
                jobserver_ledger_path, jobserver)
            if os.path.exists(jobserver_ledger_path):
                leaks, tokens_refilled = summarize_jobserver_leaks(
                    jobserver_ledger_path)
            if psi_withdraw_counter:
                psi_memory_withdraws = psi_withdraw_counter(jobserver_ledger_path)
            if jobserver_status_path and os.path.exists(jobserver_status_path):
                with open(jobserver_status_path, encoding="utf-8") as handle:
                    controller_stopped = json.load(handle)["controller_stopped"]
            else:
                controller_stopped = False
        else:
            moves, pool_min, pool_max = 0, jobserver_seed, jobserver_seed
        block["jobserver_pool"] = {
            "mode": jobserver_pool_mode, "ceiling": jobserver,
            "seed": jobserver_seed,
            "capacity": capacity, "moves": moves,
            "pool_min": pool_min, "pool_max": pool_max,
            "psi_present": os.path.exists(_PSI_CPU_PATH),
            "controller_stopped": controller_stopped,
            "leaks": leaks, "tokens_refilled": tokens_refilled,
        }
        if plan_path and broker_status_path and os.path.exists(broker_status_path):
            with open(broker_status_path, encoding="utf-8") as handle:
                broker_status = json.load(handle)
            memory_withheld = broker_status.get("memory_withheld", 0)
            block["jobserver_pool"]["broker"] = {
                "plan": plan_path, **broker_status,
            }
        block["jobserver_pool"]["memory"] = {
            "withheld": memory_withheld,
            "psi_memory_present": os.path.exists(_PSI_MEMORY_PATH),
            "psi_memory_withdraws": psi_memory_withdraws,
        }
    else:
        block["jobserver_pool"] = None
    block["jobserver_kinds_read"] = (
        capture["element_kinds_present"] if jobserver else None)
    block["jobserver_decisions"] = read_jobserver_decisions(jobserver_decisions_path)
    block["jobserver_wrappers"] = capture["jobserver_wrappers"]
    if jobserver and jobserver_ledger_path:
        ledger_rows = read_jobserver_ledger(jobserver_ledger_path)
        block["jobserver_ledger"] = ledger_rows
        by_element, unmapped = summarize_jobserver_tokens_by_element(
            ledger_rows, pid_to_element or {}, tool_pids, element_ends)
        block["jobserver_tokens_by_element"] = by_element
        block["jobserver_tokens_unmapped"] = unmapped
    return block
