"""UX-234: the store speaks for more than one build.

Direction 9's anchor. Every question R5 (capacity) and R7 (release) ask
begins with a distribution `bga` already holds the samples for and never
aggregates: a store of captures **is** a measured service-time
distribution with host manifests, hit rates and resource profiles
attached, and until this its only cross-run reading was a trend line of
medians.

What this is not:

- **Not a model.** No queueing, no arrival rates, no cost translation,
  no normalisation across machines. `UX-129`'s standing lesson is that a
  model dressed as a measurement is worse than a refusal, and `UX-186`
  already declined to scale durations across hosts. The capacity model
  is the *next* task and deserves its own argued filing.
- **Not continuous.** It reads a store on demand, like every other
  command.

Two honesty rules decide most of the shape:

- **A run that did not finish is not a sample.** `UX-156`: a failed,
  interrupted or suspended capture is excluded from every distribution
  and *counted* where it was excluded, because "we had nine runs" and
  "we had nine runs and threw two away" are different claims.
- **A mix of machines is not a distribution.** `UX-186`'s grammar: runs
  are grouped by the host class its `COMPARED_FIELDS` already
  distinguish, and a blended figure across classes is refused rather
  than printed. `--blend` prints it under an explicit request, which is
  the caller taking the claim rather than the tool making it.

The percentile definition is **nearest-rank**, stated because a
percentile without its definition is not reproducible: for `n` sorted
samples, `p` is the value at index `ceil(p * n) - 1`. On 20 samples the
p95 is the 19th; on 3 it is the 3rd. No interpolation, so every figure
here is a value the store actually measured - which is the same reason
`compute_band` uses a median and a MAD rather than a mean.
"""
import math
import os
import statistics
from typing import Optional

from . import hostinfo, run_store, schemas
from .compare import MIN_BASELINE_RUNS

# The class a run belongs to when its capture predates `UX-186`'s
# manifest. Named rather than dropped: "we do not know which machine"
# and "the same machine" are different, and an aggregate that quietly
# merged them would be exactly the blend this module refuses.
UNKNOWN_HOST_CLASS = "unknown host"

# Which percentiles the contract publishes. p95 because that is the
# question R7 asks by name; min/max because a distribution's ends are
# what a capacity argument is actually about.
PERCENTILES = (50, 95)

# `UX-528`: how many stamps a class entry names. The document is a
# *distribution*; the run list beside it grew with the store and nothing
# read it as a list - `render()` prints the counts, and the trend plots
# `store/v1`'s own rows. The same window the page takes, so "which runs
# is this class" and "which runs are drawn" cannot answer differently.
STAMPS_MAX = 12

# `UX-565`: how many runs of a class Part 29's variability reads. The
# same window the element card's sparkline draws (`element.js`'s
# `HISTORY_POINTS_MAX`), so the figure and the line above it cannot be
# about different runs.
HISTORY_RUNS_MAX = 12


def percentile(samples: list[float], p: float) -> Optional[float]:
    """Nearest-rank percentile - a value the store measured, not one
    between two of them.

    Interpolation would invent a duration no build ever took, which is
    a small lie in a document whose whole claim is that it aggregates
    measurements.
    """
    if not samples:
        return None
    ordered = sorted(samples)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def distribution(samples: list[float]) -> Optional[dict]:
    """`min/median/p95/max/MAD`, or `None` below the sample floor.

    The floor is `compare.MIN_BASELINE_RUNS`, the same one the noise
    band refuses under. Two runs define no distribution, and a p95 of
    two samples is the larger of the two wearing a statistic's name.
    """
    if len(samples) < MIN_BASELINE_RUNS:
        return None
    ordered = sorted(samples)
    median = statistics.median(ordered)
    return {
        "samples": len(ordered),
        "min": ordered[0],
        "median": median,
        "p95": percentile(ordered, 95),
        "max": ordered[-1],
        # The same robust spread `compute_band` is built on, published
        # unscaled: a reader comparing two host classes wants the
        # dispersion, not a band's half-width.
        "mad": statistics.median([abs(x - median) for x in ordered]),
    }


