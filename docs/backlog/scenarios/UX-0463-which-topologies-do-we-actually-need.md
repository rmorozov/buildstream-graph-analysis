# UX-463: which topologies we actually need, and why that set

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** none — this is the decision `UX-459` was blocked on, and `UX-464`/`UX-465` both consume it | **Found by:** round 72, asked to inventory the generation tooling before building more of it | **Serves:** the round that wants a fixture for a case nobody has enumerated, and adds a tenth example instead | **Topic:** guards

## Motivation

`UX-459` left a choice with no measurement between its arms: curated
fixtures, or a CI job that runs the census on builds it already
performs. The answer is both, and the reason is that **they cover
different axes** — which only becomes visible once you inventory what
already generates fixtures here.

### What the repository already has

| what | lines | emits | needs `bst` | topology control |
|---|---|---|---|---|
| `tests/fixtures/topologies.py` | 334 | the ingested triple, in memory | no | 10 factories, parametrised on `n` and per-element durations |
| `tools/gen_synthetic_scale_run.py` | 616 | the ingested triple on disk, seeded | no | layers × modules × builders, one archetype |
| `tests/fixtures/synthetic_multi_subproject/build_model.py` | 258 | the ingested triple **plus** a Chrome trace through the real converter | no | one hardcoded `ELEMENTS` dict |
| `examples/05,06/generate_sources.py`, `09/generate_bulk.py` | 348 | source files only, into a hand-written project | to build, yes | none — each is one fixed shape |
| `examples/01..09` | — | hand-written `.bst` projects | to build, yes | hand-authored |

Three generators, and **all three start after `bst` would have run.**
They synthesise the ingested form directly. Nothing in the tree
generates a `project.conf` plus `elements/*.bst` that `bst build` can
consume, so Plane 1's real scheduler log, Plane 2's hook and Plane 3's
spine are exercised by exactly nine hand-written projects and by
nothing else.

Someone already felt this. `tests/fixtures/synthetic_multi_subproject/`
ships a `project/` tree — `elements/`, `junctions/`, four subprojects,
a `project.conf` — and its own module docstring says what happened to
it:

> `project/` - a human-readable synthetic BuildStream project tree
> matching the same model (**documentation only, not parsed by bga or
> by this test**)

A buildable project tree, written and then not wired to anything.

### What is missing, per reader

`FINDING_READERS` sorts the 21 findings by who they are for. Coverage
by reader, from `tools/dev_finding_coverage.py` over the tracked tree:

```text
reader               total  produced  declared  NEITHER
local-optimizer          9         4         2        3
recipe-author            4         1         0        3
graph-owner              2         1         0        1
ci-gatekeeper            4         3         0        1
capacity-operator        2         2         0        0
```

"8 of 21" understates it. **The recipe-author has four findings and a
clone can produce one of them.** The graph-owner has two and can
produce one. Those are precisely the two readers whose questions are
about graph shape and about what an element costs — the subject of the
threads this round was asked to audit.

## Required Fix

A written spec — this file's Outcome — naming the axes a finding can
key on, the covering set derived from them, and which half of the
tooling covers which axis. Not a fixture and not a tool: the argument
those two consume, so that `UX-464` and `UX-465` build to an
enumeration rather than to a hunch.

The derivation must run from `FINDING_READERS` and the census outward.
A covering set assembled from what seems like a good variety of graphs
is the same unmeasured claim this repository keeps catching — fixing
guide §5, one level up: the *population* being wrong rather than the
instrument.

## Out of Scope

- Writing any fixture — `UX-464` does that, against this spec.
- Writing the project generator — `UX-465`, against this spec.
- `cache-transfer-cost`: it needs a remote CAS, which is an
  environment this repository has never stood up in CI or in a
  container. Named in the spec as an axis level with no covering
  fixture and no plan for one, so the gap is a decision rather than an
  omission.
- Re-tiering or re-timing anything — this item adds no test and no
  code, so no file's measured duration moves and neither
  `tests/tiers.py` nor `tests/ci_reference.json` has anything to
  re-record.

## Acceptance Test

```bash
python3 tools/dev_finding_coverage.py | tail -12
```

pasted in the Outcome, and every finding it reports as uncovered
appearing in exactly one row of the covering-set table below it.

## Outcome

**Round 72 · 2026-09-01 · Status: 🟢 Done**

### The census this was derived from

```text
$ python3 tools/dev_finding_coverage.py | tail -12
(a clone) 21 findings | 11 produced by a capture | 2 declared unreachable | 8 neither
  neither: blast-radius-ranking
  neither: blast-radius-structural
  neither: cache-transfer-cost
  neither: certified-headroom
  neither: criticality
  neither: execution-bound
  neither: run-mode-incremental
  neither: shared-source-blast
```

