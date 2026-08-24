"""UX-51: join Plane 1's "which elements matter" with Plane 2's "what
happened inside them".

The two planes have always been separate tools over separate artifacts,
and `docs/design/directions.md` named the seam between them as the
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
- **The horizons genuinely cannot be merged.** `docs/design/architecture.md`
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

# UX-89: the same bar, applied to the single-process serialization rule,
# which had none. `ar` and `ranlib` are single processes by construction,
# so on `examples/06` every one of the six libs and `app.bst` earned an
# identical "`ranlib` is a SINGLE process holding 0.1s of wall time - a
# serialization point no job count can help" line. A tenth of a second
# inside a two-second element is how `ar` works, not a finding.
#
# `UX-72`'s materiality bar is relative, and the absolute backstop is
# what actually removes this case: a serialization point worth under a
# second is not a next action at any scale, and on a large element the
# 1% share raises the bar further rather than lowering it.
_SERIALIZATION_NOTABLE_SHARE = _REDUNDANCY_NOTABLE_SHARE
_SERIALIZATION_NOTABLE_S = 1.0

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
    # Whether Plane 1's declared graph knows this element at all. False
    # means Plane 2 produced a name that looks like an element and is
    # not one (`UX-66`), so nothing may be recommended for it.
    declared: bool = True
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


def _declared_elements(analysis: dict) -> set:
    """Every element UID Plane 1 knows about, from the declared graph.

    `UX-66` required that "a bucket name that is not a declared element
    uid never enters a join, even if it ends in `.bst`" - because round 7
    measured `flit_core` and `expat` arriving as bwrap `--dir` segments
    where neither is an element. The producer's own check is the
    syntactic one (`assess_element_attribution`: a name ends in `.bst`),
    which is all Plane 2 can do on its own; the *declared graph* is a
    Plane 1 fact, so this is the only place the stronger check can be
    made.

    Built from the per-element signals rather than from the critical path
    alone: a real element that is off the path and has no blast radius
    still belongs to the graph, and refusing it would be a worse error
    than the one being fixed. An analysis carrying none of these signals
    yields an empty set, and the caller then skips the check rather than
    rejecting everything.
    """
    signals = analysis.get("signals") or {}
    known: set = set()
    for key in ("slack", "downstream_count", "blast_radius", "criticality_probability"):
        value = signals.get(key)
        if isinstance(value, dict):
            known |= set(value)
    known |= set(signals.get("critical_path") or [])
    for entry in signals.get("critical_path_detail") or []:
        uid = entry.get("element_uid")
        if uid:
            known.add(uid)
    return known


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


# UX-82: an unread edge is only worth restructuring around if it is
# holding the build up. Both endpoints on the critical path is the
# cheapest honest filter - the projection below then tells the truth
# about what removing them is actually worth, so this bound only has to
# be *permissive enough*, not exact.
def _unread_gating_edges(analysis: dict, native_report: dict) -> List[tuple]:
    """`(predecessor, successor)` build edges measured never-read that
    also sit on the critical path.

    The producer reports `{element, dependency}` where `element` is the
    consumer, so the graph edge runs `dependency -> element`.
    """
    declared = native_report.get("declared_vs_used") or {}
    on_path = set((analysis.get("signals") or {}).get("critical_path") or [])
    known = _declared_elements(analysis)
    edges = []
    for entry in declared.get("unused_candidates") or []:
        predecessor, successor = entry.get("dependency"), entry.get("element")
        if not predecessor or not successor:
            continue
        if known and (predecessor not in known or successor not in known):
            continue
        if predecessor in on_path and successor in on_path:
            edges.append((predecessor, successor))
    return sorted(set(edges))


def _connected_edge_groups(edges: List[tuple]) -> List[List[tuple]]:
    """Group edges that share an endpoint.

    Five separately-hedged rows saying "`lib-b` never read `lib-a`" are
    five bricks; one group saying "these six elements form a chain whose
    every internal edge is unread" is the wall (`UX-82`).
    """
    parent: Dict[str, str] = {}

    def find(node: str) -> str:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for predecessor, successor in edges:
        union(predecessor, successor)
    groups: Dict[str, List[tuple]] = {}
    for edge in edges:
        groups.setdefault(find(edge[0]), []).append(edge)
    return [sorted(group) for _root, group in sorted(groups.items())]


def project_without_edges(
    tasks, run_context, edges: List[tuple], capacities: Optional[dict] = None,
) -> Optional[dict]:
    """Replay the observed run with `edges` deleted from the graph.

    Same durations, same capacity, same deterministic scheduler - only
    the shape changes. A pure longest-path recomputation would be
    cheaper and wrong here: removing five chain edges lets six elements
    become ready at once, and what happens next is decided by how many
    builders there are, not by the chain that no longer exists.

    Returns None when there is nothing to replay, rather than a zero that
    would read as "this change saves everything".
    """
    from dataclasses import replace

    from .floors.capacity import compute_default_capacities
    from .replay.scheduler import ReplayScheduler

    if not tasks:
        return None
    removed = set(edges)
    element_of = {str(task.task_key): task.task_key.element_uid for task in tasks}

    def keep(successor_key: str, dependency_key: str) -> bool:
        pair = (element_of.get(dependency_key), element_of.get(successor_key))
        return pair not in removed

    rewired = [
        replace(
            task,
            dependencies=[
                dep for dep in task.dependencies if keep(str(task.task_key), dep)
            ],
        )
        for task in tasks
    ]
    if capacities is None:
        capacities = compute_default_capacities(run_context)
    before = ReplayScheduler(list(tasks), run_context).replay(capacities)
    after = ReplayScheduler(rewired, run_context).replay(capacities)
    return {
        'replayed_baseline_us': before.makespan_us,
        'projected_us': after.makespan_us,
        'saving_us': max(0, before.makespan_us - after.makespan_us),
        'capacities': dict(capacities),
    }


def _collapse_range(values: List[float], fmt, unit: str = "") -> str:
    """`1.4-1.8` for a spread, `1.6` for agreement.

    UX-89: a grouped block must not imply more precision than the group
    has, and must not spend two numbers where the members agree. The unit
    is carried separately so a range reads `6-9%` rather than `6%-9%`.
    """
    present = [v for v in values if v is not None]
    if not present:
        return ""
    low, high = fmt(min(present)), fmt(max(present))
    return f"{low}{unit}" if low == high else f"{low}-{high}{unit}"


def _name_elements(elements: List[str]) -> str:
    """`lib-a.bst..lib-f.bst, app.bst` rather than seven full names.

    Only contracts a run of names sharing a prefix and differing in a
    single trailing character - anything looser would invent a family
    that is not there, and a reader has to be able to expand the label
    back into real element names without guessing.
    """
    if len(elements) < 3:
        return ", ".join(elements)
    ordered = sorted(elements)
    runs: List[List[str]] = []
    for name in ordered:
        if runs and _is_next_in_run(runs[-1][-1], name):
            runs[-1].append(name)
        else:
            runs.append([name])
    parts = []
    for run in runs:
        parts.append(f"{run[0]}..{run[-1]}" if len(run) >= 3 else ", ".join(run))
    return ", ".join(parts)


def _is_next_in_run(previous: str, name: str) -> bool:
    """Same length, same everything but one character, and that
    character is the next letter or digit."""
    if len(previous) != len(name):
        return False
    diffs = [i for i, (a, b) in enumerate(zip(previous, name)) if a != b]
    if len(diffs) != 1:
        return False
    a, b = previous[diffs[0]], name[diffs[0]]
    return a.isalnum() and b.isalnum() and ord(b) == ord(a) + 1


def _grouped_line(finding_id: str, entries: List[dict], text: str) -> Optional[str]:
    """One line standing in for `len(entries)` identical ones.

    Returns None for a finding whose per-element figures do not
    generalize, and the caller then falls back to printing the group's
    first member verbatim - preferring a slightly longer block to a
    summary that quietly drops a number.
    """
    count = len(entries)

    if finding_id == 'already-compute-bound':
        cores = _collapse_range([e.get('cores_busy') for e in entries], lambda v: f"{v:.1f}")
        return (f"already compute-bound at {cores} cores busy - nothing to gain from "
                f"their parallelism; shortening them means less work")

    if finding_id in ('waiting-not-computing', 'pinned-to-one-job',
                      'underachieved-requested-jobs'):
        cores = _collapse_range([e.get('cores_busy') for e in entries], lambda v: f"{v:.2f}")
        return (f"running at only {cores} cores busy - waiting, not computing; "
                f"look at how they are built before what they build")

    if finding_id == 'cpu-concentration':
        binaries = {(e.get('dominant_binary') or {}).get('binary') for e in entries}
        if len(binaries) != 1 or None in binaries:
            return None
        shares = _collapse_range(
            [(e.get('dominant_binary') or {}).get('cpu_share') for e in entries],
            lambda v: f"{v * 100:.0f}", "%",
        )
        return (f"`{binaries.pop()}` is {shares} of each one's measured CPU - "
                f"they are all the same problem, so look there before anywhere else")

    if finding_id == 'serialization-point':
        binaries = {(e.get('serial_binary') or {}).get('binary') for e in entries}
        if len(binaries) != 1 or None in binaries:
            return None
        walls = _collapse_range(
            [(e.get('serial_binary') or {}).get('wall_s') for e in entries],
            lambda v: f"{v:.1f}", "s",
        )
        return (f"`{binaries.pop()}` is a SINGLE process holding {walls} of wall time "
                f"in each - a serialization point no job count can help")

    if finding_id == 'declared-not-used':
        counts = [len(e.get('unused_dependencies') or []) for e in entries]
        total = sum(counts)
        spread = _collapse_range([float(c) for c in counts], lambda v: f"{v:.0f}")
        return (f"opened no file staged by {spread} declared build dependencies each "
                f"({total} edges across the {count}) - worth checking whether those "
                f"edges are needed at build time; this is evidence, not a verdict (a "
                f"runtime-only dependency looks identical here). Per-element lists are "
                f"in --format json")

    # peak-memory and redundant-operation carry per-element figures whose
    # meaning does not survive being averaged (a shared operation's own
    # element list, an absolute RSS to multiply by concurrency), so they
    # are deliberately not generalized.
    return None


def _grouped_blocks(actionable: List[dict]) -> List[tuple]:
    """Partition `actionable` into (elements, entries, signature) groups.

    UX-89: on `examples/06`'s baseline, `lib-a.bst` through `lib-f.bst`
    and `app.bst` each produced the *same four findings* differing only
    in their parameters - forty lines to convey two facts, and at
    freedesktop-sdk scale the same structure would bury the one
    distinctive row under dozens of interchangeable ones.

    Grouped on the finding-id signature alone, not on the numbers: two
    elements with the same findings are the same *story*, and the
    numbers are what the grouped line puts a range on. Order is
    preserved - the list is already ranked by Plane 1 impact, and a
    group takes the position of its strongest member, so grouping never
    reorders what leads.
    """
    groups: List[tuple] = []
    index: Dict[tuple, int] = {}
    for entry in actionable:
        signature = tuple(step['id'] for step in entry['recommendations'])
        if signature in index:
            groups[index[signature]][0].append(entry)
        else:
            index[signature] = len(groups)
            groups.append(([entry], signature))
    return [
        ([e['element'] for e in entries], entries, signature)
        for entries, signature in groups
    ]


def _group_header(elements: List[str], entries: List[dict]) -> str:
    """`lib-a.bst..lib-f.bst, app.bst (7 elements, 6-9% of the critical
    path each, 2.6-3.0s apiece, 19.7s together)`.

    The per-element impact figures live in the finding text for a single
    element; for a group they belong here, once, because the findings
    below are what the group shares and the impact is what distinguishes
    its members. The total is the number a reader actually acts on -
    seven elements worth 3s each are a different decision from one worth
    3s.
    """
    if len(entries) == 1:
        return f"{elements[0]}:"
    shares = _collapse_range(
        [e.get('critical_path_share') for e in entries], lambda v: f"{v * 100:.0f}", "%",
    )
    savings_us = [e.get('potential_saving_us') or 0 for e in entries]
    each = _collapse_range([v / 1e6 for v in savings_us], lambda v: f"{v:.1f}", "s")
    parts = [f"{len(entries)} elements"]
    if shares:
        parts.append(f"{shares} of the critical path each")
    if any(savings_us):
        parts.append(f"{each} apiece, {sum(savings_us) / 1e6:.1f}s together")
    return f"{_name_elements(elements)} ({', '.join(parts)}):"


def _recommend(joined: ElementJoin, memory_envelope_available: bool = False) -> List[str]:
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
        serial_floor_s = max(
            _SERIALIZATION_NOTABLE_S,
            joined.potential_saving_us / 1e6 * _SERIALIZATION_NOTABLE_SHARE,
        )
        if serial and (serial.get('wall_s') or 0) >= serial_floor_s:
            ranked.append((_EVIDENCE_SERIALIZATION, 'serialization-point',
                f"`{serial['binary']}` is a SINGLE process holding "
                f"{serial['wall_s']:.1f}s of wall time - a serialization point no "
                f"job count can help; it has to get faster or go away"))

        if joined.peak_rss_kb and joined.peak_rss_kb / 1024 >= _PEAK_RSS_NOTABLE_MB:
            # UX-104: the trailing instruction used to be "multiply by
            # however many elements build concurrently before raising
            # `builders`". Where the capture recorded the host's RAM the
            # tool does that multiplication itself, once, in the memory
            # envelope above - so this row states the element's own
            # measurement and points there rather than handing over
            # arithmetic it can do.
            ranked.append((_EVIDENCE_MEMORY, 'peak-memory',
                f"its largest single process peaked at "
                f"{joined.peak_rss_kb / 1024:.0f} MB resident"
                + (
                    " - see the memory envelope above for what that means for "
                    "`builders`" if memory_envelope_available else
                    " - multiply by however many elements build concurrently "
                    "before raising `builders` (the capture recorded no host "
                    "memory, so this cannot do it for you)"
                )))

        redundancy = joined.worst_redundancy
        redundancy_s = (redundancy or {}).get("max_element_duration_s") or 0
        floor_s = max(
            _REDUNDANCY_NOTABLE_S,
            joined.potential_saving_us / 1e6 * _REDUNDANCY_NOTABLE_SHARE,
        )
        if redundancy and redundancy_s >= floor_s:
            others = [e for e in redundancy.get("elements", []) if e != joined.element]
            ranked.append((_EVIDENCE_REDUNDANCY, 'redundant-operation',
                f"it pays {redundancy_s:.1f}s for an operation "
                f"{_count(len(others), 'other element')} also run"
                f"{'s' if len(others) == 1 else ''} "
                f"({redundancy['occurrence_count']}x in total): "
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


# UX-83: at or above this share of the host's cores, the run was already
# CPU-busy and another builder buys contention rather than throughput.
# Not tuned: it is the point past which "there is idle CPU to fill" stops
# being true, with a margin for the fact that the measure is an average
# over the whole run rather than over the contended window.
_SATURATION_SHARE = 0.8


def compute_memory_envelope(
    native_report: dict, builders: Optional[int], host_memory_mb: Optional[int],
) -> dict:
    """UX-104: how much memory this build's shape needs at N builders,
    and whether the host has it.

    The report's standing memory line is *"its largest single process
    peaked at 1902 MB resident - multiply by however many elements build
    concurrently before raising `builders`"*. That multiplication is the
    tool's job, and every input is already measured: per-element peak RSS
    (`UX-63`), the host's RAM (`UX-104` records it at capture time), and
    the builders count (Plane 1).

    **Conservative by construction, and it says so.** The envelope at N
    is the sum of the N largest measured per-element peaks, as if those N
    elements built at once *and* peaked at the same instant. Neither is
    guaranteed - `compute_peak_memory`'s own note is emphatic that per-
    process peaks must not be summed, because two processes peaking at
    different moments never held the sum between them. The same caution
    applies one level up and is the reason this is an upper bound: for
    the question being asked - "is it safe to raise `builders`?" - an
    upper bound is the useful direction to be wrong in.

    **No invented safety margin.** A reserve for the OS and page cache
    would be a threshold picked from nothing, which this codebase does
    not do; `fits` is a strict comparison against the host's RAM, and
    the payload says plainly that headroom below 100% is not the same as
    safe.

    Returns `{}` when Plane 2 has no memory data or the host's RAM was
    not recorded - the arithmetic needs both, and half of it is not an
    estimate, it is a guess.
    """
    peak_memory = (native_report or {}).get("peak_memory") or {}
    per_element = peak_memory.get("per_element") or {}
    peaks_mb = sorted(
        ((entry.get("peak_rss_kb") or 0) / 1024 for entry in per_element.values()),
        reverse=True,
    )
    peaks_mb = [peak for peak in peaks_mb if peak > 0]
    if not peaks_mb or not host_memory_mb:
        return {}

    def _envelope(count: int) -> float:
        # Fewer measured elements than builders means the build cannot
        # actually run that many at once out of this population, so the
        # sum is over what exists rather than padded with a guess.
        return sum(peaks_mb[:count])

    observed = builders if isinstance(builders, int) and builders > 0 else None
    projections = []
    # Projected up to the measured population, and no further. That is a
    # real bound rather than a chosen one: N builders can only be N
    # elements building at once, and beyond the elements whose peak was
    # measured there is nothing to sum but a guess. (An earlier version
    # stopped two past the observed count, which is arbitrary and hid a
    # ceiling three builders away.)
    for count in range(1, len(peaks_mb) + 1):
        envelope = _envelope(count)
        projections.append({
            'builders': count,
            'envelope_mb': envelope,
            'share_of_host': envelope / host_memory_mb,
            'fits': envelope <= host_memory_mb,
        })
    at_observed = next(
        (p for p in projections if p['builders'] == observed), None,
    )
    higher = [p for p in projections if observed and p['builders'] > observed]
    first_that_does_not_fit = next((p for p in higher if not p['fits']), None)
    return {
        'host_memory_mb': host_memory_mb,
        'builders': observed,
        'elements_measured': len(peaks_mb),
        'largest_element_peak_mb': peaks_mb[0],
        'at_observed_builders': at_observed,
        'projections': projections,
        'first_builders_that_does_not_fit': (
            first_that_does_not_fit['builders'] if first_that_does_not_fit else None
        ),
        'note': (
            "The envelope at N builders is the sum of the N largest measured "
            "per-element peak RSS values, as if those elements built at once and "
            "peaked at the same instant - an upper bound, which is the useful "
            "direction to be wrong in for a question about raising --builders. No "
            "reserve is subtracted for the OS or page cache, so headroom below "
            "100% is not the same as safe."
        ),
    }


def summarize_plane2_capacity(
    native_report: dict, host_cpu_count: Optional[int] = None,
) -> dict:
    """What Plane 2 knows about whether more builders would help.

    `UX-83`: measured on one dual-plane capture, `bga analyze` said
    *"31.9% of wall-clock is RESOURCE WAIT - try `--capacity N` with a
    higher N"* and `bga sweep` put the knee at capacity 5, while
    `bga correlate` on the **same capture** named the real fix -
    `core.bst` at 0.90 cores busy with `-j1`, worth -32.4% and costing no
    extra capacity. The capacity axis being unmodeled is a known gap
    (`UX-09`); what was new is that when the missing information is
    present in the same capture, the Plane 1 advice did not consult it.

    Returns the two facts that change the advice, and enough provenance
    to say why. Empty when Plane 2 cannot answer, which leaves today's
    hint standing unchanged.
    """
    cpu_time = native_report.get("cpu_time") or {}
    per_element = cpu_time.get("per_element") or {}
    wall_span = native_report.get("wall_span_s")
    measured_cpu_us = sum(
        (entry.get("cpu_us") or 0) for entry in per_element.values()
    )
    cores_busy = (
        (measured_cpu_us / 1e6) / wall_span if wall_span and measured_cpu_us else None
    )
    pinned = sorted(
        entry["element"]
        for entry in native_report.get("per_element_parallelism") or []
        if "pinned_to_one_job" in (entry.get("findings") or [])
        and entry.get("element")
    )
    saturated = (
        cores_busy is not None and host_cpu_count
        and cores_busy >= _SATURATION_SHARE * host_cpu_count
    )
    return {
        "cores_busy": cores_busy,
        "host_cpu_count": host_cpu_count,
        "saturated": bool(saturated),
        "pinned_elements": pinned,
    }


# UX-116: how far the sweep is run when the joint recommendation needs a
# knee. The sweep's own default is "one configuration per task", which on
# a 1200-element project is 1200 replays to answer a question about a
# 4-core host. The recommendation only concerns the neighbourhood of what
# is settable, so the range is bounded by the host and the current
# setting - and when the knee lands at the top of that range, the block
# says the graph wants "at least" that many rather than inventing a
# number it did not reach.
_RECOMMENDATION_SWEEP_HEADROOM = 2
_RECOMMENDATION_SWEEP_CAP = 32


def compute_capacity_recommendation(
    plane2_capacity: dict,
    memory_envelope: dict,
    knee: Optional[int],
    knee_range_top: Optional[int] = None,
    builders: Optional[int] = None,
    native_max_jobs: Optional[int] = None,
) -> dict:
    """UX-09, finally answered: what should `--builders` and `--max-jobs`
    be, and which constraint is the reason (`UX-116`).

    Every input has been measured for rounds and reported in a different
    block: the sweep's scheduling knee (how many builders the *graph*
    can use), Plane 2's aggregate cores-busy (how much CPU the elements
    actually draw at their current `-j`), `UX-104`'s memory envelope per
    builders value, and the host's core count. What was missing is the
    sentence that intersects them - the difference between four blocks a
    reader must reconcile and the one recommendation they came for.

    **How the CPU ceiling is derived.** At the observed `builders`, the
    run drew `cores_busy` cores; that is `cores_busy / builders` per
    concurrently-building element, measured rather than assumed. The
    number of builders the host's cores can feed at that draw is
    `host_cores * builders / cores_busy`, floored. It is an average over
    the whole run, not over the contended window, so it is a guide and
    the payload says so.

    **What it will not do.** It never recommends a value it has no
    measurement for, and it does not try configurations - one capture
    in, one recommendation out. `UX-09`'s real timing table remains the
    ground truth this is checked against, not something this replaces.

    Returns `{}` when Plane 2 cannot answer - the same bar `UX-83` uses,
    because a recommendation resting on a missing `cores_busy` is a
    guess wearing a measurement's clothes.
    """
    cores_busy = (plane2_capacity or {}).get('cores_busy')
    host_cores = (plane2_capacity or {}).get('host_cpu_count')
    if cores_busy is None or not host_cores or not builders or builders <= 0:
        return {}

    constraints = []
    if knee:
        constraints.append({
            'name': 'graph',
            'allows': knee,
            'reason': (
                f"the sweep's knee is at {knee} builder(s)"
                + (", the top of the range swept, so the graph may want more"
                   if knee_range_top and knee >= knee_range_top else "")
            ),
        })
    cpu_allows = int(host_cores * builders / cores_busy) if cores_busy > 0 else None
    if cpu_allows:
        constraints.append({
            'name': 'CPU',
            'allows': cpu_allows,
            'reason': (
                f"{cores_busy:.2f} of {host_cores} core(s) busy at builders="
                f"{builders}, i.e. {cores_busy / builders:.2f} core(s) per "
                f"concurrent element"
            ),
        })
    memory_allows = _memory_allows(memory_envelope)
    if memory_allows:
        constraints.append({
            'name': 'memory',
            'allows': memory_allows['allows'],
            'reason': memory_allows['reason'],
        })

    if not constraints:
        return {}
    binding = min(constraints, key=lambda c: (c['allows'], c['name']))
    pinned = (plane2_capacity or {}).get('pinned_elements') or []
    return {
        'builders': builders,
        'native_max_jobs': native_max_jobs,
        'host_cpu_count': host_cores,
        'cores_busy': cores_busy,
        'constraints': constraints,
        'binding_constraint': binding['name'],
        'recommended_builders': binding['allows'],
        'change': binding['allows'] - builders,
        'pinned_elements': pinned,
        # UX-14, inherited rather than re-invented: the sweep replays the
        # durations it observed and does not model contention, so a knee
        # is what the *schedule* could do with more builders, not what
        # this host would.
        'caveat': (
            "Derived from this run's shape: the sweep replays observed durations "
            "and does not model contention (UX-14), and cores-busy is an average "
            "over the whole run rather than over the contended window. One capture "
            "in, one recommendation out - no configuration was tried."
        ),
    }


def _memory_allows(memory_envelope: dict) -> Optional[dict]:
    """The largest builders value whose envelope fits in the host's RAM.

    `None` rather than a number when the envelope was never computed, so
    a missing measurement cannot masquerade as an unbounded ceiling.
    """
    envelope = memory_envelope or {}
    projections = envelope.get('projections') or []
    if not projections:
        return None
    fitting = [p['builders'] for p in projections if p['fits']]
    if not fitting:
        return {
            'allows': 0,
            'reason': (
                f"no builders value fits: even one element of this shape peaks at "
                f"~{envelope['largest_element_peak_mb'] / 1024:.1f} GB against "
                f"{envelope['host_memory_mb'] / 1024:.1f} GB of RAM"
            ),
        }
    largest = max(fitting)
    measured = envelope.get('elements_measured')
    return {
        'allows': largest,
        'reason': (
            f"the {largest}-builder envelope fits in "
            f"{envelope['host_memory_mb'] / 1024:.1f} GB"
            + (f" (measured over {measured} element peak(s), so it says nothing "
               f"above {measured})" if measured and largest >= measured else "")
        ),
    }


# UX-100: the too-fine signature, stated as a definition rather than as
# a threshold.
#
# The Required Fix asks for a cut "derived from the measured toll
# distribution, not guessed". Deriving one was tried first and the real
# distribution refuses to supply it: on the freedesktop-sdk log tree, 23
# elements have a median toll share of **0.0** and a MAD of **0.0**,
# because BuildStream times these phases to the second and most stagings
# finish inside one. `median + k*MAD` collapses to the median, every
# element clears it, and the "derived" threshold is decorative - `UX-28`
# arriving through the back door.
#
# So the criterion comes from the direction's own sentence instead:
# elements "each paying the UX-99 toll to do less work than the toll
# costs". That is `toll >= work` - a definition, with nothing to tune -
# and it is the same 50% share the direction hypothesised, arrived at
# rather than picked. The measured distribution is still published
# beside it, because "nothing here is close to the line" is the useful
# thing to know when nothing fires: on fdsdk the maximum toll share is
# 16.7%, on a 6-second element.
MERGE_TOLL_AT_LEAST_WORK = 0.5

# ...and an absolute floor, because a 91% toll share on a 0.44s element
# is arithmetic. `UX-99` ranks toll payers by seconds for the same
# reason.
MERGE_TOLL_FLOOR_S = 1.0

# A split candidate must hold at least this share of the critical path.
# `UX-33`'s own materiality bar, one domain over.
SPLIT_PATH_SHARE = 0.10

# ...and show real internal parallelism, or splitting it buys nothing
# that raising its job count would not.
SPLIT_MEAN_CONCURRENCY = 2.0


def find_granularity_findings(
    analysis: dict, native_report: dict, cache_logs: Optional[dict] = None,
    tasks=None, run_context=None, dependencies=None,
) -> List[dict]:
    """UX-100: are the elements the right size?

    Element granularity is BuildStream's oldest tuning question and every
    answer is folklore. Both failure directions are real and opposite,
    and by this round the tool measures every ingredient of both - the
    toll (`UX-99`), durations and critical-path share (Plane 1), internal
    parallelism (Plane 2), invalidation blast (`UX-92`) - while drawing
    no conclusion from any of them. That is the same measure-but-don't-say
    gap `UX-82` closed for graph shape.

    **Too fine** is a group of siblings each paying more toll than this
    project's own toll distribution says is normal. The projected saving
    is replayed, not summed: merging N of them deletes N-1 stagings, and
    whether that shortens the *build* depends on the scheduler, which is
    what a replay knows and arithmetic does not.

    **Too coarse** is hedged harder and never projected, because a
    split's shape is a human decision. It names an element and its
    evidence: a material share of the critical path, real internal
    parallelism Plane 2 measured, and - where the run history can supply
    it - a wide invalidation blast.
    """
    findings = []
    findings.extend(
        _merge_candidates(dependencies, cache_logs, tasks, run_context)
    )
    findings.extend(_split_candidates(analysis, native_report))
    return findings


def _merge_candidates(dependencies, cache_logs, tasks, run_context) -> List[dict]:
    payers = ((cache_logs or {}).get('sandbox_tax') or {}).get('top_payers') or []
    measured = [p for p in payers if p.get('total_us')]
    if not measured:
        return []
    toll_share = {p['element']: p['toll_share'] for p in measured}
    toll_us = {p['element']: p['toll_us'] for p in measured}

    # Siblings: elements with the identical set of build dependencies. A
    # merge only makes sense where the graph would not notice - two
    # elements with different parents cannot become one without changing
    # what depends on what.
    #
    # Taken from the caller's graph object, not from the analysis JSON:
    # that payload carries no `graph` key, so reading one there produced
    # a check that could never fire - the defect class this repository
    # keeps finding in its own gates, caught here by printing the parent
    # map while wiring it up.
    parents: Dict[str, set] = {}
    for dependency in dependencies or []:
        if getattr(dependency, 'dependency_type', None) == 'runtime':
            continue
        parents.setdefault(dependency.successor, set()).add(dependency.predecessor)
    groups: Dict[frozenset, List[str]] = {}
    for element, own_parents in parents.items():
        if element in toll_share:
            groups.setdefault(frozenset(own_parents), []).append(element)

    findings = []
    for parent_set, members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        over = sorted(
            member for member in members
            if toll_share.get(member, 0) >= MERGE_TOLL_AT_LEAST_WORK
            and toll_us.get(member, 0) / 1e6 >= MERGE_TOLL_FLOOR_S
        )
        if len(over) < 2:
            continue
        # Merging N deletes N-1 tolls; the largest is kept, because one
        # staging still happens.
        deleted = sorted((toll_us[member] for member in over), reverse=True)[1:]
        projection = _project_with_reduced_durations(
            tasks, run_context,
            {member: toll_us[member] for member in over[1:]},
        )
        findings.append({
            'id': 'merge-candidate',
            'severity': 'medium',
            'elements': over,
            'parents': sorted(parent_set),
            'deleted_toll_us': sum(deleted),
            'projection': projection,
            'projection_is_a_floor': bool(projection),
            'title': (
                f"{len(over)} sibling element(s) spend at least half their time on "
                f"sandbox tax rather than on building: {', '.join(over[:4])}. "
                f"Merging them would delete {len(deleted)} staging(s), "
                f"{sum(deleted) / 1e6:.1f}s of sandbox tax"
                + (
                    f" and at least a replayed {projection['saving_us'] / 1e6:.1f}s "
                    f"of build - a floor, because the replay shortens the tasks "
                    f"without collapsing them into one (UX-120)"
                    if projection else ""
                )
                + ". It also merges their cache granularity: one source change then "
                "rebuilds the group"
            ),
        })
    if findings:
        return findings

    # Nothing fired. Say how far away the project is from the line, which
    # is the useful form of "no finding" here - and distinguishes it from
    # a check that could not run.
    worst = max(measured, key=lambda p: p['toll_share'])
    return [{
        'id': 'merge-not-indicated',
        'severity': 'info',
        'elements': [],
        'title': (
            f"No element pays more sandbox tax than it spends building. Across "
            f"{len(measured)} measured element(s) the largest tax share is "
            f"{worst['toll_share'] * 100:.0f}% ({worst['element']}, "
            f"{worst['toll_us'] / 1e6:.1f}s of {worst['total_us'] / 1e6:.1f}s), "
            f"against the {MERGE_TOLL_AT_LEAST_WORK * 100:.0f}% that would make a "
            f"merge worth its cache cost (UX-100)"
        ),
    }]


def _project_with_reduced_durations(tasks, run_context, reductions) -> Optional[dict]:
    """Replay the run with each named element's BUILD shortened by its
    toll - the `UX-82` pattern, applied to durations instead of edges.

    Replayed rather than summed for the same reason: deleting five
    stagings frees capacity, and what happens next is decided by the
    scheduler.

    **It is a lower bound, and `UX-120` measured how loose.** The replay
    shortens N tasks; a real merge leaves *one* task. The group's wave
    structure therefore survives the projection - eight one-second tasks
    on four builders still take two waves - while the real merge collapses
    them into a single sandbox. On the purpose-built fixture the
    projection said 1.0s and the real merged rebuild measured
    substantially more (see `UX-0120`'s verification log for the table).

    Modelling the collapse means synthesising a merged task and rewriting
    the group's edges, which is a different change from this one; until
    then the number is published as a floor and says so, because a
    projection that under-predicts is safe to act on and a projection
    that quietly under-predicts is not.
    """
    from .floors.capacity import compute_default_capacities
    from .replay.scheduler import ReplayScheduler

    if not tasks or not reductions:
        return None
    overrides = {}
    for task in tasks:
        element = task.task_key.element_uid
        if element in reductions and task.task_key.task_kind.value == 'BUILD':
            duration = task.finish_us - task.start_us
            overrides[str(task.task_key)] = max(0, duration - reductions[element])
    if not overrides:
        return None
    capacities = compute_default_capacities(run_context)
    before = ReplayScheduler(list(tasks), run_context).replay(capacities)
    after = ReplayScheduler(list(tasks), run_context).replay(
        capacities, duration_overrides=overrides,
    )
    return {
        'replayed_baseline_us': before.makespan_us,
        'projected_us': after.makespan_us,
        'saving_us': max(0, before.makespan_us - after.makespan_us),
    }


def _split_candidates(analysis, native_report) -> List[dict]:
    signals = analysis.get('signals') or {}
    durations = signals.get('element_durations') or {}
    path = signals.get('critical_path') or []
    horizon = (analysis.get('floors') or {}).get('t_infinity_observed') or 0
    if not path or not horizon:
        return []
    concurrency = {
        entry['element']: entry
        for entry in (native_report.get('per_element_parallelism') or [])
        if entry.get('element')
    }
    findings = []
    for element in path:
        share = (durations.get(element) or 0) / horizon
        entry = concurrency.get(element) or {}
        mean = entry.get('mean_work_concurrency') or 0
        if share < SPLIT_PATH_SHARE or mean < SPLIT_MEAN_CONCURRENCY:
            continue
        findings.append({
            'id': 'split-candidate',
            'severity': 'info',
            'elements': [element],
            'critical_path_share': share,
            'mean_work_concurrency': mean,
            'work_processes': entry.get('work_process_count'),
            'invalidation_blast': None,
            'title': (
                f"{element} holds {share * 100:.0f}% of the critical path and runs "
                f"{mean:.2f} concurrent work processes inside one element "
                f"({entry.get('work_process_count')} of them)"
            ),
            # The caveat is identical for every candidate, so it is
            # carried separately and the renderer prints it once. Four
            # candidates used to mean four verbatim copies of the same
            # three sentences - 1300 characters saying one thing.
            'rationale': (
                "That is work BuildStream could have scheduled as separate "
                "cacheable elements. Evidence, not a recommendation: a split's "
                "shape is a human decision, and this run's history carries no "
                "invalidation blast for it (every capture is the same commit), "
                "which is the third piece of evidence and the one that would "
                "make the case"
            ),
        })
    return findings


def find_restructuring_findings(
    analysis: dict, native_report: dict, tasks=None, run_context=None,
) -> List[dict]:
    """The structural conclusion five per-element rows jointly support.

    On `examples/06`'s baseline the tool had every fact of the macro
    problem and never stated it: `analyze` printed a ten-element critical
    path with `lib-a..lib-f` six links of it, and `correlate` reported
    **each of the five chain edges** as "opened no file staged by …" -
    five disconnected, deliberately-hedged rows, ranked last by design
    (`UX-68`). The one conclusion they support together - *these six
    elements form a chain whose every internal edge is unread; fan them
    out* - was never drawn, and it was the biggest win in the project.

    The hedge stands: this recommends *checking* the edges, and says so.
    What it adds is the prize, replayed rather than guessed - and a
    reason to look at the group at all, which five separate rows at the
    bottom of a list did not provide.
    """
    edges = _unread_gating_edges(analysis, native_report)
    if not edges:
        return []
    findings = []
    for group in _connected_edge_groups(edges):
        elements = sorted({uid for edge in group for uid in edge})
        projection = project_without_edges(tasks, run_context, group)
        findings.append({
            'id': 'unread-gating-chain',
            'severity': SEVERITY_HIGH,
            'elements': elements,
            'edges': [list(edge) for edge in group],
            'projection': projection,
        })
    # Biggest projected prize first; an unprojected group sorts last
    # rather than to the top, since "unknown" is not "large".
    return sorted(
        findings,
        key=lambda f: -((f['projection'] or {}).get('saving_us') or 0),
    )


def _scale_of(cache_logs: Optional[dict], native_report: dict) -> dict:
    """`UX-260`'s two distributions, each present only if its plane is.

    Sandbox tax comes from Plane 3's `top_payers`, which despite the
    name is *every* payer sorted rather than a truncated head - a
    distribution over a top-N slice would describe the slice and be
    read as the population.
    """
    from .analyzer import distribution

    shapes = {}
    payers = ((cache_logs or {}).get('sandbox_tax') or {}).get('top_payers') or []
    tolls = [p.get('toll_us') for p in payers if p.get('toll_us') is not None]
    tax = distribution(tolls)
    if tax:
        shapes['sandbox_tax_distribution'] = tax

    counts = [entry.get('work_process_count')
              for entry in (native_report or {}).get('per_element_parallelism') or []
              if entry.get('work_process_count') is not None]
    processes = distribution(counts)
    if processes:
        shapes['process_count_distribution'] = processes
    return shapes


def correlate(analysis: dict, native_report: dict, tasks=None, run_context=None,
              cache_logs: Optional[dict] = None, dependencies=None) -> dict:
    """Join a Plane 1 analysis with a Plane 2 native report.

    Both arguments are already-parsed artifacts - this function performs
    no IO and knows nothing about how either was produced, which is what
    keeps the two planes independently replaceable.
    """
    plane1, ranking_metric = _plane1_view(analysis)
    plane2 = _plane2_view(native_report)
    declared = _declared_elements(analysis)

    # UX-104: the multiplication the per-element memory row used to hand
    # to the reader ("multiply by however many elements build
    # concurrently"). Computed once for the whole join, because it is a
    # fact about the build's shape rather than about any one element -
    # and computed *before* the rows, because whether it exists decides
    # what those rows say.
    memory_envelope = compute_memory_envelope(
        native_report,
        getattr(run_context, 'max_jobs', None),
        getattr(run_context, 'memory_budget_mb', None)
        or getattr(run_context, 'host_memory_mb', None),
    )
    memory_envelope_available = bool(memory_envelope.get('at_observed_builders'))

    joined: List[ElementJoin] = []
    for element in sorted(set(plane1) | set(plane2)):
        p1 = plane1.get(element, {})
        p2 = plane2.get(element, {})
        entry = ElementJoin(
            element=element,
            # No check to make when Plane 1 published no per-element
            # signals at all - degrade, rather than reject every row.
            declared=(not declared) or element in declared,
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
        # UX-66: a name Plane 1 never declared is fiction, whatever it
        # ends in. Recommendations are what a reader acts on, so they are
        # what must not be produced; the row still exists in `elements`,
        # labelled, rather than vanishing.
        entry.recommendations = (
            _recommend(entry, memory_envelope_available) if entry.declared else []
        )
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

    # UX-82: computed after the per-element rows, rendered before them -
    # a structural conclusion outranks the individual measurements it is
    # drawn from, and those measurements are the ones the producer
    # itself hedges hardest.
    restructuring = (
        [] if attribution_unreliable
        else find_restructuring_findings(analysis, native_report, tasks, run_context)
    )
    # UX-100: the same posture as `restructuring` - a conclusion about the
    # graph's *shape* rather than about any one element's numbers, drawn
    # after the per-element rows and rendered before them.
    granularity = (
        [] if attribution_unreliable
        else find_granularity_findings(
            analysis, native_report, cache_logs, tasks, run_context,
            dependencies=dependencies,
        )
    )

    return {
        # UX-95's rule, applied to the join: a report that names no run
        # cannot be filed, compared, or trusted a week later. Plane 1's
        # analysis already carries both halves - the identity hash that
        # says which runs are comparable, and the instance that says
        # which capture this was - and the join was dropping them.
        "run_id": analysis.get("run_id"),
        "run_instance": analysis.get("run_instance"),
        "elements": [vars(e) for e in joined],
        # UX-260: the two cross-plane quantities whose scale a reader
        # cannot know. Absent rather than null when the plane that
        # measures them was not captured, and absent rather than
        # invented when there are too few payers to have a shape -
        # `UX-259`'s rule, and the same `distribution()`, so the
        # arithmetic cannot drift from the store's or the graph's.
        **_scale_of(cache_logs, native_report),
        "restructuring": restructuring,
        "granularity": granularity,
        "memory_envelope": memory_envelope,
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
            # UX-66: names Plane 2 produced that the declared graph does
            # not contain. Reported rather than silently dropped - a
            # non-empty list here means the sandbox-to-element mapping is
            # producing fiction and is worth investigating on its own.
            "undeclared_plane2_elements": sorted(
                e.element for e in joined if not e.declared
            ),
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


def _chain_order(finding: dict) -> List[str]:
    """The group's elements in dependency order where it is a simple
    chain, and sorted otherwise.

    A chain is what this finding is usually about, and `a -> b -> c`
    says "these are in a line" in a way an alphabetical list does not.
    """
    edges = [tuple(edge) for edge in finding['edges']]
    successors = {a: b for a, b in edges}
    heads = {a for a, _ in edges} - {b for _, b in edges}
    if len(heads) != 1 or len(successors) != len(edges):
        return list(finding['elements'])
    chain = [heads.pop()]
    while chain[-1] in successors:
        nxt = successors[chain[-1]]
        if nxt in chain:  # a cycle cannot be a chain; fall back
            return list(finding['elements'])
        chain.append(nxt)
    return chain if len(chain) == len(finding['elements']) else list(finding['elements'])


def _count(n: int, noun: str) -> str:
    """`1 element` / `2 elements`, rather than `1 element(s)`. The
    parenthesised plural is honest when a count is unknown at authoring
    time and simply wrong once it is known to be one."""
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def format_correlation(result: dict) -> str:
    """Human-readable join, leading with what to do next."""
    lines = ["=" * 60, "Two-Plane Correlation (Plane 1 x Plane 2)", "=" * 60]
    if result.get("run_id"):
        lines.append(f"Run: {result['run_id']}")
    instance = result.get("run_instance") or {}
    if instance.get("started_at"):
        lines.append(
            f"Instance: {instance['started_at']}"
            + (f"  {instance['run_dir']}" if instance.get("run_dir") else "")
        )
    if len(lines) > 3:
        lines.append("")
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
    # UX-66: said before the rows, because it says the mapping produced
    # names that are not elements - which is the failure mode `UX-56`
    # measured and this check exists to stop reaching a reader.
    if coverage.get("undeclared_plane2_elements"):
        names = coverage["undeclared_plane2_elements"]
        lines.append(
            f"  {len(names)} Plane 2 name(s) are not declared elements and are "
            f"excluded from the rows below: {', '.join(names[:5])}"
            + (f" (+{len(names) - 5} more)" if len(names) > 5 else "")
        )
    if coverage.get("aggregating_dependency_pairs"):
        lines.append(
            f"  {coverage['aggregating_dependency_pairs']} further dependency "
            f"pair(s) set aside as aggregating - they stage almost nothing of "
            f"their own, so 'nobody opened it' says nothing about them (UX-68); "
            f"see --format json for the list"
        )
    # UX-104: the whole-build memory answer, once, before the per-element
    # rows that used to tell the reader to work it out themselves.
    envelope = result.get("memory_envelope") or {}
    at_observed = envelope.get("at_observed_builders")
    if at_observed:
        host_gb = envelope["host_memory_mb"] / 1024
        line = (
            f"  Memory envelope: {at_observed['builders']} builders of this shape "
            f"peak at ~{at_observed['envelope_mb'] / 1024:.1f} GB of {host_gb:.1f} GB "
            f"({at_observed['share_of_host'] * 100:.0f}%)"
        )
        ceiling = envelope.get("first_builders_that_does_not_fit")
        if ceiling:
            line += f"; {ceiling} would not fit"
        else:
            higher = [
                p for p in envelope["projections"]
                if p["builders"] > at_observed["builders"]
            ]
            if higher:
                line += (
                    f"; {higher[-1]['builders']} would still fit, so memory is not "
                    f"what binds first here"
                )
        lines.append(line)
        lines.append(f"    ({envelope['note']})")
    lines.append("")

    # UX-100: granularity, beside the other whole-graph conclusions.
    # Grouped by the caveat they share: the JSON keeps one entry per
    # element, because that is what a CI consumer keys on, and the text
    # says the shared half once.
    grouped: List[Tuple[Tuple[str, str, str], List[dict]]] = []
    for finding in result.get("granularity") or []:
        key = (finding['severity'], finding['id'], finding.get('rationale') or '')
        if grouped and grouped[-1][0] == key:
            grouped[-1][1].append(finding)
        else:
            grouped.append((key, [finding]))
    for (severity, finding_id, rationale), group in grouped:
        head, *rest = group
        lines.append(f"[{severity}] {finding_id}: {head['title']}")
        for finding in rest:
            lines.append(f"  ...and {finding['title']}")
        if rationale:
            lines.append(f"  {rationale}")
        lines.append("")

    # UX-82: before the per-element rows. A structural conclusion
    # outranks the individual measurements it is drawn from.
    for finding in result.get("restructuring") or []:
        lines.append(
            f"Restructuring opportunity: {len(finding['edges'])} declared build "
            f"edge(s) among {len(finding['elements'])} element(s) were measured "
            f"never-read, and they chain those elements along the critical path:"
        )
        lines.append("    " + " -> ".join(_chain_order(finding)))
        projection = finding.get("projection")
        if projection and projection.get("saving_us"):
            lines.append(
                f"    Replaying this run with those edges removed - same durations, "
                f"same capacity - finishes in "
                f"{projection['projected_us'] / 1e6:.1f}s against "
                f"{projection['replayed_baseline_us'] / 1e6:.1f}s: "
                f"{projection['saving_us'] / 1e6:.1f}s"
            )
        elif projection:
            lines.append(
                "    Replaying this run with those edges removed changes nothing - "
                "the chain is not what binds here"
            )
        lines.append(
            "    Worth checking whether those edges are needed at build time: each "
            "one is evidence, not a verdict (a runtime-only dependency looks "
            "identical here), and the projection is a replay of this run's "
            "durations, not a re-capture."
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
        # UX-89: elements whose finding *sets* are identical share one
        # block. A single-element group renders exactly as it always did,
        # so nothing changes for the case that was never repetitive.
        groups = _grouped_blocks(actionable)
        shown, elements_shown = 0, 0
        for elements, entries, signature in groups:
            if shown >= _SHOWN_MAX:
                break
            shown += 1
            elements_shown += len(entries)
            lines.append(f"  {_group_header(elements, entries)}")
            for index, step in enumerate(entries[0]["recommendations"]):
                if len(entries) == 1:
                    lines.append(f"    - {step['text']}")
                    continue
                grouped = _grouped_line(signature[index], entries, step['text'])
                # A finding whose figures do not generalize keeps the
                # first member's own words rather than being summarized
                # into something the measurement does not say.
                lines.append(f"    - {grouped or step['text']}")
            coverages = [
                e["cpu_coverage"] for e in entries if e["cpu_coverage"] is not None
            ]
            if coverages and min(coverages) < 1.0:
                span = _collapse_range(coverages, lambda v: f"{v * 100:.0f}", "%")
                scope = "this element's" if len(entries) == 1 else "each element's"
                lines.append(f"    ({span} of {scope} processes were measured)")
        if elements_shown < len(actionable):
            lines.append(
                f"  (+{len(actionable) - elements_shown} more element(s) with findings, "
                f"see --format json)"
            )
    lines.append("")
    lines.append(f"({result['note']})")
    lines.append("=" * 60)
    return "\n".join(lines)