# How each of `hostinfo.COMPARED_FIELDS` reads in a class label. A
# field with no entry here still groups - it is appended as
# `name=value` - so adding one to `COMPARED_FIELDS` widens the grouping
# immediately and only costs the label its polish, which is the right
# way round for a guard nobody remembers to update.
_FIELD_SUFFIX = {"cpu_count": " cores", "memory_bytes": " B"}


def host_class(manifest: Optional[dict]) -> str:
    """The label two runs must share to be aggregated together.

    Built by walking `hostinfo.COMPARED_FIELDS` - the fields a
    difference in which moves durations - so this grouping and `bga
    compare`'s cross-host refusal cannot disagree about what "the same
    machine" means. Human-readable rather than a hash, because it ends
    up in a refusal sentence a person has to act on.
    """
    if not manifest:
        return UNKNOWN_HOST_CLASS
    parts = []
    for field in hostinfo.COMPARED_FIELDS:
        value = manifest.get(field)
        if value is None:
            parts.append(f"unknown {field}")
        elif field in _FIELD_SUFFIX:
            parts.append(f"{value}{_FIELD_SUFFIX[field]}")
        elif field == "cpu_model":
            parts.append(str(value))
        else:
            parts.append(f"{field}={value}")
    return " · ".join(parts)


def _manifest_of(snapshot: str) -> Optional[dict]:
    """The host manifest a snapshot's run context recorded, or None."""
    import json

    path = os.path.join(snapshot, run_store.RUN_SUBDIR, "run-context.json")
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle).get("host_manifest")
    except (OSError, ValueError):
        return None


def _resource_profile(row: dict) -> dict:
    """This run's two capacity facts, off the row the listing built.

    **`UX-296`: this used to `json.load` the snapshot's whole
    `plane2.json`.** Once per snapshot, on every view of *any* run, to
    reach two floats - measured 1.17 GB of resident memory to view a
    2 MB neighbour of one big capture, and on a store of fewer than
    three runs it paid that and then published null distributions
    because there was nothing to distribute.

    The numbers are unchanged and so is where they come from:
    `correlate.resource_profile` computes them from the report's own
    aggregates, and the capture writes them beside the report
    (`run_store.write_resource_profile`) at the one moment it has the
    document in memory. This reads the row.

    `{}` for a snapshot captured before that sidecar existed - which
    `_class_aggregate` names, rather than reaching for the big file.
    """
    return dict(row.get("resource") or {})


def _class_aggregate(label: str, manifest: Optional[dict],
                     rows: list[dict]) -> dict:
    """One host class's distributions, or its shortfall."""
    durations = [row["total_duration_us"] for row in rows]
    entry = {
        "host_class": label,
        "host_manifest": manifest,
        "runs": len(rows),
        "duration_us": distribution(durations),
        "cache_hit_rate": distribution(
            [row["cache_hit_rate"] for row in rows
             if row.get("cache_hit_rate") is not None]),
        "cores_busy": distribution(
            [row["resource"]["cores_busy"] for row in rows
             if "cores_busy" in (row.get("resource") or {})]),
        "peak_rss_bytes": distribution(
            [row["resource"]["peak_rss_bytes"] for row in rows
             if "peak_rss_bytes" in (row.get("resource") or {})]),
        # UX-300: what these runs cost on disk. The rows have carried
        # `bytes` since `UX-159` and nothing read them, so a store whose
        # snapshots grew from kilobytes to gigabytes said nothing about
        # it here - the one place that reads a whole store at once.
        # A distribution rather than a total alone, because "the median
        # capture is 4.7 MB and the p95 is 2.1 GB" is the reading that
        # names the run worth looking at.
        "snapshot_bytes": distribution(
            [row["bytes"] for row in rows if row.get("bytes")]),
        "total_bytes": sum(row.get("bytes") or 0 for row in rows),
        # `UX-528`: capped. This is one entry per run per host class,
        # and nothing reads it as a list - the trend plots `store/v1`'s
        # rows. At 100 runs it was the whole of this document's growth.
        "stamps": [row["stamp"] for row in rows][-STAMPS_MAX:],
        "stamps_total": len(rows),
    }
    # UX-296: a class whose runs carry no capacity scalars says why, and
    # what produces them. The old code reached into every snapshot's
    # `plane2.json` for these; a capture written before the sidecar has
    # them nowhere cheap, and "absent" must not read as "measured at
    # zero" or as "this run had no Plane 2".
    if entry["cores_busy"] is None and entry["peak_rss_bytes"] is None:
        entry["resource_shortfall"] = {
            "have": sum(1 for row in rows if row.get("resource")),
            "runs": len(rows),
            "sentence": (
                "No capacity scalars for this class: they are written "
                "beside the Plane 2 report at capture time, and these "
                "snapshots predate that or recorded no Plane 2. "
                "`bga snapshot -- bst build TARGET` writes them for the "
                "next run; nothing re-reads an old capture to find them."),
        }
    if entry["duration_us"] is None:
        # Named, not silent. `UX-114`'s shortfall shape: what is missing
        # and how much of it, so a reader knows whether to wait for two
        # more runs or to look somewhere else.
        entry["shortfall"] = {
            "have": len(rows),
            "need": MIN_BASELINE_RUNS,
            "sentence": (
                f"{len(rows)} finished run(s) on {label}: "
                f"{MIN_BASELINE_RUNS} are needed before a distribution "
                f"means anything, so none is published for this class."),
        }
    return entry


