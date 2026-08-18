"""UX-51: join Plane 1's "which elements matter" with Plane 2's "what
happened inside them".

The two planes have always been separate tools over separate artifacts,
and `docs/design-directions.md` named the seam between them as the
biggest remaining gap. This module closes it as an **explicit join**
rather than by merging the planes, on evidence measured before the
design was chosen:

- **One capture already produces both artifacts.** `UX-24`'s
  `bst_native_build_tracer.py run --wrapped-log` runs a single real
  `bst build` and emits a Plane 1 log and a Plane 2 report together, so a
  merged capture would buy nothing that is not already available.
- **The join key already exists on both sides and is exact.** Plane 1 is
  keyed by element UID; `UX-23` tags every traced process with its owning
  element. On a real dual capture of `examples/06`, 9 of 9 Plane 2
  elements matched Plane 1 UIDs with zero mismatches. The only Plane 1
  elements absent from Plane 2 were `all.bst` (a `stack`) and
  `toolchain.bst` (an `import`) - elements that run no build commands, so
  their absence is correct rather than a join failure.
- **The horizons genuinely cannot be merged.** `docs/architecture.md`
  argues this at length: Plane 2's timeline is one level down inside a
  single element's sandbox and shares no horizon with an element-level
  trace, so attribution cannot be reconciled across them even in
  principle. Anything that looked like a merge would be a join wearing a
  misleading name.

So the contract between the planes is one string - the element UID - and
this module is a third consumer that reads two finished artifacts and
neither plane knows about. That keeps each plane independently
improvable, which is the whole point of leaving it thin.

What the join produces is the thing neither plane can say alone: not
"`core.bst` is 24% of your critical path" (Plane 1) and not "`core.bst`
runs at 0.87 cores busy" (Plane 2), but **"the element that dominates
your critical path is not compute-bound, so fix how it is built, not what
it builds"**.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .findings import SEVERITY_HIGH, SEVERITY_INFO, SEVERITY_MEDIUM


# An element is "not compute-bound" below this many cores busy. One core
# means a build that never overlapped any work with anything - the
# `notparallel` signature - and real parallel elements in the reference
# capture sit at 1.6-2.1, so the gap between the two populations is wide
# and this sits in it rather than being tuned to either.
_COMPUTE_BOUND_CORES = 1.25

# How much of the *build* fixing an element must be worth before the join
# calls it out. Below this, a native-build finding is real but is not
# what to do next.
#
# `UX-71`: this used to read `sensitivity.top_opportunities`, whose score
# is `min(duration, next_binding_gap) / makespan` - a correct upper bound
# and a useless ranking, because the cap is a constant over exactly the
# population being ranked. On a real `freedesktop-sdk` capture all five
# candidates scored an identical 0.0316, so the order was decided by
# element name and this gate never opened for anything. The quantity is
# now `UX-70`'s realizable saving: what the build would actually lose if
# this element became instant.
_REALIZABLE_SAVING_SHARE = 0.05

# UX-72: one binary holding more than half an element's measured CPU is
# a majority, not a tuned threshold - it says "this element is a <binary>
# problem" and points at a different day's work from every other finding
# the join makes.
_DOMINANT_BINARY_SHARE = 0.5

# UX-72: a single process peaking above this much resident memory is
# where concurrent builders start to matter on an ordinary CI runner -
# round 9's host had 16 GB across 4 builders, so 4 GB each.
_PEAK_RSS_NOTABLE_MB = 1024

# UX-72: a redundant operation is worth naming in an element's row only
# when it is a real fraction of what fixing that element is worth at all.
# On the real capture `cmake-stage1` pays 2.2s for a shared `rm -rf`
# against 1569.8s of realizable saving - true, and noise in that row,
# while `doxygen` paying 20.4s of its 513.5s for a shared `m4` is not.
# The 1% floor is `UX-65`'s own "below this is rounding" bar.
_REDUNDANCY_NOTABLE_SHARE = 0.01
# Backstop for an element whose saving was never evaluated: a finding
# worth under a second is not a next action however it is measured.
_REDUNDANCY_NOTABLE_S = 1.0

# UX-72: evidence classes, strongest first. A measured 81%-of-CPU binary
# and an explicitly hedged dependency candidate must not print as two
# identically-weighted bullets - round 9's join printed eight rows that
# were all the second kind.
#
# UX-75: each class carries a stable id and a severity, so a consumer
# acts on `id` rather than on a substring of the prose, and so the rank
# that orders the text is the same fact the JSON publishes.
_EVIDENCE_PARALLELISM = 1
_EVIDENCE_CPU_CONCENTRATION = 2
_EVIDENCE_SERIALIZATION = 3
_EVIDENCE_MEMORY = 4
_EVIDENCE_REDUNDANCY = 5
_EVIDENCE_DECLARED_VS_USED = 6

_EVIDENCE_SEVERITY = {
    _EVIDENCE_PARALLELISM: SEVERITY_HIGH,
    _EVIDENCE_CPU_CONCENTRATION: SEVERITY_HIGH,
    _EVIDENCE_SERIALIZATION: SEVERITY_HIGH,
    _EVIDENCE_MEMORY: SEVERITY_MEDIUM,
    _EVIDENCE_REDUNDANCY: SEVERITY_MEDIUM,
    # UX-68: the producer's own words are "this is evidence, not a
    # verdict". Its severity says the same thing in a field a machine can
    # read.
    _EVIDENCE_DECLARED_VS_USED: SEVERITY_INFO,
}

# A finding below the gate above still earns a line when Plane 2 says the
# fix is cheap and specific - an element running at ~1 core busy is a job
# count, not a rewrite. `UX-65`'s own floor: below 1% of wall clock is
# rounding, not an opportunity, so that is where this stops too.
_CHEAP_WIN_FLOOR = 0.01

# How many elements the text report names before overflowing to JSON.
_SHOWN_MAX = 8


@dataclass
class ElementJoin:
    """One element, seen from both planes."""

    element: str
    # Plane 1
    on_critical_path: bool = False
    critical_path_share: Optional[float] = None
    potential_saving_us: int = 0
    # UX-71: `potential_saving_us` as a share of the whole build - the
    # quantity the recommendations are gated on. Kept beside the path
    # share rather than replacing it: "what this chain is made of" and
    # "what changing it is worth" are different facts and the report says
    # both.
    saving_share: Optional[float] = None
    blast_radius: Optional[int] = None
    # Plane 2
    cores_busy: Optional[float] = None
    cpu_coverage: Optional[float] = None
    requested_jobs: Optional[int] = None
    native_findings: List[str] = field(default_factory=list)
    unused_dependencies: List[str] = field(default_factory=list)
    # UX-72: the measurements the join used to read past. Each is
    # produced per element and was published to JSON for rounds without
    # ever reaching the command the workflow ends on.
    dominant_binary: Optional[dict] = None
    serial_binary: Optional[dict] = None
    peak_rss_kb: Optional[int] = None
    worst_redundancy: Optional[dict] = None
    redundancy_count: int = 0
    aggregating_dependencies: List[str] = field(default_factory=list)
    # Synthesis
    recommendations: List[str] = field(default_factory=list)


def _plane1_view(analysis: dict) -> Tuple[Dict[str, dict], str]:
    """Per-element Plane 1 facts, keyed by element UID.

    Returns the view and the name of the metric its `potential_saving_us`
    came from, because a reader who is handed a ranking is entitled to
    know what it was ranked on - and because the two available metrics
    are not equivalent (`UX-71`).
    """
    structural = analysis.get("structural") or {}
    signals = analysis.get("signals") or {}
    sensitivity = structural.get("sensitivity") or {}
    critical_path = list(signals.get("critical_path") or [])
    critical_path_us = sensitivity.get("critical_path_us") or 0
    total_us = analysis.get("total_duration_us") or 0

    view: Dict[str, dict] = {}
    for element in critical_path:
        view.setdefault(element, {})["on_critical_path"] = True

    # UX-70's per-element simulation, published on every critical-path
    # entry. Share of the path comes from here too: it is the same
    # quantity `bga analyze` prints, rather than the capped proxy, so the
    # two commands cannot describe the same element differently.
    detail = signals.get("critical_path_detail") or []
    realizable: Dict[str, int] = {}
    for entry in detail:
        element = entry.get("element_uid")
        if not element:
            continue
        record = view.setdefault(element, {})
        if entry.get("share_of_path") is not None:
            record["critical_path_share"] = entry["share_of_path"]
        saving = entry.get("realizable_saving_us")
        if saving is not None:
            realizable[element] = int(saving)

    if realizable:
        metric = "realizable_saving_us"
        for element, saving in realizable.items():
            record = view.setdefault(element, {})
            record["potential_saving_us"] = saving
            record["saving_share"] = (saving / total_us) if total_us else None
    else:
        # An artifact analysed by a `bga` older than UX-70 carries no
        # simulation. Fall back to the capped proxy rather than refusing
        # to join - degraded, not broken - and say which one was used.
        metric = "sensitivity_score"
        for entry in sensitivity.get("top_opportunities") or []:
            # (key, score, impact_pct); score is the fraction of the
            # finish this element could remove (UX-44).
            element, score = entry[0], entry[1]
            record = view.setdefault(element, {})
            record.setdefault("critical_path_share", score)
            record["potential_saving_us"] = int(score * critical_path_us)
            record["saving_share"] = score

    blast = signals.get("blast_radius") or {}
    for element, value in blast.items():
        count = value.get("downstream_count") if isinstance(value, dict) else value
        if count is not None:
            view.setdefault(element, {})["blast_radius"] = count

    return view, metric


def _plane2_view(native_report: dict) -> Dict[str, dict]:
    """Per-element Plane 2 facts, keyed by the same element UID."""
    view: Dict[str, dict] = {}

    for entry in native_report.get("per_element_parallelism") or []:
        element = entry.get("element")
        if not element:
            continue
        view.setdefault(element, {}).update(
            {
                "requested_jobs": entry.get("requested_jobs"),
                "native_findings": list(entry.get("findings") or []),
            }
        )

    cpu_time = native_report.get("cpu_time") or {}
    for element, entry in (cpu_time.get("per_element") or {}).items():
        record = view.setdefault(element, {})
        record["cores_busy"] = entry.get("cpu_per_wall_second")
        record["cpu_coverage"] = entry.get("coverage")

    declared = native_report.get("declared_vs_used") or {}
    for entry in declared.get("unused_candidates") or []:
        view.setdefault(entry["element"], {}).setdefault(
            "unused_dependencies", []
        ).append(entry["dependency"])
    # UX-72: `UX-68` filtered these out of the candidate list three
    # rounds ago and nothing has read them since - no renderer, no
    # consumer. Carried here so the join can say how much it set aside,
    # rather than leaving the filtered population visible only to someone
    # reading the raw JSON.
    for entry in declared.get("aggregating_dependencies") or []:
        view.setdefault(entry["element"], {}).setdefault(
            "aggregating_dependencies", []
        ).append(entry["dependency"])

    # UX-69: where an element's CPU actually went, and whether any of it
    # sat in a single unparallelisable process.
    for element, entry in (native_report.get("binary_cost") or {}).items():
        if not entry.get("available"):
            continue
        record = view.setdefault(element, {})
        by_cpu = entry.get("by_cpu") or []
        if by_cpu:
            record["dominant_binary"] = by_cpu[0]
        serial = [s for s in (entry.get("single_process_costs") or []) if s.get("wall_s")]
        if serial:
            record["serial_binary"] = max(serial, key=lambda s: s["wall_s"])

    # UX-63: the largest single process's resident memory.
    for element, entry in ((native_report.get("peak_memory") or {}).get(
        "per_element"
    ) or {}).items():
        if entry.get("peak_rss_kb"):
            view.setdefault(element, {})["peak_rss_kb"] = entry["peak_rss_kb"]

    # UX-23/UX-73: cross-element repeats, attributed to the element that
    # paid the most for them. Only the worst one per element is carried:
    # the join names a next action, not a catalogue.
    for finding in native_report.get("redundant_operations") or []:
        worst = finding.get("worst_element")
        if not worst:
            continue
        record = view.setdefault(worst, {})
        record["redundancy_count"] = record.get("redundancy_count", 0) + 1
        current = record.get("worst_redundancy")
        if current is None or (finding.get("max_element_duration_s") or 0) > (
            current.get("max_element_duration_s") or 0
        ):
            record["worst_redundancy"] = finding

    return view


def _recommend(joined: ElementJoin) -> List[str]:
    """Turn one element's two-plane picture into directed next steps.

    Only fires where the join actually adds something. A Plane 2 finding
    on an element that holds no meaningful share of the critical path is
    true but is not what to do next, and saying so anyway is how a report
    becomes noise (the lesson of `UX-34` and `UX-37`).
    """
    # (evidence rank, id, text) - sorted at the end so the strongest
    # measured finding leads and the hedged one never displaces it.
    ranked: List[tuple] = []
    share = joined.critical_path_share
    worth = joined.saving_share

    # A claim about impact needs a real measure of impact. An element can
    # sit on the critical path and still be unable to move the finish -
    # that is what `UX-44` established and what `UX-70` measured - which
    # is why the gate is the saving rather than mere membership.
    # Rendering "holds 0% of the critical path and is genuinely
    # compute-bound" for such an element, as an earlier version did, is a
    # confident statement about nothing.
    matters = worth is not None and worth >= _REALIZABLE_SAVING_SHARE
    # UX-71: an element the gate excludes is not automatically silent.
    # Worth is only half of "low-hanging fruit"; the other half is how
    # cheap the fix is, and ~1 core busy is the one Plane 2 signal that
    # names a cheap fix outright. On the real capture this is the
    # difference between reporting `bison.bst` (0.91 cores busy, worth
    # 4.0% of the build, fixable by a job-count setting) and saying
    # nothing about it at all.
    cheap_win = (
        not matters
        and worth is not None
        and worth >= _CHEAP_WIN_FLOOR
        and joined.cores_busy is not None
        and joined.cores_busy < _COMPUTE_BOUND_CORES
    )

    def _impact() -> str:
        parts = []
        if share is not None:
            parts.append(f"holds {share * 100:.0f}% of the critical path")
        if worth is not None and joined.potential_saving_us:
            parts.append(
                f"fixing it is worth {joined.potential_saving_us / 1e6:.1f}s "
                f"({worth * 100:.1f}% of the build)"
            )
        return " and ".join(parts) if parts else "on the critical path"

    if (matters or cheap_win) and joined.cores_busy is not None:
        if joined.cores_busy < _COMPUTE_BOUND_CORES:
            detail = (
                f"{_impact()}, but runs at only {joined.cores_busy:.2f} cores "
                f"busy - it is waiting, not computing"
            )
            if "pinned_to_one_job" in joined.native_findings:
                ranked.append((_EVIDENCE_PARALLELISM, 'pinned-to-one-job',
                    f"{detail}, and its native build asked for -j1: remove "
                    f"`notparallel` / raise its job count before touching its sources"))
            elif joined.requested_jobs and joined.requested_jobs > 1:
                ranked.append((_EVIDENCE_PARALLELISM, 'underachieved-requested-jobs',
                    f"{detail}, despite asking for -j{joined.requested_jobs}: its "
                    f"native build is not achieving the parallelism it requested"))
            else:
                ranked.append((_EVIDENCE_PARALLELISM, 'waiting-not-computing',
                    f"{detail}: look at how it is built before what it builds"))
        else:
            # Deliberately phrased as a *negative* result. Its value is
            # ruling the micro plane out, so the reader stops looking
            # there - not as a thing to go and do.
            ranked.append((_EVIDENCE_PARALLELISM, 'already-compute-bound',
                f"{_impact()} - already compute-bound at "
                f"{joined.cores_busy:.2f} cores busy, so there is nothing to gain "
                f"from its parallelism; shortening it means less work"))

    # UX-72: the measurements the join used to read past. Gated on the
    # same "is this what to do next" question as the block above - a
    # per-element CPU breakdown for an element worth 0.1% of the build is
    # true and is not a next step.
    if matters or cheap_win:
        dominant = joined.dominant_binary
        if dominant and (dominant.get("cpu_share") or 0) >= _DOMINANT_BINARY_SHARE:
            ranked.append((_EVIDENCE_CPU_CONCENTRATION, 'cpu-concentration',
                f"{dominant['cpu_share']:.0%} of its measured CPU is one binary, "
                f"`{dominant['binary']}` ({dominant['count']} process(es), "
                f"{dominant['cpu_us'] / 1e6:.0f} CPU s) - this element is a "
                f"`{dominant['binary']}` problem, so look there before anywhere else"))

        serial = joined.serial_binary
        if serial:
            ranked.append((_EVIDENCE_SERIALIZATION, 'serialization-point',
                f"`{serial['binary']}` is a SINGLE process holding "
                f"{serial['wall_s']:.1f}s of wall time - a serialization point no "
                f"job count can help; it has to get faster or go away"))

        if joined.peak_rss_kb and joined.peak_rss_kb / 1024 >= _PEAK_RSS_NOTABLE_MB:
            ranked.append((_EVIDENCE_MEMORY, 'peak-memory',
                f"its largest single process peaked at "
                f"{joined.peak_rss_kb / 1024:.0f} MB resident - multiply by however "
                f"many elements build concurrently before raising `builders`"))

        redundancy = joined.worst_redundancy
        redundancy_s = (redundancy or {}).get("max_element_duration_s") or 0
        floor_s = max(
            _REDUNDANCY_NOTABLE_S,
            joined.potential_saving_us / 1e6 * _REDUNDANCY_NOTABLE_SHARE,
        )
        if redundancy and redundancy_s >= floor_s:
            others = [e for e in redundancy.get("elements", []) if e != joined.element]
            ranked.append((_EVIDENCE_REDUNDANCY, 'redundant-operation',
                f"it pays {redundancy_s:.1f}s for an operation {len(others)} other "
                f"element(s) also run ({redundancy['occurrence_count']}x in total): "
                f"{redundancy.get('signature', '').strip()[:60]}"))

    if joined.unused_dependencies:
        count = len(joined.unused_dependencies)
        names = ", ".join(sorted(joined.unused_dependencies))
        plural = "dependency" if count == 1 else "dependencies"
        # UX-68: the producer says "this is evidence, not a verdict" -
        # runtime-only dependencies, cached configure probes and
        # directory-existence dependencies are all indistinguishable
        # from here. Rendering that as "removing the edge is free" turned
        # a measurement into a claim the measurement does not support,
        # and on a real capture it did so for 8 of 10 findings.
        ranked.append((_EVIDENCE_DECLARED_VS_USED, 'declared-not-used',
            f"opened no file staged by {count} declared build {plural} "
            f"({names}) - worth checking whether the edge is needed at "
            f"build time, or only at runtime; this is evidence, not a "
            f"verdict (a runtime-only dependency looks identical here)"))

    return [
        {'id': id, 'severity': _EVIDENCE_SEVERITY[rank], 'text': text}
        for rank, id, text in sorted(ranked, key=lambda item: item[0])
    ]


def correlate(analysis: dict, native_report: dict) -> dict:
    """Join a Plane 1 analysis with a Plane 2 native report.

    Both arguments are already-parsed artifacts - this function performs
    no IO and knows nothing about how either was produced, which is what
    keeps the two planes independently replaceable.
    """
    plane1, ranking_metric = _plane1_view(analysis)
    plane2 = _plane2_view(native_report)

    joined: List[ElementJoin] = []
    for element in sorted(set(plane1) | set(plane2)):
        p1 = plane1.get(element, {})
        p2 = plane2.get(element, {})
        entry = ElementJoin(
            element=element,
            on_critical_path=p1.get("on_critical_path", False),
            critical_path_share=p1.get("critical_path_share"),
            potential_saving_us=p1.get("potential_saving_us", 0),
            saving_share=p1.get("saving_share"),
            blast_radius=p1.get("blast_radius"),
            cores_busy=p2.get("cores_busy"),
            cpu_coverage=p2.get("cpu_coverage"),
            requested_jobs=p2.get("requested_jobs"),
            native_findings=p2.get("native_findings", []),
            unused_dependencies=p2.get("unused_dependencies", []),
            dominant_binary=p2.get("dominant_binary"),
            serial_binary=p2.get("serial_binary"),
            peak_rss_kb=p2.get("peak_rss_kb"),
            worst_redundancy=p2.get("worst_redundancy"),
            redundancy_count=p2.get("redundancy_count", 0),
            aggregating_dependencies=p2.get("aggregating_dependencies", []),
        )
        entry.recommendations = _recommend(entry)
        joined.append(entry)

    # Ranked by what Plane 1 says is worth fixing, since that is the
    # question the user arrived with; Plane 2 explains the top of that
    # list rather than reordering it.
    joined.sort(key=lambda e: (-e.potential_saving_us, e.element))

    # UX-71: a metric that is constant over the ranked population does
    # not rank it, and the tie was previously broken by element name and
    # presented as impact order. Detected rather than assumed away: any
    # metric can saturate on some graph, and a reader must be told when
    # theirs did.
    ranked_savings = {e.potential_saving_us for e in joined if e.potential_saving_us > 0}
    ranking_degenerate = len(ranked_savings) == 1 and sum(
        1 for e in joined if e.potential_saving_us > 0
    ) > 1

    covered = [e for e in joined if e.cores_busy is not None]
    plane1_only = [
        e.element for e in joined if e.cores_busy is None and e.potential_saving_us > 0
    ]

    # UX-56: Plane 2 tags processes with an element name derived from
    # bwrap's `--dir`, which is the element only under BuildStream's
    # default build-root layout. On a real `freedesktop-sdk` capture,
    # 99.4% of 127,630 processes landed in one bucket named
    # `buildstream-build`, so the join key on this side was not an
    # element UID at all and every "joined" row was meaningless. The
    # producer now says so; refuse the join rather than render it.
    attribution = native_report.get("element_attribution") or {}
    attribution_unreliable = (
        attribution.get("note") if attribution.get("reliable") is False else None
    )
    # UX-66: a partial attribution is not an unreliable one. When the
    # names present are real but do not cover every process, the join is
    # correct for the elements it names and silent about the rest - so it
    # is rendered with its coverage stated, the way `UX-45` publishes
    # measured CPU time and `UX-63` measured memory. Refusing here is
    # reserved for the case where the names themselves are fiction.
    attribution_partial = (
        attribution.get("note")
        if attribution.get("reliable") and attribution.get("unattributed_processes")
        else None
    )

    return {
        "elements": [vars(e) for e in joined],
        "actionable": (
            [] if attribution_unreliable
            else [vars(e) for e in joined if e.recommendations]
        ),
        "attribution_unreliable": attribution_unreliable,
        "attribution_partial": attribution_partial,
        "ranking": {
            "metric": ranking_metric,
            "degenerate": ranking_degenerate,
            "tied_saving_us": (
                next(iter(ranked_savings)) if ranking_degenerate else None
            ),
        },
        "coverage": {
            "joined_elements": len(covered),
            "plane1_elements": len(plane1),
            "plane2_elements": len(plane2),
            "plane1_only_with_impact": plane1_only,
            # UX-72: `UX-68` set these aside as unprovable and nothing
            # has looked at them since. Counted here so the filtered
            # population is visible rather than merely absent.
            "aggregating_dependency_pairs": sum(
                len(e.aggregating_dependencies) for e in joined
            ),
        },
        "note": (
            "Joined on element UID - the only contract between the two planes. "
            "Elements present in Plane 1 but not Plane 2 either ran no build "
            "commands (a `stack`/`import`) or were not traced; they are listed "
            "rather than assumed to be fine. The two planes' timelines are not "
            "merged and cannot be: Plane 2 measures inside one element's sandbox "
            "and shares no horizon with an element-level trace."
        ),
    }


def format_correlation(result: dict) -> str:
    """Human-readable join, leading with what to do next."""
    lines = ["=" * 60, "Two-Plane Correlation", "=" * 60]
    # UX-56: said before the join, because it invalidates it.
    if result.get("attribution_unreliable"):
        lines.append("NO USABLE JOIN: Plane 2's element attribution is unreliable.")
        lines.append(f"  {result['attribution_unreliable']}")
        lines.append("")
        lines.append(
            "  The join key on the Plane 2 side is not an element UID, so no row "
            "below would mean anything. Nothing is recommended from this pair of "
            "artifacts."
        )
        lines.append("=" * 60)
        return "\n".join(lines)
    # UX-66: stated before the rows, because it scopes them.
    if result.get("attribution_partial"):
        lines.append("PARTIAL ATTRIBUTION - the rows below are correct for the")
        lines.append("elements they name, and say nothing about the rest:")
        lines.append(f"  {result['attribution_partial']}")
        lines.append("")
    coverage = result["coverage"]
    lines.append(
        f"Joined {coverage['joined_elements']} element(s) on element UID "
        f"({coverage['plane1_elements']} in Plane 1, "
        f"{coverage['plane2_elements']} traced in Plane 2)"
    )
    if coverage["plane1_only_with_impact"]:
        lines.append(
            "  Not traced, but Plane 1 says they matter: "
            + ", ".join(coverage["plane1_only_with_impact"])
        )
    # UX-72: `UX-68` filtered these out for good reason - a dependency
    # that stages almost nothing of its own cannot be shown unused by
    # nobody reading it - but a filtered population that is never
    # mentioned is indistinguishable from one that does not exist.
    if coverage.get("aggregating_dependency_pairs"):
        lines.append(
            f"  {coverage['aggregating_dependency_pairs']} further dependency "
            f"pair(s) set aside as aggregating - they stage almost nothing of "
            f"their own, so 'nobody opened it' says nothing about them (UX-68); "
            f"see --format json for the list"
        )
    lines.append("")

    actionable = result["actionable"]
    if not actionable:
        lines.append("No element has a finding in both planes worth acting on.")
    else:
        lines.append("What to do next (ranked by Plane 1 impact):")
        # UX-71: said before the rows, because it tells the reader
        # whether the order below means anything.
        ranking = result.get("ranking") or {}
        if ranking.get("degenerate"):
            tied = ranking.get("tied_saving_us")
            tied_text = f" ({tied / 1e6:.1f}s)" if tied else ""
            lines.append(
                f"  NOTE: every ranked element carries the same Plane 1 "
                f"impact{tied_text}, so the order below is alphabetical, not an "
                f"impact ranking - read the rows, not their positions"
            )
        # Capped with an overflow line, the same house pattern UX-33 uses:
        # a real project produces one of these per element, and a list
        # nobody reads to the end is a list that hid its own first item.
        for entry in actionable[:_SHOWN_MAX]:
            lines.append(f"  {entry['element']}:")
            for step in entry["recommendations"]:
                lines.append(f"    - {step['text']}")
            if entry["cpu_coverage"] is not None and entry["cpu_coverage"] < 1.0:
                lines.append(
                    f"    ({entry['cpu_coverage'] * 100:.0f}% of this element's "
                    f"processes were measured)"
                )
        if len(actionable) > _SHOWN_MAX:
            lines.append(
                f"  (+{len(actionable) - _SHOWN_MAX} more element(s) with findings, "
                f"see --format json)"
            )
    lines.append("")
    lines.append(f"({result['note']})")
    lines.append("=" * 60)
    return "\n".join(lines)
