# UX-432: the question library had never been run

**Priority:** High | **Status:** 🟢 Done | **Found by:** round 69, an outside walk of `bga snapshot` → `bga view` → Perfetto | **Serves:** every future round that touches the trace or the query library | **Topic:** guards | **Area:** tools

## Motivation

`bga/viewer/questions.js` ships fourteen questions the page hands a
reader to paste into Perfetto. `UX-312`'s guard holds their
*vocabulary* against the emitter's — every `debug.` key a question
names is one the trace writes — and that check is right, because it
runs everywhere.

What it cannot say is whether a question **returns anything**.
`extract_arg` answers null rather than failing, so a question whose keys
all exist can still come back empty in silence. That is the exact
failure `UX-312` was written after, one level further out.

Answering it needs Perfetto's own reader. The repository has a gate for
that — `tests/trace_processor.py`, `UX-321`'s one place — and it skips
when `trace_processor_shell` is absent:

```python
REASON = "trace_processor_shell is not installed"
```

**It has been absent on every machine this project has run on.** So
fourteen questions shipped to readers had never been executed once, and
the skip census counted the skip as normal.

Run at last, against a 1,202-element capture with both planes and
14,424 traced processes, three came back empty. One of them was
`graph-levels` — the question that resolves the dependency graph's
shape, and the one a field report said could not be made to work.

The friction that kept this from happening was small and total: the
binary is a 14 MB download nobody had scripted, and `get.perfetto.dev`
is a redirector some proxies refuse.

## Required Fix

- **A command that runs the library against a trace**, reporting per
  question: rows, empty, or the reader's error.
- **It fetches the reader** if none is on `PATH` or named by
  `BGA_TRACE_PROCESSOR`, from the bucket rather than the redirector,
  at a pinned version — an unpinned reader makes two runs
  incomparable, which is why `gen-synthetic` takes a seed.
- **Empty and refused are different findings**, and the exit code says
  which: empty means the trace cannot answer, an error means the
  question is malformed. A harness that blurred them would have told
  this round that all fourteen were fine.
- **The element it substitutes comes from the trace** (`UX-369`'s rule,
  reaching the harness) and is printed, so the pick can be checked.

## Out of Scope

- **Fixing the three empty answers**: filed as `UX-431`, which also
  carries the absent `analyze.json` finding. This item builds the
  instrument; what it found is somebody else's row.
- **Running this in CI**: the reader is a 14 MB download per job and
  the value here is a round's audit, not a per-commit gate. Revisit
  when a fixture with an `analyze.json` exists to run it against.
- **New questions** — `UX-433` holds the pivot-by-executable work.

## Acceptance Test

```bash
python tools/dev_perfetto_queries.py /tmp/two.pftrace --fetch
```

names every question and whether it answered. The guard's mutations
must redden it: reporting a refused query as empty, dropping the
`{element}` substitution, always exiting zero, and picking the element
alphabetically again.

## Outcome

**Round 69, 2026-08-30.** Landed as `tools/dev_perfetto_queries.py`
with `tests/unit/test_the_questions_are_asked_of_a_real_trace.py`.

The gap, measured. Perfetto v57.2, against
`audit/twoplane/20260830T120000Z` — 1,202 elements, 14,424 traced
processes, 795,537 B of trace:

```text
  element-time         Plane 1         21 row(s)
  graph-levels         Plane 1          1 row(s)
  process-storm        Plane 2         25 row(s)
  sandbox-tax          both planes     20 row(s)
  stalls               Plane 1         20 row(s)
  element-commands     Plane 2         12 row(s)
  dependency-wait      Plane 1          0 row(s)  <-- EMPTY
  time-by-kind         Plane 1          3 row(s)
  failed-processes     Plane 2          0 row(s)  <-- EMPTY
  cpu-versus-wall      Plane 2         25 row(s)
  peak-rss             Plane 2         25 row(s)
  waited-on-flow       Plane 1          1 row(s)
  concurrency-curve    Plane 2         25 row(s)
  which-run-is-this    run              1 row(s)

empty:  2/14  ['dependency-wait', 'failed-processes']
errors: 0/14  []
```

Both remaining empties are the fixture, not the tool: it has no failed
process, and its spans overlap so heavily that nothing finished before
`layer00/mod000.bst` began. `graph-levels` returned **0 rows** until an
`analyze.json` was placed beside the snapshot — that is `UX-431`.

**Two guards of my own that did not discriminate**, found by mutating
rather than by reading, and worth more written down than quietly fixed:

```text
baseline                                        7 passed
M1 a refused query is reported as empty         2 failed, 5 passed
M2 the element placeholder stops being filled   6 passed   <-- did not
M3 the command always succeeds                  2 failed, 5 passed
M4 the element is picked alphabetically again   6 passed   <-- did not
reverted                                        7 passed
```

`M2` passed because the clause read `results[].first` — the *first* row
— while the stub emitted its `NO-SUBSTITUTION` marker as the second,
behind a plausible one. `M4` passed because the stub recognised the
element-pick query by the text of the ordering it was meant to detect,
so a changed ordering fell through to the generic branch and answered
the same element either way — **the stub could not tell the two picks
apart, which is precisely what the clause claimed to check.** Both are
the "guard whose setup excludes what it tests" class, sightings eight
and nine.

After rewriting the stub to answer the two orderings differently and to
emit the marker as the only row:

```text
baseline                                        7 passed
M1 a refused query is reported as empty         2 failed, 5 passed
M2 the element placeholder stops being filled   3 failed, 4 passed
M3 the command always succeeds                  2 failed, 5 passed
M4 the element is picked alphabetically again   1 failed, 6 passed
reverted                                        7 passed
```

**The element pick was wrong twice before it was right**, which is why
it carries a docstring. `min(element)` chose `all.bst`, the target,
which waits for nothing; longest-duration alone chose `toolchain.bst`,
the root, which is the source of every flow in the capture and the sink
of none. Both made `waited-on-flow` report empty — the harness blaming
the trace for a question it had asked of the one element with no answer.
The rule now is: prefer an element that waited, then the longest.

**Deviation from the Required Fix:** none.

```text
make lint    clean
make test    5325 passed, 26 skipped, 310.25s
```
