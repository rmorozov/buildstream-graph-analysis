# UX-518: the snapshot's tail pays one BuildStream startup per element

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** `UX-46` (which added the call), `UX-107` (which widened the element set it runs over) | **Found by:** round 77, field report — *"at the end of bga snapshot, bst list contents takes considerable time on big projects"* | **Serves:** anyone capturing a project with more than a handful of elements | **Topic:** capture

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

and the cost is per *invocation*, not per element. Measured on
`examples/09-fine-grained-siblings`, 11 elements, `bst` 2.7.0, the same
container in the same minute, one warm-up call discarded:

```text
A. one call per element (11 calls): total 55.98s, median per call 5.32s
B. one call, all 11 elements:      5.50 / 5.20 / 4.83s, median 5.20s

ratio A/B = 10.8x
```

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

At the measured 5.3s per invocation that is **~11 minutes** of process
startups where one call is ~5 seconds. The 5.3s constant is this
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
`examples/09-fine-grained-siblings` issues **one** `bst` invocation, its
result equals today's per-element result element for element, and both
timings are pasted. Mutation: send two elements to one call and attribute
every path to the first — the equality clause reddens.

## Outcome

_Not started._