def _excluded(rows: list[dict]) -> dict:
    """Why each unusable snapshot was left out, counted by reason.

    `UX-156`: a build that did not finish is not a sample, and a
    distribution that silently dropped it would claim a cleaner store
    than the one on disk.
    """
    reasons: dict[str, int] = {}
    for row in rows:
        if row.get("incomplete_reason"):
            reasons[str(row["incomplete_reason"])] = (
                reasons.get(str(row["incomplete_reason"]), 0) + 1)
        elif row.get("total_duration_us") is None:
            reasons["no recorded duration"] = (
                reasons.get("no recorded duration", 0) + 1)
    return {"count": sum(reasons.values()), "by_reason": reasons}


# UX-253: the contract set a snapshot was written under.
#
# **The argument.** `UX-234` refuses to blend across *host classes* and
# publishes per-class figures instead, because durations from a fast
# machine and a slow one are incomparable - the numbers mean different
# things. A **contract set** is not that, and treating it the same way
# would be a rule nobody argued:
#
# - A host class partitions the runs into populations that must not be
#   pooled. Two contract sets do not: if every contract this document
#   *reads* is unchanged, the runs are comparable whatever else moved -
#   which is exactly the rule `UX-250` settled for the two-run case,
#   and refusing on the version number instead would fire on every
#   upgrade, including the thirty rounds that moved no contract at all.
# - What a moved read-contract does is make a run's fields absent or
#   differently defined. That is an **exclusion**, not an
#   incomparability: the run cannot be read, rather than being read and
#   meaning something else.
#
# So the many-run rule is the two-run rule applied to a set: aggregate
# the runs whose read-contracts agree with the newest state, exclude
# the rest *by the same mechanism an interrupted capture is excluded* -
# counted, named, with a reason - and publish the composition either
# way, because a reader cannot evaluate an aggregate whose composition
# is invisible.
#
# The minority is defined against the **newest** state rather than by
# count or by age: the newest is the one the reader is holding.
AGGREGATE_READS = ("analyze/v2", "store/v1")   # UX-288


def _contract_set_of(snapshot: str) -> Optional[tuple]:
    """The contracts the producer of this snapshot declared, or `None`.

    `None` means unstamped - every artifact written before `UX-249`
    is, and that absence reads as an explicit unknown rather than as
    agreement.
    """
    import json

    path = os.path.join(snapshot, run_store.RUN_SUBDIR, "report.json")
    try:
        with open(path, encoding="utf-8") as handle:
            producer = json.load(handle).get("producer")
    except (OSError, ValueError):
        return None
    ids = (producer or {}).get("contracts")
    return tuple(sorted(ids)) if ids else None


