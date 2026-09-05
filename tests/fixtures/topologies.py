"""
Shared synthetic graph topology fixture library (P3-01, spec Part 36.1).

Each factory below builds one of the topologies Part 36.1 requires
tests to cover (linear chain, diamond, fan-in, fan-out, multiple equal
predecessors, deep unequal predecessors, independent branches, terminal
tasks, requested/non-requested targets) and returns a
`(run_context, graph, trace)` tuple of plain JSON-serializable dicts in
the canonical graph/v9 + trace/v9 shape (Part 32.2/32.3) - the same
shape already used across the P1/P2 regression tests (e.g.
`tests/unit/test_cold_floor.py`), so any test that already knows how to
write a run dir from that shape can consume these directly.

`write_run_dir` does that writing; `build_analyzer` is a convenience
that writes + constructs a loaded `BuildEfficiencyAnalyzer` in one call.
No test *assertions* live here - only fixture construction (Part 36.1's
assertions are the consuming tasks' job: P3-03 through P3-09 and various
P1-*/P2-* acceptance tests).
"""
import json
from pathlib import Path
from typing import Optional

from bga import BuildEfficiencyAnalyzer

RunContext = dict
Graph = dict
Trace = dict
Topology = tuple[RunContext, Graph, Trace]


def _element(uid: str, cache_key: Optional[str] = None, requested_target: bool = False) -> dict:
    return {"uid": uid, "cache_key": cache_key, "requested_target": requested_target}


def _dependency(predecessor: str, successor: str, dependency_type: str = "build") -> dict:
    return {"predecessor": predecessor, "successor": successor, "dependency_type": dependency_type}


def _span(
    uid: str, start_us: int, dur_us: int,
    kind: str = "BUILD", phase: str = "BUILD", attempt: int = 0,
    resources: tuple[str, ...] = ("PROCESS",),
) -> dict:
    return {
        "task_key": f"{uid}|{kind}|{phase}|{attempt}",
        "ts_us": start_us,
        "dur_us": dur_us,
        "resources": list(resources),
        "primary_resource": resources[0] if resources else None,
    }


def _run_context(
    wall_end_us: int, max_jobs: int = 8,
    resource_capacities: Optional[dict[str, int]] = None,
    trace_epsilon_us: int = 1000,
) -> RunContext:
    return {
        "trace_epsilon_us": trace_epsilon_us,
        "wall_clock": {"start_us": 0, "end_us": wall_end_us},
        "max_jobs": max_jobs,
        "resource_capacities": resource_capacities or {"PROCESS": max_jobs},
        # Declares as many effective CPUs as max_jobs, matching each
        # topology's own concurrency - avoids a spurious CPU
        # reconciliation warning (Part 33.3) from the default
        # effective_cpus=1.0 fallback whenever a fixture runs >1 task
        # concurrently, which every topology but linear_chain does.
        "cpu_accounting": {"effective_cpus": max_jobs},
    }


def _build(
    elements: list[dict], dependencies: list[dict], spans: list[dict],
    wall_end_us: int, max_jobs: int = 8,
    resource_capacities: Optional[dict[str, int]] = None,
) -> Topology:
    graph = {"elements": elements, "dependencies": dependencies}
    trace = {"spans": spans, "phases": []}
    run_context = _run_context(wall_end_us, max_jobs=max_jobs, resource_capacities=resource_capacities)
    return run_context, graph, trace


def _duration_for(uid: str, default_us: int, durations: Optional[dict[str, int]]) -> int:
    return (durations or {}).get(uid, default_us)


# --- Topology factories (Part 36.1) ---

