"""UX-676: the envelope, and the intervals that violate it.

`traced processes running` counts slots; `UX-675`'s `cpu_busy_cores`
counts cores. This reads the second against the capacity the scheduler
was configured with and the cores the host has, and names the windows
where the two disagree.

Two violations, each grounded in a measurement rather than a threshold:
**under-utilized** is at least one whole core idle while Plane 1 says
there was work - something building, or something ready and not
dispatched. One core because that is the granularity at which the
machine could have started another job; the work because idle capacity
with nothing to run is the graph's shape, not a defect (`UX-48`'s
`idle_no_tasks`, per window instead of as a total). **Overcommitted**
is load above the core count or a page written to swap in the window.

The row says which kind it is and stops there: `ready_not_dispatched`
is the scheduler, `building` with each element's own `max-jobs` is the
element's own cap. Deciding between them is `UX-677`'s.
"""

# `UX-676`: the nearest-rank rule, imported rather than restated. The
# first draft carried its own copy with a note saying the two were held
# equal by a guard - which is two rules and an instrument to keep them
# the same, where one import is one rule. `store_aggregate` reads a
# whole store, but importing it does not: this is a pure function of a
# list, and the module costs `hostinfo`, `run_store` and `schemas`,
# which `bga.analyzer` has already imported by the time this runs.
from ..store_aggregate import percentile as percentile

#: `UX-676`: how many interval rows are published per table. The same
#: number as `REDUNDANCY_FINDINGS_MAX` and the viewer's
#: `TABLE_OPENS_BOUNDED_ABOVE`, for the same reason - more rows than a
#: reader will act on. A four-hour build sampled every two seconds has
#: 7,200 intervals; the cap is what makes this a table rather than the
#: series again.
INTERVALS_MAX = 40

#: The idle that counts. One core, because a machine with 0.4 of a core
#: spare could not have started anything: BuildStream dispatches whole
#: jobs. Not a tuned fraction - halve it and the rows stop being
#: actionable, double it and a two-core host can never be under-utilized.
IDLE_CORES_FLOOR = 1.0


def wall_samples(read: dict) -> list[dict]:
    """`host-samples/v1` on the build's own wall clock.

    The same walk `bga_timeline.host_series` makes and for the same
    reason: the sampler stamps `CLOCK_MONOTONIC`, and the header carries
    the pair taken at one instant, so reaching wall time is a
    subtraction and an addition. A header missing either half yields
    nothing rather than a series on an arbitrary epoch.
    """
    header = read.get("header") or {}
    start, wall = header.get("monotonic_at_start"), header.get("wall_at_start")
    if start is None or wall is None:
        return []
    out = []
    for sample in read.get("samples") or []:
        at = sample.get("t")
        if at is None or sample.get("cpu_busy_cores") is None:
            continue
        out.append(dict(sample,
                        at_us=int(round((float(wall) + float(at)
                                         - float(start)) * 1e6))))
    return out


def intervals(samples: list[dict]) -> list[dict]:
    """`[previous sample, this sample)`, which is what a delta measures.

    `cpu_busy_cores` is a rate over the gap that ends at its own stamp -
    the sampler differences jiffies against the previous read - so
    stamping the row at `at_us` and drawing it forward would place every
    reading one interval late.
    """
    out = []
    for earlier, later in zip(samples, samples[1:]):
        span_us = later["at_us"] - earlier["at_us"]
        if span_us <= 0:
            continue
        out.append({"start_us": earlier["at_us"], "end_us": later["at_us"],
                    "duration_us": span_us,
                    "busy_cores": later["cpu_busy_cores"],
                    "cores": later.get("cores"),
                    "load1": later.get("load1"),
                    "swapped_out": (later.get("pswpout") or 0)
                    - (earlier.get("pswpout") or 0)})
    return out


def _ready_and_waiting(window: dict, tasks: list[dict]) -> dict:
    """What Plane 1 says was going on in one window.

    Three populations, because the row has to answer "could anything
    have used the idle core": what was building, what was ready and not
    dispatched, and what finished just before.
    """
    start, end = window["start_us"], window["end_us"]
    building, ready, finished = [], [], []
    for task in tasks:
        if task["start_us"] < end and task["finish_us"] > start:
            building.append(task["element"])
        # Dependency-ready and not yet dispatched for the whole window:
        # `UX-48`'s `idle_underparallel`, per window.
        if task["ready_us"] <= start and task["start_us"] >= end:
            ready.append(task["element"])
        if start <= task["finish_us"] < end:
            finished.append(task["element"])
    return {"building": sorted(set(building)), "ready": sorted(set(ready)),
            "finished": sorted(set(finished))}


#: `UX-676`: the canned question each row points at, and the token its
#: SQL carries for the bounds. The row does not ship SQL of its own -
#: `UX-368`'s rule is that a finding names a library query, so the
#: library stays the one place a query is written down.
#:
#: `plane2/v3` is folded and carries no per-process time ranges, so the
#: "processes in this interval" column the item asked for has no source
#: in `analyze`'s inputs: the only file with them is `plane2.log.gz`,
#: which `analyze` never opens by design (it is the timeline's streaming
#: input and runs to gigabytes, `UX-300`). Bounding the concurrency
#: query to the row's own window puts that count one click away instead.
ROW_QUERY = "concurrency-curve"


