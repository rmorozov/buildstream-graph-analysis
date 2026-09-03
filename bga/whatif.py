"""UX-230: what if you could choose the fixes.

`UX-219` draws the published optimization plan as the fixed sequence the
pipeline projects. The fourth external review's sketch - checkboxes,
pick your subset, see the projected build - is the interaction R8 brings
to a prioritisation meeting, and its own warning is the constraint:
**this must not pretend to simulate.**

A page that summed per-element savings would be wrong the moment two
fixes share a chain, which is exactly why the pipeline's projection
exists. `UX-219` measured the gap on the golden fixture: the published
`makespan_after_us` differs from `total - cumulative_saving_us` at every
step. So the arithmetic lives here, in the same
`compute_joint_saving` `bga analyze` already calls, and the page asks
rather than computes - the transport pattern `bga blast` established.

What this refuses, and why:

- **An element the graph does not know.** Named rather than dropped: a
  subset silently missing a member projects a different question from
  the one that was asked.
- **An element with no measured duration.** Zeroing an unmeasured
  element is not a projection, it is a guess about a number nobody
  took.
- **An empty selection.** Zero elements is not "no change projected",
  it is no question - and the two read very differently beside a
  makespan.

The convention is `UX-74`'s and unchanged: *fixed* means the element
becomes instant, over this run's measured durations, with nothing else
about the build assumed to change. It is an upper bound, not a
forecast, and the payload says so.
"""
from typing import Dict, List, Sequence

from . import schemas
from .report import rate

# What `fixed` means here, published with every answer so a figure that
# travels keeps its assumption attached.
CONVENTION = (
    "A structural projection over this run's measured durations: "
    "\"fixed\" means the element becomes instant and nothing else about "
    "the build changes. An upper bound on what the selection can be "
    "worth, not a forecast - a re-capture is still the ground truth."
)


def project(result, graph, elements: Sequence[str]) -> dict:
    """`whatif/v1`: what the build drops to if all of `elements` were
    fixed together.

    Takes the analysed result and the graph rather than a run directory,
    so the page's transport and `bga whatif` reach the same function
    with the same inputs - the property the acceptance asserts
    byte-for-byte. The graph is a separate argument because
    `AnalysisResult` does not carry one: it is the analyzer's, and
    passing it explicitly is better than a second load that could
    disagree with the durations beside it.
    """
    from .graph.edg import compute_critical_path, compute_joint_saving

    durations = _durations(result)
    selected = [str(uid) for uid in elements]

    refusals = _refusals(graph, durations, selected)
    document = {
        "run_id": getattr(result, 'run_id', None),
        "selected": selected,
        "total_duration_us": getattr(result, 'total_duration_us', None),
        "convention": CONVENTION,
        "refusals": refusals,
        "projected": None,
    }
    if refusals or graph is None:
        return schemas.stamp(document, schemas.WHATIF)

    baseline, _path = compute_critical_path(graph, durations)
    saving = compute_joint_saving(graph, durations, selected)
    document["projected"] = {
        "baseline_makespan_us": int(baseline),
        "joint_saving_us": int(saving),
        "makespan_after_us": int(baseline) - int(saving),
        # The number a page would otherwise reach for, published beside
        # the real one so the difference is visible rather than
        # reproduced: this is what "just adding the savings" would say.
        "sum_of_individual_us": _sum_of_individual(graph, durations, selected),
    }
    return schemas.stamp(document, schemas.WHATIF)


def _durations(result) -> Dict[str, int]:
    durations = (getattr(result, 'signals', None) or {}).get('element_durations')
    return dict(durations or {})


def _sum_of_individual(graph, durations, selected) -> int:
    """What each element is worth *alone*, added up.

    Published as the wrong answer, deliberately. `UX-219`'s Out of Scope
    section says a page must not add savings; publishing the sum beside
    the joint projection is how a reader sees *why* - on a shared chain
    the two differ, and the difference is the whole finding.
    """
    from .graph.edg import compute_realizable_savings

    savings = compute_realizable_savings(graph, durations, list(selected))
    return int(sum(savings.get(uid, 0) for uid in selected))


def _refusals(graph, durations, selected) -> List[dict]:
    if not selected:
        return [{"check": "empty_selection",
                 "elements": [],
                 "sentence": "No elements selected: that is not a question "
                             "about this build, and a makespan beside it "
                             "would read as an answer."}]
    known = {getattr(element, 'uid', element)
             for element in (getattr(graph, 'elements', None) or [])}
    known |= set(durations)
    unknown = [uid for uid in selected if uid not in known]
    if unknown:
        return [{"check": "unknown_element", "elements": unknown,
                 "sentence": f"Not in this run's graph: {', '.join(unknown)}. "
                             f"A subset quietly missing a member projects a "
                             f"different question from the one asked."}]
    unmeasured = [uid for uid in selected if not durations.get(uid)]
    if unmeasured:
        return [{"check": "no_measured_duration", "elements": unmeasured,
                 "sentence": f"No measured duration: {', '.join(unmeasured)}. "
                             f"Zeroing an unmeasured element is a guess about "
                             f"a number nobody took, not a projection."}]
    return []


def render(document: dict) -> List[str]:
    """The answer as text. One renderer, so `bga whatif` and
    `bga whatif --format json` cannot describe one selection two ways."""
    chosen = ", ".join(document["selected"]) or "(nothing selected)"
    lines = [f"What if these were fixed: {chosen}"]
    for refusal in document.get("refusals") or []:
        lines.append(f"  Refused: {refusal['sentence']}")
    projected = document.get("projected")
    if projected:
        lines.append(
            f"  Makespan {projected['baseline_makespan_us'] / 1e6:.3f}s -> "
            f"{projected['makespan_after_us'] / 1e6:.3f}s "
            f"(saves {projected['joint_saving_us'] / 1e6:.3f}s)")
        if projected["sum_of_individual_us"] != projected["joint_saving_us"]:
            # Not "they share a chain": the sum can also be *larger*
            # than the joint figure when the elements sit on parallel
            # branches and the projection takes a maximum. Which of the
            # two holds is a property of this graph, and the numbers
            # beside each other say it without the renderer guessing.
            lines.append(
                f"  Their individual savings add up to "
                f"{projected['sum_of_individual_us'] / 1e6:.3f}s, which is "
                f"not what they are worth together "
                f"({projected['joint_saving_us'] / 1e6:.3f}s) - what one "
                f"fix is worth depends on the others.")
        lines.extend(_in_your_units(projected))
        lines.append(f"  {document['convention']}")
    return lines


def _in_your_units(projected: dict) -> List[str]:
    """`UX-611`: the projected saving in the unit the reader decides in.

    Through `report.rate` - the converter the headline and the plan
    already call - so a saving is priced by one rule and not two.
    """
    supplied = rate.supplied()
    if supplied is None:
        return []
    if supplied.get("error"):
        # Named rather than swallowed: silence here is indistinguishable
        # from having supplied no rate at all.
        return [f"  In your units: not applied: {supplied['error']}"]
    saving_us = projected["joint_saving_us"]
    return [f"  In your units: saves {saving_us / 1e6:.3f}s = "
            f"{rate.phrase(saving_us, supplied)}",
            f"    {rate.preamble(supplied)}"]