def linear_chain(
    n: int = 3, duration_us: int = 10000,
    durations: Optional[dict[str, int]] = None,
    requested_target_last: bool = True,
) -> Topology:
    """elem0 -> elem1 -> ... -> elem(n-1), each depending only on its
    immediate predecessor, run strictly sequentially."""
    uids = [f"elem{i}.bst" for i in range(n)]
    elements = [
        _element(uid, requested_target=requested_target_last and i == n - 1)
        for i, uid in enumerate(uids)
    ]
    dependencies = [_dependency(uids[i - 1], uids[i]) for i in range(1, n)]

    spans = []
    t = 0
    for uid in uids:
        d = _duration_for(uid, duration_us, durations)
        spans.append(_span(uid, t, d))
        t += d

    return _build(elements, dependencies, spans, wall_end_us=t, max_jobs=1)


def diamond(duration_us: int = 10000, durations: Optional[dict[str, int]] = None) -> Topology:
    """a -> {b, c} -> d: b and c run concurrently between a and d."""
    a, b, c, d = "a.bst", "b.bst", "c.bst", "d.bst"
    elements = [_element(a), _element(b), _element(c), _element(d, requested_target=True)]
    dependencies = [_dependency(a, b), _dependency(a, c), _dependency(b, d), _dependency(c, d)]

    da = _duration_for(a, duration_us, durations)
    db = _duration_for(b, duration_us, durations)
    dc = _duration_for(c, duration_us, durations)
    dd = _duration_for(d, duration_us, durations)
    mid = da + max(db, dc)
    spans = [
        _span(a, 0, da),
        _span(b, da, db),
        _span(c, da, dc),
        _span(d, mid, dd),
    ]
    return _build(elements, dependencies, spans, wall_end_us=mid + dd, max_jobs=2)


def fan_in(
    n: int = 4, duration_us: int = 10000, durations: Optional[dict[str, int]] = None,
) -> Topology:
    """n independent predecessors converging on one successor."""
    pred_uids = [f"pred{i}.bst" for i in range(n)]
    sink = "sink.bst"
    elements = [_element(uid) for uid in pred_uids] + [_element(sink, requested_target=True)]
    dependencies = [_dependency(uid, sink) for uid in pred_uids]

    pred_durations = [_duration_for(uid, duration_us, durations) for uid in pred_uids]
    ready_us = max(pred_durations)
    spans = [_span(uid, 0, d) for uid, d in zip(pred_uids, pred_durations)]
    sink_dur = _duration_for(sink, duration_us, durations)
    spans.append(_span(sink, ready_us, sink_dur))

    return _build(elements, dependencies, spans, wall_end_us=ready_us + sink_dur, max_jobs=n)


def fan_out(
    n: int = 4, duration_us: int = 10000, durations: Optional[dict[str, int]] = None,
) -> Topology:
    """one predecessor, n independent successors (all requested targets)."""
    source = "source.bst"
    succ_uids = [f"succ{i}.bst" for i in range(n)]
    elements = [_element(source)] + [_element(uid, requested_target=True) for uid in succ_uids]
    dependencies = [_dependency(source, uid) for uid in succ_uids]

    source_dur = _duration_for(source, duration_us, durations)
    spans = [_span(source, 0, source_dur)]
    finish = source_dur
    for uid in succ_uids:
        d = _duration_for(uid, duration_us, durations)
        spans.append(_span(uid, source_dur, d))
        finish = max(finish, source_dur + d)

    return _build(elements, dependencies, spans, wall_end_us=finish, max_jobs=n)


def multiple_equal_predecessors(duration_us: int = 10000) -> Topology:
    """target depends on two predecessors that finish at exactly the
    same normalized time but sit at different depths (shallow.bst is a
    direct root; deep_pre.bst -> deep.bst is a 2-level chain) - feeds
    tie-break tests (Part 36.4: same finish, different depth -> greater
    depth wins)."""
    shallow, deep_pre, deep, target = "shallow.bst", "deep_pre.bst", "deep.bst", "target.bst"
    elements = [
        _element(shallow), _element(deep_pre), _element(deep),
        _element(target, requested_target=True),
    ]
    dependencies = [
        _dependency(deep_pre, deep),
        _dependency(shallow, target),
        _dependency(deep, target),
    ]
    tie_us = 2 * duration_us
    spans = [
        _span(shallow, 0, tie_us),
        _span(deep_pre, 0, duration_us),
        _span(deep, duration_us, duration_us),
        _span(target, tie_us, duration_us),
    ]
    return _build(elements, dependencies, spans, wall_end_us=tie_us + duration_us, max_jobs=2)


