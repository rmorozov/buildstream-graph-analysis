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
from typing import Dict, List, Optional


# An element is "not compute-bound" below this many cores busy. One core
# means a build that never overlapped any work with anything - the
# `notparallel` signature - and real parallel elements in the reference
# capture sit at 1.6-2.1, so the gap between the two populations is wide
# and this sits in it rather than being tuned to either.
_COMPUTE_BOUND_CORES = 1.25

# How much of the critical path an element must hold before the join
# calls it out. Below this, a native-build finding is real but is not
# what to do next.
_CRITICAL_PATH_SHARE = 0.05

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
    blast_radius: Optional[int] = None
    # Plane 2
    cores_busy: Optional[float] = None
    cpu_coverage: Optional[float] = None
    requested_jobs: Optional[int] = None
    native_findings: List[str] = field(default_factory=list)
    unused_dependencies: List[str] = field(default_factory=list)
    # Synthesis
    recommendations: List[str] = field(default_factory=list)


def _plane1_view(analysis: dict) -> Dict[str, dict]:
    """Per-element Plane 1 facts, keyed by element UID."""
    structural = analysis.get("structural") or {}
    signals = analysis.get("signals") or {}
    sensitivity = structural.get("sensitivity") or {}
    critical_path = list(signals.get("critical_path") or [])
    critical_path_us = sensitivity.get("critical_path_us") or 0

    view: Dict[str, dict] = {}
    for element in critical_path:
        view.setdefault(element, {})["on_critical_path"] = True

    for entry in sensitivity.get("top_opportunities") or []:
        # (key, score, impact_pct); score is the fraction of the finish
        # this element could remove (UX-44).
        element, score = entry[0], entry[1]
        record = view.setdefault(element, {})
        record["critical_path_share"] = score
        record["potential_saving_us"] = int(score * critical_path_us)

    blast = signals.get("blast_radius") or {}
    for element, value in blast.items():
        count = value.get("downstream_count") if isinstance(value, dict) else value
        if count is not None:
            view.setdefault(element, {})["blast_radius"] = count

    return view


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

    return view


def _recommend(joined: ElementJoin) -> List[str]:
    """Turn one element's two-plane picture into directed next steps.

    Only fires where the join actually adds something. A Plane 2 finding
    on an element that holds no meaningful share of the critical path is
    true but is not what to do next, and saying so anyway is how a report
    becomes noise (the lesson of `UX-34` and `UX-37`).
    """
    steps: List[str] = []
    share = joined.critical_path_share

    # A share-based claim needs a real share. An element can sit on the
    # critical path and still be unable to move the finish - that is what
    # `UX-44` established, and it is why the gate is the measured saving
    # rather than mere membership. Rendering "holds 0% of the critical
    # path and is genuinely compute-bound" for such an element, as an
    # earlier version did, is a confident statement about nothing.
    matters = share is not None and share >= _CRITICAL_PATH_SHARE

    if matters and joined.cores_busy is not None:
        if joined.cores_busy < _COMPUTE_BOUND_CORES:
            detail = (
                f"holds {share * 100:.0f}% of the critical path but runs at only "
                f"{joined.cores_busy:.2f} cores busy - it is waiting, not computing"
            )
            if "pinned_to_one_job" in joined.native_findings:
                steps.append(
                    f"{detail}, and its native build asked for -j1: remove "
                    f"`notparallel` / raise its job count before touching its sources"
                )
            elif joined.requested_jobs and joined.requested_jobs > 1:
                steps.append(
                    f"{detail}, despite asking for -j{joined.requested_jobs}: its "
                    f"native build is not achieving the parallelism it requested"
                )
            else:
                steps.append(f"{detail}: look at how it is built before what it builds")
        else:
            # Deliberately phrased as a *negative* result. Its value is
            # ruling the micro plane out, so the reader stops looking
            # there - not as a thing to go and do.
            steps.append(
                f"holds {share * 100:.0f}% of the critical path and is already "
                f"compute-bound at {joined.cores_busy:.2f} cores busy - nothing to "
                f"gain from its parallelism; shortening it means less work"
            )

    if joined.unused_dependencies:
        count = len(joined.unused_dependencies)
        names = ", ".join(sorted(joined.unused_dependencies))
        plural = "dependency" if count == 1 else "dependencies"
        steps.append(
            f"declares {count} build {plural} it never read ({names}) - removing "
            f"the edge is free and widens the graph"
        )

    return steps


def correlate(analysis: dict, native_report: dict) -> dict:
    """Join a Plane 1 analysis with a Plane 2 native report.

    Both arguments are already-parsed artifacts - this function performs
    no IO and knows nothing about how either was produced, which is what
    keeps the two planes independently replaceable.
    """
    plane1 = _plane1_view(analysis)
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
            blast_radius=p1.get("blast_radius"),
            cores_busy=p2.get("cores_busy"),
            cpu_coverage=p2.get("cpu_coverage"),
            requested_jobs=p2.get("requested_jobs"),
            native_findings=p2.get("native_findings", []),
            unused_dependencies=p2.get("unused_dependencies", []),
        )
        entry.recommendations = _recommend(entry)
        joined.append(entry)

    # Ranked by what Plane 1 says is worth fixing, since that is the
    # question the user arrived with; Plane 2 explains the top of that
    # list rather than reordering it.
    joined.sort(key=lambda e: (-e.potential_saving_us, e.element))

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
        "coverage": {
            "joined_elements": len(covered),
            "plane1_elements": len(plane1),
            "plane2_elements": len(plane2),
            "plane1_only_with_impact": plane1_only,
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
    lines.append("")

    actionable = result["actionable"]
    if not actionable:
        lines.append("No element has a finding in both planes worth acting on.")
    else:
        lines.append("What to do next (ranked by Plane 1 impact):")
        # Capped with an overflow line, the same house pattern UX-33 uses:
        # a real project produces one of these per element, and a list
        # nobody reads to the end is a list that hid its own first item.
        for entry in actionable[:_SHOWN_MAX]:
            lines.append(f"  {entry['element']}:")
            for step in entry["recommendations"]:
                lines.append(f"    - {step}")
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