def _contract_composition(rows: list[dict]) -> dict:
    """Which contract sets this store holds, and which one is current.

    Published whichever way the rule falls: "we aggregated thirty runs"
    and "we aggregated thirty runs written under two different
    definitions of the fields" are different claims.
    """
    seen: dict[tuple, int] = {}
    unstamped = 0
    for row in rows:
        found = _contract_set_of(row.get("path") or "")
        if found is None:
            unstamped += 1
        else:
            seen[found] = seen.get(found, 0) + 1
    sets = [{"contracts": list(contracts), "runs": count}
            for contracts, count in sorted(seen.items(), key=lambda kv: -kv[1])]
    return {
        "sets": sets,
        "unstamped_runs": unstamped,
        # The contracts this document actually reads. A set that moved
        # one of these makes its runs unreadable here; a set that moved
        # anything else does not, and saying so is the whole point of
        # naming them.
        "reads": list(AGGREGATE_READS),
        "mixed": len(sets) > 1,
    }


def aggregate(listing: dict, blend: bool = False) -> dict:
    """A `store-aggregate/v1` document over one `store/v1` listing.

    Takes the listing rather than the directory so the two documents
    cannot describe different sets of snapshots - the same reason
    `provenance.attach` reads the finished analyze document.
    """
    project = listing.get("project")
    rows = list(listing.get("snapshots") or [])
    usable, unusable = [], []
    for row in rows:
        if row.get("incomplete_reason") or row.get("total_duration_us") is None:
            unusable.append(row)
        else:
            usable.append(row)

    by_class: dict[str, list[dict]] = {}
    manifests: dict[str, Optional[dict]] = {}
    for row in usable:
        # The label is on the row (the listing computed it once); the
        # full manifest is read here, once per class, because a reader
        # asking "which machine is that" wants the kernel and the
        # distro too and the listing deliberately does not carry them.
        label = row.get("host_class") or UNKNOWN_HOST_CLASS
        manifest = manifests.get(label)
        if label not in manifests:
            manifest = _manifest_of(row.get("path") or "")
            manifests[label] = manifest
        by_class.setdefault(label, []).append(dict(
            row, resource=_resource_profile(row)))

    classes = [_class_aggregate(label, manifests[label], by_class[label])
               for label in sorted(by_class)]

    document = {
        "project": project,
        "snapshots": len(rows),
        "measured": len(usable),
        "excluded": _excluded(unusable),
        # UX-253: what this aggregate is made of, in contract terms.
        "contract_composition": _contract_composition(usable),
        "host_classes": classes,
        # UX-300: what the whole store weighs, at the document level and
        # not inside `blended`. Every other blended figure is refused
        # across host classes because a duration measured on two
        # machines is two populations (`UX-186`); a byte is a byte, and
        # a reader asking what their disk is holding must not have to
        # pass `--blend` to be told. Over **every** snapshot, including
        # the ones excluded from the distributions - a failed capture
        # is not a sample but it is still on the disk.
        "store_bytes": {
            "total": sum(row.get("bytes") or 0 for row in rows),
            "snapshots": len(rows),
            "measured_total": sum(row.get("bytes") or 0 for row in usable),
            "note": "Bytes on disk under `.bga/runs`, over every snapshot "
                    "this store holds - a capture excluded from the "
                    "distributions above for failing or being interrupted "
                    "still occupies its disk. `bga snapshot prune` says "
                    "what deleting would recover.",
        },
        "blended": None,
        "refusal": None,
    }

    if len(classes) > 1:
        names = ", ".join(entry["host_class"] for entry in classes)
        refusal = {
            "check": "cross_host_aggregate",
            "classes": len(classes),
            "sentence": (
                f"This store holds finished runs from {len(classes)} host "
                f"classes ({names}). Durations are not scaled across "
                f"machines here and should not be, so a blended "
                f"distribution is not published: read the per-class "
                f"figures, or pass --blend to state the mixed claim "
                f"yourself."),
        }
        document["refusal"] = refusal
        if blend:
            document["blended"] = _blended(by_class)
            document["blended"]["mixes"] = len(classes)
    elif classes:
        # One class is not a mix, so the blended figure *is* the answer
        # and there is nothing to refuse.
        document["blended"] = dict(
            {k: classes[0][k] for k in
             ("duration_us", "cache_hit_rate", "cores_busy", "peak_rss_bytes",
              "snapshot_bytes", "total_bytes")},
            runs=classes[0]["runs"], mixes=1)
    return schemas.stamp(document, schemas.STORE_AGGREGATE)