def deep_unequal_predecessors(
    duration_us: int = 10000, chain_length: int = 3,
    shallow_us: Optional[int] = None,
) -> Topology:
    """target depends on a shallow predecessor that finishes early and a
    `chain_length`-deep chain that finishes later - target's ready time
    is governed by the deep chain, not the shallow one.

    `shallow_us` inverts that, and `UX-478` is why it exists. Make the
    shallow predecessor heavy enough and the **critical path** runs
    through it - two elements - while the **graph** still has
    `chain_length + 1` dependency stages. Every other committed shape
    has those two numbers equal, which is what let a mutation reading
    the measured path instead of the graph pass unnoticed; here they
    differ by construction.
    """
    shallow = "shallow.bst"
    chain_uids = [f"deep{i}.bst" for i in range(chain_length)]
    target = "target.bst"

    elements = [_element(shallow)] + [_element(uid) for uid in chain_uids] + [
        _element(target, requested_target=True)
    ]
    dependencies = [_dependency(chain_uids[i - 1], chain_uids[i]) for i in range(1, chain_length)]
    dependencies.append(_dependency(shallow, target))
    dependencies.append(_dependency(chain_uids[-1], target))

    shallow_dur = duration_us if shallow_us is None else shallow_us
    spans = [_span(shallow, 0, shallow_dur)]
    t = 0
    for uid in chain_uids:
        spans.append(_span(uid, t, duration_us))
        t += duration_us
    target_dur = duration_us
    start = max(t, shallow_dur)
    spans.append(_span(target, start, target_dur))

    return _build(elements, dependencies, spans,
                  wall_end_us=start + target_dur, max_jobs=2)


def independent_branches(
    n: int = 2, chain_length: int = 3, duration_us: int = 10000,
) -> Topology:
    """n fully disconnected linear chains sharing no dependencies -
    each branch's last element is a requested target."""
    elements: list[dict] = []
    dependencies: list[dict] = []
    spans: list[dict] = []
    finish = 0

    for branch in range(n):
        uids = [f"branch{branch}_elem{i}.bst" for i in range(chain_length)]
        for i, uid in enumerate(uids):
            elements.append(_element(uid, requested_target=(i == chain_length - 1)))
            if i > 0:
                dependencies.append(_dependency(uids[i - 1], uid))
        t = 0
        for uid in uids:
            spans.append(_span(uid, t, duration_us))
            t += duration_us
        finish = max(finish, t)

    return _build(elements, dependencies, spans, wall_end_us=finish, max_jobs=n)


def graph_with_terminal_and_nonterminal_tasks(duration_us: int = 10000) -> Topology:
    """A mix of requested and non-requested elements: `dep.bst` is
    required (an ancestor of the requested `target.bst`), while
    `orphan.bst` -> `orphan_child.bst` form a branch entirely
    unreachable from any requested target - feeds leaf/deferrability
    analysis (dependencies not on any path to a requested target)."""
    dep, target = "dep.bst", "target.bst"
    orphan, orphan_child = "orphan.bst", "orphan_child.bst"

    elements = [
        _element(dep), _element(target, requested_target=True),
        _element(orphan), _element(orphan_child),
    ]
    dependencies = [
        _dependency(dep, target),
        _dependency(orphan, orphan_child),
    ]
    spans = [
        _span(dep, 0, duration_us),
        _span(target, duration_us, duration_us),
        _span(orphan, 0, duration_us),
        _span(orphan_child, duration_us, duration_us),
    ]
    return _build(elements, dependencies, spans, wall_end_us=2 * duration_us, max_jobs=2)


