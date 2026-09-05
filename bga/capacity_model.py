"""UX-595: builders and the store's measured service times, as a model.

`UX-234` published the fact base - min/median/p95/max/MAD per host
class - and said the model was the next task. This is it: a builder
count and an arrival rate turned into utilization and waiting.

The rule it is built to is that **every number prints the assumptions
its own arithmetic used**. They are recorded by `_Assumed.on` where
they enter the computation rather than listed beside it afterwards, so
a number cannot acquire an assumption the printout does not carry.

Measured and assumed are kept apart on purpose. The service-time
distribution is this store's own finished runs - mean and squared
coefficient of variation from the same samples `UX-234` takes its
percentiles from. The arrival *process* is assumed and measured by
nothing: no store yet carries the request instants `UX-594` records,
and the rate is the operator's own number.

The wait is Allen-Cunneen's M/G/c approximation - the M/M/c wait
scaled by `(CV_a^2 + CV_s^2) / 2`. Plain M/M/c would assume an
exponential service time that the store can measure and contradict,
which is the shape `UX-129` calls worse than a refusal.
"""
import statistics
from typing import Optional

from . import schemas, store_aggregate
from .compare import MIN_BASELINE_RUNS

MICROSECONDS_PER_DAY = 86_400_000_000

# Every assumption this model can lean on, and the sentence printed
# where it does. A number's `assumes` list is built from these ids as
# the arithmetic touches them, and `render` prints the sentence under
# the number - so the two cannot describe the model differently.
ASSUMPTIONS = {
    "arrival_rate_declared":
        "The arrival rate is the one you passed. bga measures no "
        "arrival rate: a store records when builds ran.",
    "arrivals_poisson":
        "Arrivals are Poisson - independent, memoryless, at a constant "
        "long-run rate, squared coefficient of variation 1. Nothing "
        "here measures that. `UX-594` records a request instant where "
        "a CI system offers one; no store carries enough of them yet.",
    "whole_arrival_stream":
        "This store holds more than one host class, and each model "
        "below sends the whole arrival stream to builders of its own "
        "class. A fleet that splits the stream waits less than this.",
    "service_is_the_store":
        "The service-time distribution is this store's finished runs "
        "on this host class - what the fleet builds is assumed to be "
        "what this store built.",
    "finished_runs_only":
        "A failed, interrupted or suspended capture is not a sample "
        "and is excluded from the service time (`UX-156`).",
    "service_general":
        "The service time is not assumed exponential. The M/M/c wait "
        "is scaled by (CV_a^2 + CV_s^2)/2 - Allen-Cunneen - which is "
        "an approximation, exact at one builder and asymptotically.",
    "servers_interchangeable":
        "The builders are interchangeable, and a build holds one of "
        "them for its whole duration.",
    "steady_state":
        "A long-run average of a system at equilibrium. A morning "
        "burst against an idle afternoon is not this number.",
    "fifo_no_priority":
        "One queue, first come first served: no priorities, no "
        "batching, no reordering.",
    "per_host_class":
        "Modelled per host class and never across them - durations "
        "are not scaled between machines (`UX-186`).",
    "littles_law":
        "The queue length is Little's law on the wait above: "
        "Lq = arrival rate x wait.",
}


class _Assumed:
    """What one number's arithmetic leaned on, in the order it did."""

    def __init__(self):
        self.ids: list[str] = []

    def on(self, name: str) -> None:
        if name not in ASSUMPTIONS:
            raise KeyError(f"{name!r} is not a declared assumption")
        if name not in self.ids:
            self.ids.append(name)


def erlang_c(builders: int, load: float) -> float:
    """The probability an arrival waits at all, M/M/c at `load` erlangs.

    From the recurrence rather than from factorials, which overflow at
    a fleet size a spreadsheet reaches before a datacentre does.
    """
    if load >= builders:
        return 1.0
    term, total = 1.0, 1.0
    for k in range(1, builders + 1):
        term *= load / k
        total += term
    busy = term * builders / (builders - load)
    return busy / (total - term + busy)


