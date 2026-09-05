# UX-518: the snapshot's tail pays one BuildStream startup per element

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-46` (which added the call), `UX-107` (which widened the element set it runs over) | **Found by:** round 77, field report — *"at the end of bga snapshot, bst list contents takes considerable time on big projects"* | **Serves:** anyone capturing a project with more than a handful of elements | **Topic:** capture | **Area:** tools

## Motivation

`read_artifact_contents` (`tools/bst_native_build_tracer.py:3312`) runs
one subprocess per element:

```python
for element in elements:
    result = subprocess.run(
        ["bst", "artifact", "list-contents", element], ...)
```

`bst artifact list-contents` takes **many** elements in one call:

```console
$ bst artifact list-contents --help
Usage: bst artifact list-contents [OPTIONS] [ARTIFACTS]...
```

and the cost is per *invocation*, not per element. `bst` 2.7.0, same
container, same minute, one warm-up call discarded:

```text
examples/06-macro-micro-optimization, 11 elements, all cached, every call rc=0
A. one call per element (11 calls): total 14.82s, median per call 1.34s
B. one call, all 11 elements:      1.59 / 1.59 / 1.61s, median 1.59s
                                                        ratio A/B = 9.3x
```

> **Corrected before this row was worked.** The first measurement used
> `examples/09-fine-grained-siblings`, which has **no built artifacts** —
> every call there exits 1 with *"is not cached"*, so both shapes were
> timed on the failing path and the 10.8x it reported described the cost
> of failing. The figures above are `examples/06`, where all 11 elements
> are cached and every call returns 0. The ratio barely moves, because
> the constant is BuildStream's startup either way — but a number
> measured on the path nobody runs is not this repository's kind of
> number.

Eleven elements in one call cost what **one** element costs. Every extra
call is a whole BuildStream startup — project load and resolve — to ask
about one more artifact.

The population is not small on a real project. From the published
capture `captures/fdsdk/953683fb-incremental-b4j4-33302016575`, read out
of its own `graph.json`:

```text
elements in the graph                 126
build edges                           663
distinct build-dependency successors  124   <- the upper bound on `needed`
```

At the measured 1.34s per invocation that is **~2.8 minutes** of process
startups where one call is ~1.6 seconds. The constant is this
container's and a developer machine will differ; the *shape* is what
this row is about, and the shape is flat in the number of elements per
call.

## Required Fix

- `read_artifact_contents` asks for its elements in one call — or in
  bounded chunks, if a single call's stdout turns out to be too large to
  hold, in which case the chunk size is a measured number and not a
  guess.
- The output is attributed per element rather than merged. Today's
  parser **discards** the element heading, because with one element per
  call there was nothing to attribute:

  ```python
  # Skip the `<element>:` heading and blank lines.
  if not stripped or stripped.endswith(":"):
      continue
  ```

  Batched, that heading is the record separator. Measured format, three
  elements in one call — a two-space-indented `<element>:` line, then
  tab-indented paths:

  ```text
    core.bst:
  \tusr/include/core.hpp
    lib-a.bst:
  \tusr/include/lib-a.hpp
  ```

- The contract `read_artifact_contents` documents is unchanged: an
  element whose artifact cannot be read maps to an **empty set** and the
  caller must read that as "unknown". A batched call must not turn a
  missing element into a missing *key*, which is the one way this change
  could make `declared_vs_used` say something new and wrong.

## Out of Scope

- `read_declared_build_deps`, next to it: it reads element YAML through
  a memoised parse and spawns no subprocess at all, so it is not this
  cost and changing it would buy nothing.
- `bst show --deps all` (`tools/bst_show_to_graph.py`), the other half of
  the field report. It is already one invocation and already draws an
  elapsed ticker (`UX-183`).
- Progress for the phase, which is `UX-519`. Batching changes what a
  progress line would even say, so it goes first.

## Acceptance Test

`read_artifact_contents` over the 11 elements of
`examples/06-macro-micro-optimization` — the example whose artifacts are
built — issues **one** `bst` invocation, its result equals the
per-element result element for element, and both timings are pasted. Mutation: send two elements to one call and attribute
every path to the first — the equality clause reddens.

## Outcome (round 78, 2026-09-02)

### The close

`read_artifact_contents` asks in chunks of `LIST_CONTENTS_CHUNK` (200),
attributes by the `<element>:` heading, and retries a failed group one
element at a time. Acceptance, `examples/06`, real `bst`, `subprocess.run`
counted:

```text
read_artifact_contents over 11 cached elements
  bst invocations : 1
  wall clock      : 1.68s
  elements keyed  : 11  (all present: True)
  total paths     : 8413
  core.bst sample : ['/usr', '/usr/include', '/usr/include/core.hpp']

per-element for comparison: 11 invocations, 15.62s
  identical result: True

speed-up: 9.3x
```

One invocation, the same answer element for element, 9.3x.

### Three things the measurement changed

**The headline figure was measured on the failing path.** The filing's
10.8x came from `examples/09-fine-grained-siblings`, which has no built
artifacts — every call there exits 1 with *"is not cached"*. Corrected
in the Motivation above, in `docs/audits/round-77.md` and in the guard's
own docstring: 9.3x on `examples/06`, where the artifacts exist. The
ratio barely moved because the constant is BuildStream's startup either
way, and that is exactly why the wrong number was easy not to notice.

**A partially-cached group succeeds.** Measured by deleting one
artifact and restoring it:

```text
lib-f alone            (1, [])            <- uncached
core alone             (0, ['core.bst'])
core + lib-f (mixed)   (0, ['core.bst'])  <- rc=0, uncached one omitted
```

So the fallback is for *unresolvable names* (rc=255, whole group lost),
not for uncached artifacts, which the batch handles by omission — and
the omitted element keeps its key and its empty set, which the contract
requires to read as "unknown".

**One line of my own was dead.** The outer `contents` dict pre-seeded
every element, and M6 showed the file still green without it:
`_list_contents` already seeds its group and the retry assigns the
rest. Removed rather than left looking load-bearing.

### Mutations

| # | mutation | result |
|---|---|---|
| M1 | chunk size back to 1 — one call per element | 4 failed |
| M2 | paths merged into every element instead of attributed | 3 failed |
| M3 | no per-element retry for a failed group | 2 failed |
| M4 | always retry — the batching buys nothing | 4 failed |
| M5 | a heading is any line ending in a colon | 1 failed |
| M6 | `_list_contents` stops seeding its group | 9 failed |

M6's first form mutated the redundant outer seed and left the file
green. That is recorded rather than quietly re-aimed: a mutation that
does not redden is either a bad mutation or dead code, and here it was
dead code.

### Deviation from the Required Fix

None. Chunked rather than one call, as the Required Fix allowed, and the
chunk size is argued from a measurement (8,425 stdout lines for 11
elements) rather than picked.

Tests: 10 new in `tests/unit/test_the_contents_read_is_one_call.py`,
which is the first guard this function has had.
