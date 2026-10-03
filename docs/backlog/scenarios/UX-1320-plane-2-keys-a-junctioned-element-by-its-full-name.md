# UX-1320: Plane 2 keys a junctioned element by its full name, not the short name the shim keeps

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1, R2 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`element_from_build_root` (`tools/native_trace/bwrap_shim.py:250-253`) turns bwrap's
`--dir buildstream/<project>/<element>` into `<element>` and drops `<project>`, though the raw
log carries it (`zcat plane2.log.gz` shows `buildstream/acme-base/pkgs/gcc-libs.bst/...`).
Every Plane 2 consumer then joins on a short name Plane 1 never uses for a junctioned element.
Reproduced on the walk's stand-in (`make-acme.sh` in that folder: three projects, local junctions two levels deep, 16 elements, `pkgs/zlib.bst` in all three) at `19f1fd73`, bst 2.8.1.

```text
By element:
  pkgs/zlib.bst                  426        <- three elements from three projects, one row
$ bga correlate @last
  Not traced, but Plane 1 says they matter: junctions/platform.bst:junctions/base.bst:pkgs/gcc-libs.bst
  6 Plane 2 names are not declared elements and are excluded from the rows below: pkgs/dbus.bst, ...
Key Findings: ... junctions/platform.bst:pkgs/mesa.bst: unpriced — no Plane 2 binary_cost measurement
Declared build dependencies never read: ... skipped junctions/platform.bst:junctions/base.bst:toolchain.bst
  - dependency staged no files
```

`gcc-libs` is the run's #1 critical-path element and Plane 2 holds 382 of its processes.
`_claim_short_names` (`tools/bst_native_build_tracer.py:1743`) counts no top-level vs junction
collision: on carbonOS `groups/core.bst` (316 elements, 140 junctioned) 33 short names exist both
at the top and under `junctions/bootstrap.bst`, and the count read is 0.

## Decomposition

Input classes: a top-level element; a junctioned element whose short name is unique; three
elements sharing one short name across three projects; two junctions resolving to the same
project name (one project junctioned twice) - ambiguous, never merged; a `build-root` override
(no `buildstream/<project>/` prefix - today's last-segment answer stays). Consumers: the Plane 2
report's per-element tables, `correlate`'s join, findings' `binary_cost` pricing, configure tax,
the declared-vs-used read, the element slice.

## Required Fix

The shim keeps `<project>/<element>`. The capture maps each project name to its junction prefix
from the `bst show` it already runs before the build (UX-843: add the `project-name` variable to
the format), and the Plane 2 report keys every element by its full Plane 1 name. A project name
two junctions resolve to is reported as ambiguous and its elements keep the qualified
`<project>/<element>` key rather than merging. `_claim_short_names` counts top-level vs junction
collisions too.

## Out of Scope

Remote junctions' cache-key disambiguation; the jobserver annotation map (UX-1311, already dual-keyed).

## Acceptance Test

A capture of the walk's stand-in project joins 13 of 13 building elements in `bga correlate`,
lists three `pkgs/zlib.bst` rows under three full names, and prices every junctioned element; a
guard reads a recorded or synthesized three-project Plane 2 log and asserts the full-name keys.
Reading taken in this container.

## Outcome