def service_time(samples: list[float]) -> dict:
    """The first two moments of a measured service time.

    `UX-234` publishes a median and a MAD because a robust centre is
    what a reader comparing two host classes wants. A queue is not
    that reader: waiting is a function of the *mean* and of the spread
    around it, so both are computed here from the same samples rather
    than reached for in a document that declined to publish them.
    """
    mean = statistics.fmean(samples)
    stdev = statistics.stdev(samples) if len(samples) > 1 else 0.0
    return {
        "samples": len(samples),
        "mean_us": mean,
        "stdev_us": stdev,
        # The squared coefficient of variation - the one shape number
        # Allen-Cunneen needs, and the one that says how far this store
        # is from the exponential M/M/c would have assumed (1.0).
        "cv2": (stdev / mean) ** 2 if mean else 0.0,
    }


def _answer(name: str, value, quantity: str, assumed: _Assumed) -> dict:
    return {"name": name, "value": value, "quantity": quantity,
            "assumes": list(assumed.ids)}


def _class_model(label: str, samples: list[float], builders: int,
                 arrivals_per_day: float, mixed: bool) -> dict:
    """One host class's utilization and waiting, or why there is none."""
    entry = {"host_class": label, "runs": len(samples), "service": None,
             "answers": [], "shortfall": None, "refusal": None}
    if len(samples) < MIN_BASELINE_RUNS:
        entry["shortfall"] = {
            "have": len(samples), "need": MIN_BASELINE_RUNS,
            "sentence": (
                f"{len(samples)} finished run(s) on {label}: "
                f"{MIN_BASELINE_RUNS} are needed before a service time "
                f"means anything, so this class is not modelled."),
        }
        return entry

    service = service_time(samples)
    entry["service"] = service

    base = _Assumed()
    base.on("per_host_class")
    if mixed:
        base.on("whole_arrival_stream")
    base.on("finished_runs_only")
    base.on("service_is_the_store")
    base.on("arrival_rate_declared")
    base.on("servers_interchangeable")
    base.on("steady_state")

    rate_us = arrivals_per_day / MICROSECONDS_PER_DAY
    load = rate_us * service["mean_us"]
    utilization = load / builders
    entry["answers"].append(
        _answer("utilization", utilization, "share", base))

    if utilization >= 1:
        entry["refusal"] = {
            "check": "unstable_queue",
            "sentence": (
                f"{arrivals_per_day:g} build(s)/day of "
                f"{service['mean_us'] / 1e6:.1f}s each need "
                f"{load:.2f} builder(s) and there are {builders}: the "
                f"queue grows without bound, so no wait is published. "
                f"A finite one would be a number about a system that "
                f"does not reach equilibrium."),
        }
        return entry

    wait = _Assumed()
    for name in base.ids:
        wait.on(name)
    wait.on("arrivals_poisson")
    wait.on("fifo_no_priority")
    # Allen-Cunneen: the M/M/c wait, corrected for a service time the
    # store measured rather than one the formula wished for.
    mmc_wait_us = (erlang_c(builders, load)
                   / (builders / service["mean_us"] - rate_us))
    wait.on("service_general")
    wait_us = mmc_wait_us * (1.0 + service["cv2"]) / 2.0
    entry["answers"].append(_answer("wait_us", wait_us, "duration_us", wait))

    queue = _Assumed()
    for name in wait.ids:
        queue.on(name)
    queue.on("littles_law")
    entry["answers"].append(
        _answer("queue_length", rate_us * wait_us, "count", queue))
    return entry


def model(listing: dict, builders: int, arrivals_per_day: float) -> dict:
    """Utilization and waiting per host class, over one `store/v1`.

    Takes the listing for the reason `store_aggregate.aggregate` does:
    the fact base and the model must not be able to describe different
    sets of snapshots.
    """
    if builders < 1:
        raise ValueError("builders must be at least 1")
    if arrivals_per_day <= 0:
        raise ValueError("the arrival rate must be greater than 0")

    by_class: dict[str, list[float]] = {}
    excluded = 0
    for row in listing.get("snapshots") or []:
        if row.get("incomplete_reason") or row.get("total_duration_us") is None:
            excluded += 1
            continue
        label = row.get("host_class") or store_aggregate.UNKNOWN_HOST_CLASS
        by_class.setdefault(label, []).append(row["total_duration_us"])

    mixed = len(by_class) > 1
    classes = [_class_model(label, by_class[label], builders,
                            arrivals_per_day, mixed)
               for label in sorted(by_class)]
    document = {
        # `UX-613`: first key, so a consumer reading the head of a
        # truncated document learns what it is before it interprets
        # anything.
        "schema": schemas.CAPACITY_MODEL,
        "project": listing.get("project"),
        "builders": builders,
        "arrivals_per_day": arrivals_per_day,
        "excluded_runs": excluded,
        "host_classes": classes,
        "refusal": None,
    }
    if mixed:
        names = ", ".join(entry["host_class"] for entry in classes)
        document["refusal"] = {
            "check": "cross_host_model",
            "classes": len(classes),
            "sentence": (
                f"This store holds finished runs from {len(classes)} host "
                f"classes ({names}). A queue over a mix of machines is a "
                f"queue over two service times, so no fleet-wide number "
                f"is published: each class below is modelled as if it "
                f"served the whole stream."),
        }
    return document


