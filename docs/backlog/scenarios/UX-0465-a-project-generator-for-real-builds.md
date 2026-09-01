# UX-465: nothing generates a BuildStream project, so axes D, F and G are hand-authored or absent

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-463` (the axes and which half owns them) · feeds `UX-466`'s stage 3, `UX-467`'s negative case and `UX-468`'s planted defect | **Found by:** round 72, inventorying the generation tooling | **Serves:** the round that needs a build with a known answer and has to hand-write a tenth example to get one | **Topic:** capture

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