# --- UX-464's covering set: the four specs UX-463 assigned to curated
# --- fixtures, one factory each. Each exists to make a finding no
# --- committed capture could produce reachable from a clone; the
# --- finding it is for is named in its docstring, and the census
# --- (`tools/dev_finding_coverage.py`) is what says whether it worked.

def shared_base_wide(
    dependents: int = 6, base_us: int = 200_000, heavy_us: int = 6_000_000,
    tie_ratio: float = 0.97, lanes: int = 2, base_kind: str = "import",
) -> Topology:
    """T1: one structural base, N dependents of unequal weight.

    Reaches `blast-radius-ranking`, `blast-radius-structural` and
    `criticality`.

    Three properties carry it, and each is load-bearing:

    - `toolchain.bst` is an `import`, which is in
      `STRUCTURAL_ELEMENT_KINDS`, so it is *reported* as the graph's
      shape rather than ranked as an action (`UX-258`/`UX-76`). That
      split is what produces two blast findings instead of one.
    - `lanes` is below `dependents`, so wall-clock is several times the
      critical path and the run is **not** chain-bound. That is what
      makes `blast-radius-ranking` - the ordered list - reachable:
      `_ranking_findings` ranks only on a scheduler-bound run
      (`UX-65`), because on a chain the concentration table already
      orders the same names (`UX-76`).

      Until `UX-479` the whole function returned nothing on a
      chain-bound run, ranking and reach alike. Raising `lanes` to
      `dependents` now gives the second shape this factory can make: a
      chain-bound wide base, which publishes `blast-radius-reach` and
      no ranking. `test_a_chain_bound_build_still_has_a_blast_radius`
      builds it that way.
    - `base_kind` decides which of the two blast findings the base
      lands in, and nothing else. `import` is in
      `STRUCTURAL_ELEMENT_KINDS`, so the base is reported as shape;
      any other kind makes it an element someone owns and edits, which
      is the `UX-468` planted project's shape (`base.bst`, a
      `compose`) rather than this one's.
    - `tie_ratio` puts the two heaviest dependents within 3% of each
      other, inside the Monte-Carlo sampler's +/-10% perturbation
      (`DEFAULT_PERTURBATION_PCT`), so criticality comes out fractional
      here. A deterministic replay scores every element 1.0 and
      `_criticality_findings` drops a list that ranks nothing.

      Narrowly: **the near-tie is not what makes `criticality`
      reachable from a clone.** Measured by mutation - replacing
      `tie_ratio` with an ordinary tail weight leaves the census at 18
      produced, because `ample_capacity` and `one_source_many_elements`
      each produce it too, on independent same-ish tasks. What the
      near-tie buys is a *named, minimal* case where the contest is the
      point rather than a side effect, which is what makes it
      debuggable when the ranking changes.
    """
    base = "toolchain.bst"
    elements = [dict(_element(base), element_kind=base_kind)]
    dependencies: list[dict] = []
    spans = [_span(base, 0, base_us)]
    # Heaviest, its near-tie, then a decreasing tail - so the ranking
    # has more than two entries to be in order over.
    weights = [1.0, tie_ratio] + [0.5 - 0.05 * i for i in range(dependents - 2)]
    uids = [f"mod{i}.bst" for i in range(dependents)]
    lane_free = [base_us] * lanes
    for i, uid in enumerate(uids):
        elements.append(dict(_element(uid, requested_target=True),
                             element_kind="manual"))
        dependencies.append(_dependency(base, uid))
        lane = lane_free.index(min(lane_free))
        duration = int(heavy_us * weights[i])
        spans.append(_span(uid, lane_free[lane], duration))
        lane_free[lane] += duration
    return _build(elements, dependencies, spans,
                  wall_end_us=max(lane_free), max_jobs=lanes)