def _used(document: dict) -> list[str]:
    """Every assumption some number in this document leaned on."""
    seen: list[str] = []
    for entry in document.get("host_classes") or []:
        for answer in entry.get("answers") or []:
            for name in answer.get("assumes") or []:
                if name not in seen:
                    seen.append(name)
    return seen


_UNITS = {
    "utilization": ("Utilization", lambda v: f"{v * 100:.1f}% of "
                                             f"{{builders}} builder(s)"),
    "wait_us": ("Wait before a build starts", lambda v: f"{v / 1e6:.1f}s"),
    "queue_length": ("Builds waiting", lambda v: f"{v:.2f}"),
}


def _wrapped(prefix: str, body: str, indent: str) -> list[str]:
    import textwrap

    return textwrap.wrap(body, width=72, initial_indent=prefix,
                         subsequent_indent=indent) or [prefix.rstrip()]


def render(document: dict) -> list[str]:
    """The model as text: every number names what its own arithmetic
    assumed, and the legend states each of those once.

    Named beside the number and stated below rather than stated beside
    it - eleven sentences repeated under three numbers is a printout
    nobody reads, and an assumption nobody reads is not published.
    """
    lines = [f"Store: {document.get('project')}",
             f"  {document['builders']} builder(s), "
             f"{document['arrivals_per_day']:g} build(s)/day"]
    if document.get("excluded_runs"):
        lines.append(f"  {document['excluded_runs']} run(s) excluded: "
                     f"not a finished build, so not a service time")
    for entry in document.get("host_classes") or []:
        lines += ["", f"  {entry['host_class']} - {entry['runs']} run(s)"]
        if entry.get("shortfall"):
            lines += _wrapped("    ", entry["shortfall"]["sentence"], "    ")
            continue
        service = entry["service"]
        lines.append(
            f"    Service time: mean {service['mean_us'] / 1e6:.1f}s, "
            f"sd {service['stdev_us'] / 1e6:.1f}s, "
            f"CV^2 {service['cv2']:.2f}, n={service['samples']}")
        for answer in entry["answers"]:
            label, form = _UNITS[answer["name"]]
            shown = form(answer["value"]).format(builders=document["builders"])
            lines.append(f"    {label}: {shown}")
            lines += _wrapped("      assumes ", ", ".join(answer["assumes"]),
                              "              ")
        if entry.get("refusal"):
            lines += _wrapped("    ", entry["refusal"]["sentence"], "    ")
    used = _used(document)
    if used:
        lines += ["", "  Assumptions, each named above by the numbers that "
                      "rest on it:"]
        for name in used:
            lines += _wrapped(f"    {name}: ", ASSUMPTIONS[name], "      ")
    if document.get("refusal"):
        lines += ["", ""] + _wrapped("  ", document["refusal"]["sentence"],
                                     "  ")
    return lines


def read(project: str, builders: int, arrivals_per_day: float) -> dict:
    """The model for a project's store, from its own listing."""
    # `UX-325`: through `_import_tool`, because the directory is
    # `tools/` in a checkout and `bga._tools` in a wheel.
    from .tools_dispatch import _import_tool

    store_listing = _import_tool("tools.bga_snapshot").store_listing
    return model(store_listing(project), builders, arrivals_per_day)


def parse_capacity(text: str) -> Optional[tuple]:
    """`N,M` - builders and builds per day - or `None`.

    One flag rather than two because they are one question, and
    `bga snapshot --help` is at its line cap (`UX-158`).
    """
    parts = [part.strip() for part in (text or "").split(",")]
    if len(parts) != 2:
        return None
    try:
        builders, arrivals = int(parts[0]), float(parts[1])
    except ValueError:
        return None
    if builders < 1 or arrivals <= 0:
        return None
    return builders, arrivals