Ten findings to cover: those eight, plus `build-failed` and
`failed-task-time`, which are declared unreachable **only because no
committed capture is of a build that failed** — a fact about the
fixture population, not about the findings.

### The axes

A project differs from another along seven axes that some finding
reads. Two projects that differ on no such axis are in the same class,
and a second fixture for them buys nothing.

| | axis | levels |
|---|---|---|
| A | graph shape | chain · diamond · fan-in · fan-out · mesh · shared base with wide dependents |
| B | where the wall-clock sits | chain-bound · scheduler-bound · execution-bound |
| C | run mode | cold · incremental · fully cached · remote-cache transfer |
| D | outcome | success · failure |
| E | source topology | distinct sources · one source, many elements · junctioned subprojects |
| F | sandbox profile | coarse · process storm · fine-grained staging |
| G | scale | ~10 · ~100 · ~1200 elements |

### The covering set

Each uncovered finding keys on one axis, sometimes two. Folding on
that gives **five specs for ten findings**:

| spec | axis · level | closes |
|---|---|---|
| T1 `shared-base-wide` | A: one base, N dependents of unequal weight, two longest paths within a few percent | `blast-radius-ranking`, `blast-radius-structural`, `criticality` |
| T2 `one-source-many-elements` | E: a single source staged into N elements | `shared-source-blast` |
| T3 `ample-capacity` | B: capacity well above concurrency demand, work-dominated | `execution-bound`, `certified-headroom` |
| T4 `the same build twice` | C: cold, then incremental | `run-mode-incremental` |
| T5 `a build that fails` | D: one element exits non-zero mid-build | `build-failed`, `failed-task-time` |

`cache-transfer-cost` is the eleventh finding and has no row: it needs
C's remote-transfer level, which is a remote CAS this repository has
never stood up. Declared, not covered — see Out of Scope.

**Two corrections from building it (`UX-464`, same round).** The table
above is the design; the census is the measurement, and it disagrees
twice:

- `certified-headroom` is produced by **T1**, not T3. Backwards in the
  table: headroom is what a run that queued leaves on the table, so
  the one shape that cannot have any is the fixture built never to
  queue.
- **The set is not minimal.** Only four of the seven findings have a
  single producer; `criticality` and `execution-bound` each come out
  of three or four of the five captures. Any run whose elements do not
  wait on each other is execution-bound whether designed to be or not,
  and criticality goes fractional on any handful of independent
  same-ish tasks. So "five specs for ten findings" was a covering set,
  but a much looser one than the fold suggested — the axes here are
  coarser than the findings' real gates.

`UX-464`'s Outcome carries the per-capture attribution and the
mutations that establish it.

T1 folds three findings because all three read axis A and no other;
T2 stays separate from T1 even though a shared base could also be one
source, because a fixture that varies two axes at once cannot say
which one a red is about.

### Which half covers which axis — the reason it is both

The two arms `UX-459` could not choose between do not overlap:

- **Curated fixtures** (`UX-464`) own axes **A, B, C, E** and the
  analysis-side of D. They are the ingested triple; they are
  deterministic to the microsecond, which is the only way to build
  T1's *two longest paths within a few percent* at all. A real build
  cannot be asked for a near-tie critical path.
- **Generated real projects** (`UX-465`) own axes **D, F, G** and the
  capture side of everything. Axis F does not exist above `bst` —
  process storms and inode-count staging are things the LD_PRELOAD
  hook and the ptrace spine observe, and a synthesised trace can only
  assert what someone already believed about them. A real failed build
  is likewise the only thing that proves the capture path survives one
  (`UX-156`, `UX-148`).

So T1, T2, T3 and the analysis half of T4 are curated; T5 and the
capture-side rechecks are built. That is the whole answer to
`UX-459`'s open question, and it is why the answer is not one arm.

### What this spec became

Five open rows, in dependency order:

```text
UX-463 (this, the spec)
  |-- UX-464  curated set: T1, T2, T3, half of T4     -> closes 6 of 8
  |            (freezes under UX-460, closes most of UX-459)
  `-- UX-465  bga gen-project: axes D, F, G           -> closes T5's 2
        |-- UX-466 stage 3   what the planes could capture and do not
        |-- UX-467           the shape conclusions' negative case
        |                     (also needs UX-464's T1 as the positive)
        `-- UX-468           the guided walk against a planted defect
```

`UX-466` stages 1–2 depend on nothing and can start immediately;
`UX-467` needs `UX-464`; `UX-468` needs `UX-465` stage 4.

### Deviation from the Required Fix

None. No code, no fixture, no test — by design.

### Suite

```text
$ make test
5510 passed, 28 skipped, 1 warning in 298.71s (0:04:58)
$ make lint
All checks passed!
```
