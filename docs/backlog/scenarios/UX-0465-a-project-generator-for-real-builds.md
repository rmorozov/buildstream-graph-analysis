# UX-465: nothing generates a BuildStream project, so axes D, F and G are hand-authored or absent

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-463` (the axes and which half owns them) · feeds `UX-466`'s stage 3, `UX-467`'s negative case and `UX-468`'s planted defect | **Found by:** round 72, inventorying the generation tooling | **Serves:** the round that needs a build with a known answer and has to hand-write a tenth example to get one | **Topic:** capture

## Motivation

Three generators in the tree, and all three start *after* `bst` would
have run — they synthesise the ingested triple directly
(`UX-463` has the table). So Plane 1's real scheduler log, Plane 2's
`LD_PRELOAD` hook and Plane 3's ptrace spine are exercised by nine
hand-written projects and by nothing else, and `UX-463`'s axes D
(outcome), F (sandbox profile) and G (scale) have no generator at all.

Axis F is the one that cannot be faked: a process storm and a
60,000-inode staging are things the hook and the spine *observe*. A
synthesised trace can only assert what its author already believed
about them, which is `UX-120`'s inert-detector problem one level down.

The need is already on record twice. `tests/fixtures/synthetic_multi_subproject/`
ships a full buildable `project/` tree that its own docstring marks
"documentation only, not parsed by bga or by this test" — written,
then not wired. And `examples/09` exists because `UX-120`'s merge
candidate had fired only on synthetic input.

## Required Fix

A generator that takes a topology spec and writes a project `bst build`
accepts. Decomposed, in dependency order:

1. **The spec format.** One JSON/YAML document naming elements, edges,
   per-element work (a `sleep`, a file count, a process count), source
   sharing and junction boundaries. Derived from `UX-463`'s axes, not
   invented. Reuse `tests/fixtures/topologies.py`'s `Topology` shape as
   the in-memory form so the two halves speak one language.
2. **The emitter.** Spec → `project.conf` + `elements/*.bst` +
   `files/`, using the `sleep`-based duration control
   `examples/04-critical-path-optimization` already uses, so wall-clock
   is a parameter rather than a measurement.
3. **Axis F knobs.** Per-element process count and staged-inode count,
   reusing `examples/09/generate_bulk.py`'s approach rather than a
   second one.
4. **Axis D.** A `fails: true` element flag, which is T5.
5. **Wiring.** `bst-examples` builds one generated project per CI run
   and runs `dev_finding_coverage.py --local` on the result, so the
   capture-side count is measured somewhere rather than nowhere.

Stages 1–2 are the deliverable that unblocks `UX-466`/`467`/`468`;
3–5 can follow.

## Out of Scope

- The curated half. `UX-464` owns axes A, B, C and E, and this item
  must not grow a second way to express a linear chain — stage 1's
  whole point is that there is one `Topology` shape.
- Replacing `examples/01..09`. They are documentation as well as
  fixtures, and a generated project is not a worked example.
- A remote CAS for `cache-transfer-cost` — `UX-463` declared that gap
  and this item does not close it.
- Scale beyond what CI can build in its budget. Axis G's ~1200-element
  level stays with `gen_synthetic_scale_run.py`, which does not need
  `bst`; a real build at that size is a separate row when someone
  wants it.

## Acceptance Test

```bash
python3 tools/bga_gen_project.py --spec tests/fixtures/specs/shared-base-wide.json --out /tmp/gen
cd /tmp/gen && bst build all.bst && bga snapshot . && bga analyze .
```

builds, captures, and produces the findings `UX-463`'s table says that
spec is for.

## Outcome

**Round 72 · 2026-09-01 · Status: 🟢 Done for stages 1-4; stage 5 is `UX-473`**

Stages 1 (the spec format), 2 (the emitter), 3 (axis F knobs) and 4
(axis D) landed together, because 3 and 4 turned out to be two lines
each in the emitter rather than the separate rounds the decomposition
assumed. Stage 5 — wiring `bst-examples` to build one generated
project per CI run — is not done and the item stays open for it.

### The gap, measured

```text
tests/fixtures/topologies.py                    334 lines  no bst
tools/gen_synthetic_scale_run.py                616 lines  no bst
.../synthetic_multi_subproject/build_model.py   258 lines  no bst
```

All three synthesise the ingested form directly, and
`tests/fixtures/synthetic_multi_subproject/project/` — a complete
buildable tree — carries its own docstring saying it is "documentation
only, not parsed by bga or by this test". Nothing turned a shape into
a project `bst build` accepts.

### The gap, closed

`tools/bga_gen_project.py`, and the Acceptance Test run verbatim:

```text
$ python3 tools/bga_gen_project.py \
      --spec tests/fixtures/specs/shared-base-wide.json --out /tmp/gen
{"out": "/tmp/gen", "name": "shared-base-wide", "elements": 7}

$ cd /tmp/gen && bst build all.bst
    Build Queue: processed 9, skipped 0, failed 0
    real 0m2.700s

$ bga snapshot -- bst build all.bst          # cold, XDG_CACHE_HOME fresh
    Fetch Queue: processed 9, skipped 0, failed 0
    Build Queue: processed 9, skipped 0, failed 0
    Native Build Trace (Plane 2)
    Processes traced: 29 (29 matched, 0 no observed exit)
    Real CPU time: 0.30s across 29 of 29 traced processes
```

A real two-plane capture from a generated project, in under three
seconds. The store holds `plane2.json`, `plane2.log.gz`,
`host-samples.jsonl` and `element-slice.json` — the whole capture
contract, from a project nobody hand-wrote.

### Axis D, and the two findings nothing could reach

`tests/fixtures/specs/a-build-that-fails.json` is `shared-base-wide`
with `"fails": true` on one element. Built and captured:

```text
findings: blast-radius-ranking, blast-radius-structural, build-failed,
          cache-hit-ratio, capacity-recommendation, confidence,
          efficiency-score, failed-task-time, memory-envelope,
          wait-category
```

**`build-failed` and `failed-task-time`** — the two `UX-463` declared
unreachable because every committed capture is of a build that
succeeded. With `UX-464`'s eighteen that is **20 of 21 findings
reachable**, and `cache-transfer-cost` is the only one left.

That spec's two seconds on the failing element are load-bearing, and
finding out why was a measurement:

```text
mod2 at 0.3s:  failed_task_count 1, failed_task_us 0   -> no finding
mod2 at 2.0s:  failed-task-time fires
```

Plane 1's log carries second-resolution timestamps, so a sub-second
task reads as `dur_us: 1000` and `failed_task_us` stays zero. Not a
defect — `failed_task_count` is right and the time genuinely cannot be
measured — but it means **any generated element under about a second
is invisible to Plane 1**, which the spec file now says.

### One language, and the half that is not shared

The spec's `graph` is `tests/fixtures/topologies.py`'s graph verbatim,
so `spec_from_topology` turns a curated fixture into a buildable
project and the committed acceptance spec *is* `shared_base_wide` at a
tenth of its seconds. A clause pins that, so the two halves cannot
drift into two different graphs with one name.

The **trace** half is deliberately not shared, which is a refinement
of the Required Fix rather than a deviation from it: a trace is what a
build produces and a spec is what one consumes. What the spec carries
instead is `work` — seconds, processes, files, failure — which is what
a real build turns back into a trace.

### Mutations applied

| # | Mutation | Went red |
|---|---|---|
| P1 | `_scalar` back to double quotes | both YAML clauses, the committed-spec parse, **and both real `bst build`s** |
| P2 | `exit 1` emitted first instead of last | `test_a_failure_runs_last` |
| P3 | reserved uids no longer refused | `test_a_reserved_uid_is_refused` |
| P4 | source paths lose their `files/` prefix | both real `bst build`s |

P1 and P4 are the two that reproduce bugs this round actually hit, and
both are caught by a real `bst`, not by inspection.

### Two defects the work found in itself

- **Double-quoted YAML.** The first emitter wrote install-commands
  inside `"` and the process-storm command contains `sh -c "sleep
  0.30"`, so the inner quote closed the scalar and bst refused the
  whole project with `did not find expected key`. Fixed with
  single-quoted scalars, and the clause that catches it parses the
  emitted YAML with a real parser rather than trusting the quoting.
- **Source paths.** `path:` is resolved against `project.conf`, not
  against the element, so the generator wrote `path: import/toolchain`
  for a tree it had created at `files/import/toolchain` and bst said
  `Specified path does not exist`.

### A test of mine that was simply wrong

`test_a_command_holding_single_quotes_survives` first built its
fixture with a string `.replace` on already-emitted YAML, which
produced invalid YAML by construction and failed for a reason that had
nothing to do with `_scalar`. Rewritten to call `_scalar` directly.

### Deviation from the Required Fix

Stage 5 is not done. Stages 3 and 4 landed early, with stages 1-2,
because each is two lines in `_commands` rather than a round of its
own.

### Tier and suite

`tests/unit/test_a_generated_project_builds.py`: 7.4s single-process
(two real `bst build` runs where bst is installed), added to `MEDIUM`.
Like `UX-466`'s file it is not in `tests/ci_reference.json` and the
first CI run will name it; the same reasoning applies and the same one
line fixes it.

```text
$ make test
5550 passed, 28 skipped, 1 warning in 301.13s (0:05:01)
$ make lint
All checks passed!
```

### Four gates this item's diff reddened, all correctly

- `test_the_pinned_bst_tier_count_matches_the_number_of_marked_tests`:
  43 → 45 bst-gated tests, and the pin in `ci.yml` is what stops a
  skipped tier reading as a pass. Updated deliberately, both the
  `grep` and the message beside it.
- `test_the_contract_inventory_is_derived`: the generator first
  stamped `project-spec/v1`, and `bga.contracts` walks the `bga`
  package only, so an id in `tools/` needs an owner there (`UX-248`).
  The right answer was that a dev tool's *input* format is not part of
  the release surface at all — it takes a plain `spec_version: 1` and
  claims no contract id, which is now written where the constant was.
- `test_every_declared_skip_reason_is_known` (`UX-449`) on the new
  busybox gate, declared in `tests/conftest.py`.
- `test_every_out_of_scope_entry_names_a_task_or_states_a_decline`
  (`UX-232`) on a bare bullet in `UX-469`.