def one_source_many_elements(
    elements: int = 4, duration_us: int = 4_000_000,
    url: str = "https://example.invalid/mono.git",
) -> tuple[Topology, dict]:
    """T2: one repository sourced by N elements.

    Reaches `shared-source-blast`, and returns
    `(topology, inventory)` rather than a bare `Topology` because that
    finding is computed from `sources.json` - a fourth file, written by
    `bga extract`, that no other factory has. Pass the inventory to
    `write_run_dir(..., sources=...)`.
    """
    uids = [f"pkg{i}.bst" for i in range(elements)]
    els = [dict(_element(uid, requested_target=True), element_kind="manual")
           for uid in uids]
    spans: list[dict] = []
    t = 0
    for uid in uids:
        spans.append(_span(uid, t, duration_us))
        t += duration_us
    topology = _build(els, [], spans, wall_end_us=t, max_jobs=1)
    inventory = {
        "schema": "sources/v1",
        "elements": {uid: [{"kind": "git", "identity": url, "keying": "url"}]
                     for uid in uids},
        "unreadable": {},
    }
    return topology, inventory


def ample_capacity(
    elements: int = 8, capacity: int = 16, duration_us: int = 3_000_000,
    stagger_us: int = 100_000,
) -> Topology:
    """T3: capacity above demand, so nothing ever queues.

    Reaches `execution-bound` - though not uniquely; three of the five
    covering-set captures produce it, because any run whose elements do
    not wait on each other is execution-bound whether or not it was
    built to be. `UX-463`'s table also assigned `certified-headroom`
    here and that was backwards: headroom is what a run that *did*
    queue leaves on the table, so it comes from `shared_base_wide`.

    Every element is independent and starts
    at once, so no wait category exists at all - which is the gate:
    `_opportunity_findings` publishes `execution-bound` only when the
    largest non-execution category is under `OPPORTUNITY_FLOOR_PCT`
    (1%) of wall-clock.

    The stagger gives the durations a spread, so the concentration
    findings this one is published beside have something to rank.
    """
    uids = [f"task{i}.bst" for i in range(elements)]
    els = [dict(_element(uid, requested_target=True), element_kind="manual")
           for uid in uids]
    spans = [_span(uid, 0, duration_us + i * stagger_us)
             for i, uid in enumerate(uids)]
    return _build(els, [], spans,
                  wall_end_us=duration_us + (elements - 1) * stagger_us,
                  max_jobs=capacity,
                  resource_capacities={"PROCESS": capacity})


def the_same_build_twice(
    chain: int = 4, duration_us: int = 2_000_000,
) -> tuple[Topology, Topology]:
    """T4: `(cold, incremental)` over one graph.

    The incremental half reaches `run-mode-incremental`. What decides
    it is `queue_summary.build.skipped` - `RunContext.run_mode` reads
    that and nothing else, returning `'incremental'` when it is above
    zero, `'full'` when it is zero and `'unknown'` when the capture has
    no Pipeline Summary at all. So the two runs share elements,
    dependencies and per-element durations, and differ only in which
    elements produced a span and in that one count.
    """
    uids = [f"lib{i}.bst" for i in range(chain)]
    els = [dict(_element(uid, cache_key=f"cachekey{i}",
                         requested_target=(i == chain - 1)),
                element_kind="manual")
           for i, uid in enumerate(uids)]
    dependencies = [_dependency(uids[i - 1], uids[i]) for i in range(1, chain)]

    def one_run(built: list[str], skipped: int) -> Topology:
        spans: list[dict] = []
        t = 0
        for uid in built:
            spans.append(_span(uid, t, duration_us))
            t += duration_us
        run_context, graph, trace = _build(
            els, dependencies, spans, wall_end_us=t, max_jobs=1)
        run_context["queue_summary"] = {
            "build": {"processed": len(built), "skipped": skipped, "failed": 0},
        }
        return run_context, graph, trace

    return one_run(uids, 0), one_run(uids[-1:], chain - 1)