def _blended(by_class: dict[str, list[dict]]) -> dict:
    every = [row for rows in by_class.values() for row in rows]
    return {
        "runs": len(every),
        "duration_us": distribution(
            [row["total_duration_us"] for row in every]),
        "cache_hit_rate": distribution(
            [row["cache_hit_rate"] for row in every
             if row.get("cache_hit_rate") is not None]),
        "cores_busy": distribution(
            [row["resource"]["cores_busy"] for row in every
             if "cores_busy" in (row.get("resource") or {})]),
        "peak_rss_bytes": distribution(
            [row["resource"]["peak_rss_bytes"] for row in every
             if "peak_rss_bytes" in (row.get("resource") or {})]),
        # UX-300: disk is the one figure that *does* blend across host
        # classes without lying. A duration measured on two machines is
        # two populations (`UX-186`); a byte is a byte, and the question
        # "what does this store weigh" has one answer whatever built it.
        "snapshot_bytes": distribution(
            [row["bytes"] for row in every if row.get("bytes")]),
        "total_bytes": sum(row.get("bytes") or 0 for row in every),
    }


def render(document: dict) -> list[str]:
    """The aggregate as text. One renderer, so `--aggregate` and
    `--aggregate --format json` cannot describe one store two ways."""
    from .run_store import human_bytes

    lines = [f"Store: {document.get('project')}",
             f"  {document['measured']} measured run(s) of "
             f"{document['snapshots']} snapshot(s)"]
    # UX-300: what it weighs, on the second line, because a store that
    # has quietly reached tens of gigabytes is a fact about the machine
    # before it is a fact about any build.
    store_bytes = document.get("store_bytes") or {}
    if store_bytes.get("total"):
        lines.append(f"  {human_bytes(store_bytes['total'])} on disk")
    excluded = document.get("excluded") or {}
    if excluded.get("count"):
        lines.append(f"  {excluded['count']} excluded:")
        for reason, count in sorted(excluded.get("by_reason", {}).items()):
            lines.append(f"    {count} x {reason}")
    for entry in document.get("host_classes") or []:
        lines.append("")
        lines.append(f"  {entry['host_class']} - {entry['runs']} run(s)")
        if entry.get("shortfall"):
            lines.append(f"    {entry['shortfall']['sentence']}")
            continue
        lines.extend(_distribution_lines(entry))
    refusal = document.get("refusal")
    if refusal:
        lines += ["", f"  {refusal['sentence']}"]
    blended = document.get("blended")
    if blended and (blended.get("mixes") or 1) > 1:
        lines += ["", f"  Blended across {blended['mixes']} host classes, "
                      f"at your request:"]
        lines.extend(_distribution_lines(blended))
    return lines


_FIGURES = (
    ("duration_us", "Duration", 1e6, "s"),
    ("cache_hit_rate", "Cache hit rate", 0.01, "%"),
    ("cores_busy", "Cores busy", 1, ""),
    ("peak_rss_bytes", "Peak RSS", 1024 * 1024, " MB"),
    # UX-300: in MiB, beside the other per-run figures, because the
    # question "which capture is the big one" is answered by a p95
    # against a median and not by a total.
    ("snapshot_bytes", "Snapshot size", 1024 ** 2, " MiB"),
)


