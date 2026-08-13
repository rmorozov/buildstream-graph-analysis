"""Synthetic multi-subproject BuildStream project model.

Describes a small but realistically-shaped BuildStream project: four
junctioned subprojects (core-utils, data-format, net-stack, ui-toolkit)
each providing one or more C++ shared libraries, and a root C++
executable (app.bst) that links against libraries pulled in from every
subproject - including a diamond dependency (several libraries in
different subprojects all depend on core-utils:libcore.bst).

This module owns the *ground truth* dependency graph and a deterministic,
capacity-aware list scheduler that produces plausible task timings. Given
that ground truth, `generate_wrapper_log` renders a BuildStream CI wrapper
log byte-for-byte in the format tools/bst_log_to_chrome_trace.py expects,
so the real converter (not a stand-in) is what turns it into Chrome Trace
JSON - see generate_fixture.py for the full pipeline.

Everything here is deterministic (no randomness, fixed durations) so the
fixture is reproducible and stable in CI.
"""
import hashlib
from datetime import datetime, timedelta

# uid -> {'deps': [uid, ...], 'size': 'small'|'medium'|'large', 'no_fetch': bool}
ELEMENTS = {
    "core-utils.bst:libcore.bst": {"deps": [], "size": "small"},
    "core-utils.bst:liblog.bst": {"deps": ["core-utils.bst:libcore.bst"], "size": "small"},
    "data-format.bst:libjson.bst": {"deps": ["core-utils.bst:libcore.bst"], "size": "medium"},
    "data-format.bst:libxml.bst": {"deps": ["core-utils.bst:libcore.bst"], "size": "medium"},
    "net-stack.bst:libcrypto.bst": {"deps": [], "size": "medium"},
    "net-stack.bst:libnet.bst": {
        "deps": ["net-stack.bst:libcrypto.bst", "core-utils.bst:liblog.bst"],
        "size": "medium",
    },
    "ui-toolkit.bst:libwidgets.bst": {"deps": ["core-utils.bst:libcore.bst"], "size": "large"},
    "ui-toolkit.bst:libui.bst": {
        "deps": ["ui-toolkit.bst:libwidgets.bst", "data-format.bst:libjson.bst"],
        "size": "large",
    },
    "app.bst": {
        "deps": [
            "net-stack.bst:libnet.bst",
            "ui-toolkit.bst:libui.bst",
            "data-format.bst:libxml.bst",
            "core-utils.bst:liblog.bst",
        ],
        "size": "large",
        "no_fetch": True,
    },
}

REQUESTED_TARGET = "app.bst"

SIZE_DURATIONS_S = {
    "small": {"TRACK": 1.5, "FETCH": 4.0, "BUILD": 8.0},
    "medium": {"TRACK": 2.0, "FETCH": 6.0, "BUILD": 18.0},
    "large": {"TRACK": 2.5, "FETCH": 8.0, "BUILD": 35.0},
}
APP_BUILD_DURATION_S = 40.0

CAPACITIES = {"DOWNLOAD": 2, "PROCESS": 4}
MAX_JOBS = CAPACITIES["PROCESS"]

PHASE_MESSAGE = {
    "TRACK": "Tracking",
    "FETCH": "Fetching sources",
    "BUILD": "Running build commands",
}
ACTION_WORD = {"TRACK": "track", "FETCH": "fetch", "BUILD": "build"}
MESSAGE_TO_KIND = {v: k for k, v in PHASE_MESSAGE.items()}

# (uid, kind) pairs that are deliberately rendered as a bare CACHED line with
# no preceding START, to exercise a real limitation of the converter: a
# hash with no START in self.active_tasks is silently dropped (see
# WrapperTraceConverter.handle_bst_event). This element's FETCH phase will
# not appear in the resulting trace at all.
DROPPED_TASKS = frozenset({("net-stack.bst:libcrypto.bst", "FETCH")})


def phases_for(uid: str):
    """Ordered (kind, duration_s) list for one element."""
    info = ELEMENTS[uid]
    sizes = SIZE_DURATIONS_S[info["size"]]
    if info.get("no_fetch"):
        dur = APP_BUILD_DURATION_S if uid == "app.bst" else sizes["BUILD"]
        return [("BUILD", dur)]
    return [("TRACK", sizes["TRACK"]), ("FETCH", sizes["FETCH"]), ("BUILD", sizes["BUILD"])]


def hash_for(uid: str, kind: str) -> str:
    """Deterministic 8-hex-char fake BuildStream task hash."""
    return hashlib.md5(f"{uid}:{kind}".encode()).hexdigest()[:8]