def a_build_that_pulls(
    chain: int = 4, pulled: int = 3,
    pull_us: int = 1_000_000, build_us: int = 9_000_000,
) -> Topology:
    """T6: a build most of whose elements came off a remote cache.

    `cache-transfer-cost` is the one finding in `FINDING_READERS` that
    nothing in a clone reached (`UX-459`), and it needs two things at
    once that no other fixture has together. `compute_cache_accounting`
    returns `{}` unless the capture records a Pipeline Summary, and
    `_transfer_us` only counts tasks whose `primary_resource` is
    `DOWNLOAD` or `UPLOAD`. The golden fixture has the second and not
    the first - one `FETCH|DOWNLOAD` span and no `queue_summary` - so
    it publishes no cache block at all.

    So the pulled elements carry a real `PULL` task on `DOWNLOAD`
    (`TaskKind.PULL`, `Resource.DOWNLOAD`, both first-class in
    `bga/ingest/models.py`), the built one a `BUILD` on `PROCESS`, and
    the queue summary says which is which. Serial on purpose:
    `_transfer_us` sums over task duration rather than over a resource
    timeline - its docstring says two concurrent pulls count twice -
    and a fixture whose transfer share exceeds 1.0 would be arguing
    with the thing it is meant to exercise.

    The defaults put the transfer share at 3.0s of 12.0s = **0.250**,
    against `TRANSFER_SHARE_NOTABLE = 0.1` - clear of the threshold
    without being a build that does nothing but download. Measured at
    three shapes while choosing them:

    ```text
      pull    build   share   cache-transfer-cost
      3.0s     4.0s   0.692   fires
      1.0s     9.0s   0.250   fires        <- the defaults
      0.5s    20.0s   0.070   silent
    ```

    Analysing it prints `Model score reduced: T_C (9000000) < LB
    (12000000)`, and that line is `UX-60`'s decided model meeting its
    first committed capture with material non-BUILD time: `T∞` counts
    the `head` (FETCH) plus the longest of everything else, a `PULL` is
    neither, and the replay is free to start `lib3`'s build at t=0
    although the artifacts it consumes arrive at 3.0s. `UX-60` fixed
    exactly this for an element's *own* FETCH; the dependency's PULL is
    the same hole one edge over, and is `UX-481`.
    """
    uids = [f"lib{i}.bst" for i in range(chain)]
    els = [dict(_element(uid, cache_key=f"cachekey{i}",
                         requested_target=(i == chain - 1)),
                element_kind="manual")
           for i, uid in enumerate(uids)]
    dependencies = [_dependency(uids[i - 1], uids[i]) for i in range(1, chain)]

    spans, t = [], 0
    for uid in uids[:pulled]:
        spans.append(_span(uid, t, pull_us, kind="PULL", phase="PULL",
                           resources=("DOWNLOAD",)))
        t += pull_us
    for uid in uids[pulled:]:
        spans.append(_span(uid, t, build_us))
        t += build_us

    run_context, graph, trace = _build(
        els, dependencies, spans, wall_end_us=t, max_jobs=1)
    run_context["queue_summary"] = {
        "build": {"processed": chain - pulled, "skipped": pulled, "failed": 0},
        "pull": {"processed": pulled, "skipped": 0, "failed": 0},
    }
    return run_context, graph, trace


# --- Helpers for tests that consume the above ---