def _row(window: dict, run: dict, binding: float) -> dict:
    """One interval, as the reader's row. `run` is the capture's own
    context - `{tasks, max_jobs, successors, ...}` - passed whole
    rather than unpacked into six parameters."""
    who = _ready_and_waiting(window, run["tasks"])
    idle = max(0.0, binding - window["busy_cores"])
    waiting = sorted({name for element in who["finished"]
                      for name in run["successors"].get(element, ())}
                     - set(who["building"]))
    row = {
        "start_us": window["start_us"], "end_us": window["end_us"],
        "duration_us": window["duration_us"],
        "busy_cores": window["busy_cores"],
        "capacity_cores": binding,
        "busy_share": (round(window["busy_cores"] / binding, 3)
                       if binding else None),
        "lost_core_seconds": round(idle * window["duration_us"] / 1e6, 3),
        "load1": window["load1"],
        # Plane 1 records which spans overlap a window, not which
        # builder ran them - there is no lane id in `trace/v9` - so the
        # column is the concurrent set against `builders`, and each
        # element's own `max-jobs` beside it (`UX-377`).
        "building": [{"element": name,
                      "max_jobs": run["max_jobs"].get(name)}
                     for name in who["building"]],
        "ready_not_dispatched": who["ready"],
        "just_finished": who["finished"],
        "successors_waiting": waiting,
        "trace_query": ROW_QUERY,
        "trace_bounds": {"start_ns": window["start_us"] * 1000,
                         "end_ns": window["end_us"] * 1000},
    }
    return row


def compute(samples: dict, run: dict) -> dict:
    """The envelope and its two violation tables, or a named absence.

    `builders x max-jobs` is what the scheduler was configured to allow;
    the cores are what the machine can actually deliver. Busy is
    measured against the **smaller**, because a build cannot use 16
    cores on a four-core host and calling 2.0 busy cores "12 % of
    capacity" would be a verdict about a number nothing could reach.
    """
    series = wall_samples(samples)
    if len(series) < 2:
        return {"available": False, "absence":
                "this capture has fewer than two host CPU samples - "
                "`cpu_busy_cores` is a rate over a gap, and one reading "
                "is not a gap (`UX-675`)"}
    cores = series[-1].get("cores")
    configured = ((run.get("builders") or 0)
                  * (run.get("native_max_jobs") or 0)) or None
    binding = min(x for x in (configured, cores) if x) if (configured or cores) \
        else None
    if not binding:
        return {"available": False, "absence":
                "this capture records neither a core count nor "
                "`builders x max-jobs`, so there is no capacity to read "
                "the series against"}
    windows = intervals(series)
    busy = [window["busy_cores"] for window in windows]
    under = [window for window in windows
             if binding - window["busy_cores"] >= IDLE_CORES_FLOOR
             and any(_ready_and_waiting(window, run["tasks"])[kind]
                     for kind in ("building", "ready"))]
    over = [window for window in windows
            if (window["load1"] is not None and cores
                and window["load1"] > cores) or window["swapped_out"] > 0]
    spent = sum(window["duration_us"] for window in windows) or 1
    envelope = {
        "available": True,
        "absence": None,
        "samples": len(series),
        "cores": cores,
        "configured_capacity_cores": configured,
        "capacity_cores": binding,
        "busy_cores_p50": percentile(busy, 50),
        "busy_cores_p95": percentile(busy, 95),
        "busy_share_p50": round(percentile(busy, 50) / binding, 3),
        "busy_share_p95": round(percentile(busy, 95) / binding, 3),
        "underutilized_share": round(
            sum(window["duration_us"] for window in under) / spent, 3),
        "overcommitted_share": round(
            sum(window["duration_us"] for window in over) / spent, 3),
    }
    envelope["verdict"] = _verdict(envelope)
    envelope["headline"] = _headline(envelope)
    rank = ("lost_core_seconds", True)
    return {
        "envelope": envelope,
        "underutilized_intervals": _table(under, run, binding, rank),
        "overcommitted_intervals": _table(over, run, binding,
                                          ("busy_cores", True)),
    }


def _table(windows, run, binding, rank):
    key, descending = rank
    rows = [_row(window, run, binding) for window in windows]
    rows.sort(key=lambda row: row[key], reverse=descending)
    return rows[:INTERVALS_MAX]


#: The three answers, and the order they are tested in. Overcommit wins
#: over under-use because a build that is swapping is not short of
#: capacity, it is past it - and the remedy points the other way.
def _verdict(envelope: dict) -> str:
    if envelope["overcommitted_share"] > 0:
        return "overcommitted"
    if envelope["busy_share_p95"] >= 1.0:
        return "binding"
    return "not_binding"


def _headline(envelope: dict) -> str:
    """One line, with the numbers in it (`UX-220`'s rule)."""
    busy, cap = envelope["busy_cores_p95"], envelope["capacity_cores"]
    share = round(100 * envelope["busy_share_p50"])
    if envelope["verdict"] == "overcommitted":
        return (f"The host was overcommitted for "
                f"{round(100 * envelope['overcommitted_share'])}% of the "
                f"build - load above {envelope['cores']} cores or pages "
                f"written to swap. More builders will make it slower.")
    if envelope["verdict"] == "binding":
        return (f"Cores were the binding resource: busy reached {busy} of "
                f"{cap} and sat at {share}% of it. More cores, or less "
                f"work, is the only thing that shortens this build.")
    return (f"Cores were not the binding resource: busy peaked at {busy} of "
            f"{cap} and sat at {share}% of it, with "
            f"{round(100 * envelope['underutilized_share'])}% of the build "
            f"holding an idle core while there was work to run.")