def simulate_schedule():
    """Deterministic, capacity-aware greedy list scheduler.

    Respects: per-element phase order (TRACK -> FETCH -> BUILD), and
    BUILD(element) waiting on BUILD(dep) for every dependency. TRACK/FETCH
    share the DOWNLOAD resource pool; BUILD uses the PROCESS pool. Ties are
    broken deterministically by (uid, kind) so the schedule never depends
    on dict/set iteration order.

    Returns a list of dicts: {uid, kind, start_s, dur_s, finish_s}, sorted
    by start_s (ties broken by uid, kind).
    """
    tasks = {}
    for uid in ELEMENTS:
        prev_kind = None
        for kind, dur in phases_for(uid):
            pool = "PROCESS" if kind == "BUILD" else "DOWNLOAD"
            deps = set()
            if prev_kind is not None:
                deps.add((uid, prev_kind))
            if kind == "BUILD":
                for dep_uid in ELEMENTS[uid]["deps"]:
                    deps.add((dep_uid, "BUILD"))
            tasks[(uid, kind)] = {"dur": dur, "deps": deps, "pool": pool}
            prev_kind = kind

    pending_deps = {k: set(v["deps"]) for k, v in tasks.items()}
    not_started = set(tasks.keys())
    running = {}  # (uid,kind) -> (finish_time, pool)
    free = dict(CAPACITIES)
    schedule = []
    time = 0.0

    while not_started or running:
        ready = sorted((k for k in not_started if not pending_deps[k]), key=lambda k: (k[0], k[1]))
        started_this_round = False
        for k in ready:
            pool = tasks[k]["pool"]
            if free[pool] > 0:
                free[pool] -= 1
                finish = time + tasks[k]["dur"]
                running[k] = (finish, pool)
                not_started.discard(k)
                schedule.append(
                    {"uid": k[0], "kind": k[1], "start_s": time, "dur_s": tasks[k]["dur"], "finish_s": finish}
                )
                started_this_round = True

        if running:
            next_finish = min(f for f, _ in running.values())
            finished_now = [k for k, (f, _) in running.items() if f == next_finish]
            time = next_finish
            for k in finished_now:
                _, pool = running.pop(k)
                free[pool] += 1
                for deps in pending_deps.values():
                    deps.discard(k)
        elif not started_this_round and not_started:
            raise RuntimeError(
                f"scheduling deadlock: {sorted(not_started)} never became ready "
                "(check ELEMENTS for a dependency cycle)"
            )

    schedule.sort(key=lambda t: (t["start_s"], t["uid"], t["kind"]))
    return schedule


def _format_ts(base_dt: datetime, offset_s: float) -> str:
    dt = base_dt + timedelta(seconds=offset_s)
    # Matches "%Y-%m-%d %H:%M:%S,%f" with a 3-digit millisecond field,
    # exactly like the real wrapper log example this fixture is modeled on.
    return dt.strftime("%Y-%m-%d %H:%M:%S,") + f"{dt.microsecond // 1000:03d}"


def _elapsed_str(offset_s: float) -> str:
    total = int(offset_s)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def generate_wrapper_log(schedule, base_dt: datetime) -> str:
    """Render the schedule as a BuildStream CI wrapper log (see tools/bst_log_to_chrome_trace.py).

    Real, wrapper-prefixed lines in strict chronological order - not
    grouped per task - matching how an actual CI log would interleave
    concurrent builder output.
    """
    events = []  # (time_s, line_text)
    events.append((0.0, f"[wrapper][{_format_ts(base_dt, 0.0)}] INFO: Executing command: bst build app.bst"))
    events.append((
        0.05,
        f"[wrapper][{_format_ts(base_dt, 0.05)}] INFO: Starting scheduler, "
        f"Maximum Build Tasks: {MAX_JOBS}, Maximum Fetch Tasks: {CAPACITIES['DOWNLOAD']}",
    ))

    for task in schedule:
        uid, kind = task["uid"], task["kind"]
        h = hash_for(uid, kind)
        action = ACTION_WORD[kind]
        msg = PHASE_MESSAGE[kind]

        if (uid, kind) in DROPPED_TASKS:
            # Deliberately no START line - see DROPPED_TASKS docstring above.
            events.append((
                task["finish_s"],
                f"[wrapper][{_format_ts(base_dt, task['finish_s'])}] INFO: "
                f"[{_elapsed_str(task['finish_s'])}][{h}][   {action}:{uid}] CACHED {msg}",
            ))
            continue

        events.append((
            task["start_s"],
            f"[wrapper][{_format_ts(base_dt, task['start_s'])}] INFO: "
            f"[{_elapsed_str(task['start_s'])}][{h}][   {action}:{uid}] START {msg}",
        ))
        events.append((
            task["finish_s"],
            f"[wrapper][{_format_ts(base_dt, task['finish_s'])}] INFO: "
            f"[{_elapsed_str(task['finish_s'])}][{h}][   {action}:{uid}] SUCCESS {msg}",
        ))

    end_time = max(t["finish_s"] for t in schedule) + 1.0
    events.append((end_time, f"[wrapper][{_format_ts(base_dt, end_time)}] INFO: Return code: 0"))

    events.sort(key=lambda e: e[0])
    return "\n".join(line for _, line in events) + "\n"


def build_graph_dict():
    """graph/v9-shaped dict (see bga.ingest.loader.load_graph)."""
    elements = []
    dependencies = []
    for uid, info in sorted(ELEMENTS.items()):
        elements.append({
            "uid": uid,
            "cache_key": hashlib.sha256(uid.encode()).hexdigest()[:16],
            "requested_target": uid == REQUESTED_TARGET,
        })
        for dep_uid in info["deps"]:
            dependencies.append({"predecessor": dep_uid, "successor": uid, "dependency_type": "build"})
    return {"elements": elements, "dependencies": dependencies}


def independent_expected_depths():
    """Ground truth unweighted_depth per element, computed independently of
    bga's own graph algorithms (longest path in hops from a root), so tests
    can check bga's answer against a second, from-scratch implementation
    rather than against a number copied out of bga's own output.
    """
    depth = {}

    def compute(uid, stack=()):
        if uid in depth:
            return depth[uid]
        if uid in stack:
            raise RuntimeError(f"cycle detected at {uid}")
        deps = ELEMENTS[uid]["deps"]
        d = 0 if not deps else 1 + max(compute(dep, stack + (uid,)) for dep in deps)
        depth[uid] = d
        return d

    for uid in ELEMENTS:
        compute(uid)
    return depth