def a_chain_beside_a_crowd(
    chain: int = 4, crowd: int = 6, chain_us: int = 2_000_000,
    crowd_us: int = 3_000_000, lanes: int = 2,
) -> Topology:
    """T7: the one shape a blast-radius *ranking* is worth reading on.

    `UX-474` stopped `blast-radius-ranking` from ordering elements whose
    reach is zero, and doing so made it unreachable from every other
    committed capture. That is the census guard working: the covering
    set had no shape where an ordering by reach carries information.
    Three conditions have to hold at once, and no other fixture holds
    all three.

    - **The reach has to vary among elements someone owns.** `lib0.bst`
      is depended on by everything (9), `lib1.bst` by two, `lib2.bst` by
      one, and the crowd by nothing - so the ranking orders three
      different numbers. `shared_base_wide`'s six dependents are all
      zero and its only reaching element is the `import` that `UX-258`
      excludes from ranking on purpose.
    - **The run has to be scheduler-bound**, because `UX-65` gates the
      ranking there: on a chain the concentration table already orders
      the same names (`UX-76`). A chain alone cannot be - it *is* its
      own critical path - so the crowd runs beside it through `lanes`
      lanes and wall-clock comes out well above the path.
    - **A wait category has to dominate**, which is what makes this the
      only committed capture where `headline.top_actions` comes from
      the blast ranking at all. `_opportunity_findings` emits
      `time-concentration` only when no category clears
      `OPPORTUNITY_FLOOR_PCT`, and `_top_actions` prefers concentration
      wherever it exists. The crowd waiting behind `lib0.bst` for two
      lanes is that category.

    It is also the only committed capture that produces a
    `blast_radius_distribution`, so it is the one that exercises
    `_blast_scale`'s percentile tag and `_density_sentence`. On
    `shared_base_wide` those were absent, switched off by the same flat
    counts that made the ranking wrong - the finding's hedge failing
    exactly where it was needed, which is half of what `UX-474`
    recorded.
    """
    elements: list[dict] = []
    dependencies: list[dict] = []
    spans: list[dict] = []

    uids = [f"lib{i}.bst" for i in range(chain)]
    for i, uid in enumerate(uids):
        elements.append(dict(_element(uid, requested_target=(i == chain - 1)),
                             element_kind="cmake"))
        if i:
            dependencies.append(_dependency(uids[i - 1], uid))
    at = 0
    for uid in uids:
        spans.append(_span(uid, at, chain_us))
        at += chain_us

    # Lane 0 is the chain; every other lane is free the moment the head
    # finishes, which is when the crowd becomes ready.
    lane_free = [at] + [chain_us] * (lanes - 1)
    for i in range(crowd):
        uid = f"app{i}.bst"
        elements.append(dict(_element(uid, requested_target=True),
                             element_kind="manual"))
        dependencies.append(_dependency(uids[0], uid))
        lane = lane_free.index(min(lane_free))
        spans.append(_span(uid, lane_free[lane], crowd_us))
        lane_free[lane] += crowd_us
    return _build(elements, dependencies, spans,
                  wall_end_us=max(lane_free), max_jobs=lanes)


def write_run_dir(tmp_path: Path, topology: Topology, name: str = "run",
                  sources: Optional[dict] = None, indent: Optional[int] = None) -> Path:
    """Write a `(run_context, graph, trace)` topology to disk in the
    run-context.json/graph.json/trace.json layout `bga.ingest.loader`
    expects, and return the run directory path.

    `sources` writes a fourth file, `sources.json` - the `sources/v1`
    inventory `bga extract` produces when the project directory is in
    hand. Only `one_source_many_elements` needs it, and it is optional
    rather than a fourth tuple slot because every other factory would
    then carry a `None` for a file it does not have (`UX-464`).
    """
    run_context, graph, trace = topology
    run_dir = tmp_path / name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run-context.json").write_text(json.dumps(run_context, indent=indent))
    (run_dir / "graph.json").write_text(json.dumps(graph, indent=indent))
    (run_dir / "trace.json").write_text(json.dumps(trace, indent=indent))
    if sources is not None:
        (run_dir / "sources.json").write_text(json.dumps(sources, indent=indent))
    return run_dir