def _distribution_lines(entry: dict) -> list[str]:
    lines = []
    for key, label, divisor, unit in _FIGURES:
        shape = entry.get(key)
        if not shape:
            continue
        lines.append(
            f"    {label}: min {shape['min'] / divisor:.1f}{unit}, "
            f"median {shape['median'] / divisor:.1f}{unit}, "
            f"p95 {shape['p95'] / divisor:.1f}{unit}, "
            f"max {shape['max'] / divisor:.1f}{unit} "
            f"(MAD {shape['mad'] / divisor:.1f}{unit}, n={shape['samples']})")
    return lines


def read(project: str, blend: bool = False) -> dict:
    """The aggregate for a project's store, from its own listing."""
    # `UX-325`: through `_import_tool`, not `from tools.…`. The
    # directory is `tools/` in a checkout and `bga._tools` in a wheel
    # (`UX-94`), so an absolute `tools.` import resolves only where the
    # author happened to be working - which is why this line ran in
    # every test and never once on a user's machine.
    from .tools_dispatch import _import_tool

    store_listing = _import_tool("tools.bga_snapshot").store_listing
    return aggregate(store_listing(project), blend=blend)


def _snapshot_of(run_dir: Optional[str]) -> Optional[str]:
    """The store snapshot `run_dir` is the run of, or `None`.

    Structural, not a guess: `<project>/.bga/runs/<stamp>/run` is the
    layout `capture-layout/v1` declares, so a directory that does not
    sit in it is a run analysed outside a store and has no history.
    """
    if not run_dir:
        return None
    run = os.path.abspath(run_dir)
    if os.path.basename(run) != run_store.RUN_SUBDIR:
        return None
    snapshot = os.path.dirname(run)
    project = run_store.project_root(snapshot)
    if not project:
        return None
    if os.path.dirname(snapshot) != os.path.abspath(run_store.runs_dir(project)):
        return None
    return snapshot


def element_history(run_dir: Optional[str],
                    measured: Optional[dict[str, int]]) -> Optional[dict]:
    """Per-element duration series for the run at `run_dir`, or `None`.

    `UX-565`. Part 29 needed a history and one existed: `UX-226` writes
    a bounded per-element slice beside every snapshot and the page
    already draws it as a sparkline. This is those rows, as samples.

    One host class - this run's - because `UX-186`'s refusal is not
    suspended by asking the question per element: a duration measured
    on another machine is a different population, not another sample.

    This run's own sample is `measured`, not its slice: `bga snapshot`
    analyses (`tools/bga_snapshot.py:543`) *before* it writes the slice
    (`:548`), so a series read from the store alone would hold one
    fewer sample at capture time than on any later `bga analyze` of the
    same snapshot.

    `None` below `MIN_BASELINE_RUNS` for every element - the floor
    `distribution` refuses under, because a spread over two runs is two
    numbers wearing a statistic's name.
    """
    from .tools_dispatch import _import_tool

    snapshot = _snapshot_of(run_dir)
    if not snapshot or not measured:
        return None
    project = run_store.project_root(snapshot)
    listing = _import_tool("tools.bga_snapshot").store_listing(project)
    rows = list(listing.get("snapshots") or [])
    stamp = os.path.basename(snapshot)
    here = next((row for row in rows if row.get("stamp") == stamp), None)
    # `UX-156`: a run that did not finish is not a sample, and this run
    # is one of the samples.
    if here is None or here.get("incomplete_reason"):
        return None
    label = here.get("host_class") or UNKNOWN_HOST_CLASS

    prior: dict[str, list[int]] = {}
    runs = 0
    for row in rows:
        if row.get("stamp", "") >= stamp or row.get("incomplete_reason"):
            continue
        if (row.get("host_class") or UNKNOWN_HOST_CLASS) != label:
            continue
        runs += 1
        for entry in row.get("elements") or []:
            uid, value = entry.get("element_uid"), entry.get("duration_us")
            if uid in measured and isinstance(value, int):
                prior.setdefault(uid, []).append(value)

    durations = {}
    for uid, value in measured.items():
        window = (prior.get(uid) or []) + [int(value)]
        if len(window) >= MIN_BASELINE_RUNS:
            durations[uid] = window[-HISTORY_RUNS_MAX:]
    if not durations:
        return None
    return {"host_class": label, "runs": runs + 1, "durations": durations}


