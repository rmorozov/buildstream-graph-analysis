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
from typing import Dict, List, Optional

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


def percentile(samples: List[float], p: float) -> Optional[float]:
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


def distribution(samples: List[float]) -> Optional[dict]:
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
_FIELD_SUFFIX = {"cpu_count": " cores", "memory_mb": " MB"}


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


def _resource_profile(snapshot: str, manifest: Optional[dict]) -> dict:
    """This run's two capacity facts from Plane 2, or an empty dict.

    `cores_busy` comes from `correlate.summarize_plane2_capacity`, the
    same function the capacity hint is conditioned on, so the aggregate
    and the per-run advice cannot disagree about how busy a host was.
    Peak RSS is a **maximum over processes**, never a sum - two
    processes that peaked at different moments never held the total
    between them (`UX-63`).
    """
    import json

    path = os.path.join(snapshot, "plane2.json")
    try:
        with open(path, encoding="utf-8") as handle:
            report = json.load(handle)
    except (OSError, ValueError):
        return {}

    from .correlate import summarize_plane2_capacity

    profile = {}
    summary = summarize_plane2_capacity(
        report, (manifest or {}).get("cpu_count")) or {}
    if summary.get("cores_busy") is not None:
        profile["cores_busy"] = summary["cores_busy"]
    per_element = ((report.get("peak_memory") or {}).get("per_element")) or {}
    peaks = [entry.get("peak_rss_kb") for entry in per_element.values()
             if entry.get("peak_rss_kb")]
    if peaks:
        profile["peak_rss_mb"] = max(peaks) / 1024
    return profile


def _class_aggregate(label: str, manifest: Optional[dict],
                     rows: List[dict]) -> dict:
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
        "peak_rss_mb": distribution(
            [row["resource"]["peak_rss_mb"] for row in rows
             if "peak_rss_mb" in (row.get("resource") or {})]),
        "stamps": [row["stamp"] for row in rows],
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


def _excluded(rows: List[dict]) -> dict:
    """Why each unusable snapshot was left out, counted by reason.

    `UX-156`: a build that did not finish is not a sample, and a
    distribution that silently dropped it would claim a cleaner store
    than the one on disk.
    """
    reasons: Dict[str, int] = {}
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
AGGREGATE_READS = ("analyze/v1", "store/v1")


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


def _contract_composition(rows: List[dict]) -> dict:
    """Which contract sets this store holds, and which one is current.

    Published whichever way the rule falls: "we aggregated thirty runs"
    and "we aggregated thirty runs written under two different
    definitions of the fields" are different claims.
    """
    seen: Dict[tuple, int] = {}
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

    by_class: Dict[str, List[dict]] = {}
    manifests: Dict[str, Optional[dict]] = {}
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
            row, resource=_resource_profile(row.get("path") or "", manifest)))

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
             ("duration_us", "cache_hit_rate", "cores_busy", "peak_rss_mb")},
            runs=classes[0]["runs"], mixes=1)
    return schemas.stamp(document, schemas.STORE_AGGREGATE)


def _blended(by_class: Dict[str, List[dict]]) -> dict:
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
        "peak_rss_mb": distribution(
            [row["resource"]["peak_rss_mb"] for row in every
             if "peak_rss_mb" in (row.get("resource") or {})]),
    }


def render(document: dict) -> List[str]:
    """The aggregate as text. One renderer, so `--aggregate` and
    `--aggregate --format json` cannot describe one store two ways."""
    lines = [f"Store: {document.get('project')}",
             f"  {document['measured']} measured run(s) of "
             f"{document['snapshots']} snapshot(s)"]
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
    ("peak_rss_mb", "Peak RSS", 1, " MB"),
)


def _distribution_lines(entry: dict) -> List[str]:
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
    from tools.bga_snapshot import store_listing

    return aggregate(store_listing(project), blend=blend)