def blast_radius_disagrees_with_horizon(
    hub_us: int = 1_000_000, heavy_us: int = 100_000_000,
    leaf_us: int = 5_000_000, leaves: int = 3,
) -> Topology:
    """`UX-440`: the shape where the document's two ranked lists invert.

    `hub` is built first and everything depends on it; `heavy` is one of
    those dependents and is a hundred times longer than the hub. So
    `hub` has the whole graph downstream of it and `heavy` has nothing,
    while `heavy` is the entire critical path and `hub` is a rounding
    error on it.

    `elements.top_blast_radius` therefore ranks `hub` first and
    `optimization_horizon` ranks `heavy` first, on one honest capture.
    Nothing here is degenerate: it is a build with a cheap common
    ancestor and one expensive leaf, which is the ordinary shape of a
    project with a toolchain at the bottom.

    What carries the inversion is the duration contrast, not the fan:
    found by mutation, `leaves=0` still inverts, while swapping
    `hub_us` and `heavy_us` does not. The leaves stay because they give
    the blast ranking more than two entries to be in order, which the
    ordered-by-its-own-key clause reads.
    """
    hub, heavy = "hub.bst", "heavy.bst"
    leaf_uids = [f"leaf{i}.bst" for i in range(leaves)]
    elements = ([_element(hub)]
                + [_element(uid, requested_target=True)
                   for uid in [heavy] + leaf_uids])
    dependencies = [_dependency(hub, uid) for uid in [heavy] + leaf_uids]
    spans = [_span(hub, 0, hub_us)]
    spans += [_span(heavy, hub_us, heavy_us)]
    spans += [_span(uid, hub_us, leaf_us) for uid in leaf_uids]
    return _build(elements, dependencies, spans,
                  wall_end_us=hub_us + heavy_us, max_jobs=8)


def build_analyzer(tmp_path: Path, topology: Topology, name: str = "run", **kwargs) -> BuildEfficiencyAnalyzer:
    """Write a topology to disk and return a loaded (but not yet
    analyzed) `BuildEfficiencyAnalyzer` - `**kwargs` are forwarded to
    the analyzer constructor (e.g. `cold=True`, `historical_runs=...`)."""
    run_dir = write_run_dir(tmp_path, topology, name=name)
    analyzer = BuildEfficiencyAnalyzer(run_dir, **kwargs)
    analyzer.load()
    return analyzer


# --- Writing the covering set as committed captures ---
#
# `UX-459`'s gap is about a *clone*: `tools/dev_finding_coverage.py`
# reads run directories git tracks, so a factory alone closes nothing.
# These five directories under `tests/fixtures/` are what the census
# can see, and this is the command that regenerates them - byte-stable,
# so a re-run with no code change produces no diff.
#
#     python3 -m tests.fixtures.topologies --write
#
COVERING_SET = {
    # name                        -> (topology, sources or None)
    "shared_base_wide": (shared_base_wide, None),
    "ample_capacity": (ample_capacity, None),
    "a_build_that_pulls": (a_build_that_pulls, None),
    "a_chain_beside_a_crowd": (a_chain_beside_a_crowd, None),
}


def covering_set() -> dict[str, tuple[Topology, Optional[dict]]]:
    """`{directory name: (topology, sources)}` for every committed
    capture `UX-464` added, including the two that are not a bare
    factory call - `one_source_many_elements` returns an inventory
    beside its topology, and `the_same_build_twice` returns a pair."""
    built: dict[str, tuple[Topology, Optional[dict]]] = {
        name: (factory(), sources)
        for name, (factory, sources) in COVERING_SET.items()
    }
    topology, inventory = one_source_many_elements()
    built["one_source_many_elements"] = (topology, inventory)
    cold, incremental = the_same_build_twice()
    built["same_build_twice_cold"] = (cold, None)
    built["same_build_twice_incremental"] = (incremental, None)
    return built


def write_covering_set(root: Path) -> list[Path]:
    """Write every covering-set capture under `root`, one directory
    each, and return the run directories in name order."""
    written = []
    for name, (topology, sources) in sorted(covering_set().items()):
        directory = root / name
        directory.mkdir(parents=True, exist_ok=True)
        written.append(write_run_dir(directory, topology, name="run",
                                     sources=sources, indent=2))
    return written


if __name__ == "__main__":                               # pragma: no cover
    import sys

    if "--write" not in sys.argv[1:]:
        raise SystemExit(f"usage: python3 -m {__name__} --write")
    for run in write_covering_set(Path(__file__).resolve().parent):
        print(run)
