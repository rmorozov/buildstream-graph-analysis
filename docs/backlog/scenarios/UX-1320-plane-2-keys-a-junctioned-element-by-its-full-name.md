# UX-1320: Plane 2 keys a junctioned element by its full name, not the short name the shim keeps

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1, R2 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_plane2_keys_a_junctioned_element_by_its_full_name.py`

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

### The gap, measured

The walk's snapshot `20261003T135009Z` of `/root/walk/jproj` (copied), correlated at `44afd957`:

```text
$ bga correlate @20261003T135009Z -f json   # coverage
{'joined_elements': 10, 'plane1_elements': 16, 'plane2_elements': 10} undeclared 6
plane1_only_with_impact ['junctions/platform.bst:junctions/base.bst:pkgs/gcc-libs.bst']
zlib rows with CPU: ['pkgs/zlib.bst']
$ grep -c unpriced logs/snapshot-1-cold.log; grep -c 'staged no files' logs/snapshot-1-cold.log
6
7
```

### The close, measured

A cold `bga snapshot -- bst build groups/all.bst` on a fresh copy (`/tmp/ux1320-jproj`, private
`XDG_CACHE_HOME`, bst 2.8.1, `PYTHONPATH` the track's worktree):

```text
$ bga correlate @last
Joined 12 elements on element UID (16 in Plane 1, 12 traced in Plane 2)
$ bga correlate @last -f json   # coverage, then the zlib rows
{'joined_elements': 12, 'plane1_elements': 16, 'plane2_elements': 12,
 'plane1_only_with_impact': [], 'undeclared_plane2_elements': [], ...}
pkgs/zlib.bst                                             cpu_us 1221618
junctions/platform.bst:junctions/base.bst:pkgs/zlib.bst   cpu_us 1213784
junctions/platform.bst:pkgs/zlib.bst                      cpu_us 1241411
$ grep -c unpriced snapshot.log; grep -c 'staged no files' snapshot.log
0
0
Declared build dependencies never read: 10 candidate(s) across 8 element(s); 12 dependency edge(s) confirmed used
  Computed over ... 12 of 12 element(s) had every process covered.
plane2.json junction_names: {'projects': 3, 'relabelled_sandboxes': 8, 'ambiguous_projects': []}
```

12, not 13: the project has `12 kind: cmake`, `1 kind: import` (toolchain), `3 kind: stack`
(`grep -h ^kind -r elements subprojects --include=*.bst | sort | uniq -c`); the four unjoined rows
are exactly the import and the three stacks, which run no sandbox. The walk's 13 counts the import.

### Mutations verified red and reverted (9)

`tests/unit/test_plane2_keys_a_junctioned_element_by_its_full_name.py`, 10 tests:

| # | mutation | reddened |
|---|---|---|
| M1 | `project_from_build_root` returns `None` | 1 of 10 |
| M2 | no junction relabel (`name = None`) | 2 of 10 |
| M3 | ambiguity ignored (`ambiguous = []`) | 1 of 10 |
| M4 | top-vs-junction collision uncounted (UX-1311's `":" in owner` back) | 1 of 10 |
| M5 | plain `list-contents` batching | 1 of 10 |
| M6 | `list-contents` heading by full name only | 1 of 10 |
| M7 | a projectless sandbox guessed from its short name | 1 of 10 |
| M8 | the `bst show` gate always off | 1 of 10 |
| M9 | the shim never records `project` | 4 of 10 |

### Deviation from the Required Fix

The live join is 12 of 12 traced (16 in Plane 1), not 13: an import and three stacks run no sandbox. Reverses UX-1311's no-collision assertion: any top-vs-junction short name now counts as a collision. Unguarded: the `%{build-deps}` fill in `load_and_summarize` (removing it stays green). Two forced baseline entries (S603, PLR0913); `dev_sizes` growth not adopted. (`2d1901b2`)
