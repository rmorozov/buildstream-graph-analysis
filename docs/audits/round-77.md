# Round 77 — three field reports, measured

Input: three cases from the field, none of them a bug report and all
three about *waiting*.

1. `bst show` and `bst artifact list-contents` take considerable time at
   the end of `bga snapshot` on big projects — optimise, or show
   progress?
2. Convenience commands to bundle a run and carry it to another machine.
3. `bga view`'s Perfetto button says nothing for minutes on a big
   capture.

A review-shaped round: it measures and files, and changes no code. Four
rows — `UX-518`, `UX-519`, `UX-520`, `UX-521`.

## Case 1 — the tail is O(N) process startups, and one of them is free

Two separate things were named and they turned out to be in opposite
states.

**`bst show --deps all` is already handled.** One invocation, and
`UX-183` put an elapsed ticker on it with the argument still in the
source: *"there is nothing to count — `bst` is a subprocess and its
stdout is the payload, not a progress stream. Elapsed seconds are the
honest signal."* Nothing to do; recorded so it is not re-filed.

**`bst artifact list-contents` is called once per element**, and the
cost is per invocation. `examples/09-fine-grained-siblings`, 11
elements, `bst` 2.7.0, same container, same minute, warm-up discarded:

```text
A. one call per element (11 calls): total 55.98s, median per call 5.32s
B. one call, all 11 elements:      5.50 / 5.20 / 4.83s, median 5.20s
                                                        ratio A/B = 10.8x
```

Eleven elements in one call cost what one element costs, because
`bst artifact list-contents` takes `[ARTIFACTS]...` and the loop was
handing it one at a time. The population on a real project, read out of
the published capture `953683fb-incremental-b4j4-33302016575`'s own
`graph.json`:

```text
elements in the graph                 126
build edges                           663
distinct build-dependency successors  124   <- the upper bound on `needed`
```

124 × 5.3s is **~11 minutes** where one call is ~5 seconds. The constant
is this container's; the shape — flat in the number of elements per call
— is what the row is about. `UX-518`.

And the phase has no progress line, alone among the `bst`-driven phases:

```text
:1240  ticker("parsing trace")   :2935  ticker("census")
:1540  ticker("pairing")         bst_show_to_graph:253  ticker("bst show")
read_artifact_contents           — none
```

It runs between the census and the report, so the silence the field
report describes is exactly this gap. `UX-519`, serial after `UX-518`
because batching changes what the line would say.

## Case 2 — portable already; what is missing is knowing what to pack

A run directory copied out of its store, to an unrelated path, analysed
from an unrelated working directory, on no project:

```console
$ cd /tmp && bga analyze /tmp/.../moved/run
Build Efficiency Report
Run: golden-fixture-manifest-hash-v1
$ echo $?
0
```

So there is no portability defect to fix. The trap is that **`run/` is
not the capture**: `UX-381`'s layout puts Plane 2, the resource scalars,
the host samples, the published analysis and the capture context
*beside* `run/`, not inside it. A user who tars the directory every
command's help names takes Plane 1 and leaves the rest.

Two things fall out that make this worth a row rather than a
documentation line. The layout is already a versioned contract, so
`load` can refuse a bundle it cannot read instead of half-reading it.
And `UX-186`'s host manifest lives inside `run-context.json`, so it
travels — a capture carried from a runner to a laptop keeps the evidence
that it was measured elsewhere, and the cross-host refusal still fires.
A bundle format that rewrote or dropped the manifest would turn that
refusal off by accident, which is the one way this row could do harm.
`UX-520`.

## Case 3 — one sentence at t=0, then nothing, for two different reasons

A capture over `TRACE_BUDGET_B` (4 MiB) takes the deep-link path: the
page points the new tab at the trace URL, announces the size once, and
returns. Perfetto then fetches from `bga view`'s own server and parses,
which on a big capture is the several minutes the report describes, and
the page's last word is a sentence written before any of it started.

The sharper finding is not the missing spinner. **"Perfetto is fetching
and parsing" and "Perfetto never fetched anything" render identically** —
one sentence and a blank tab — and they want opposite actions.
`UX-314` already predicts the refusal it can predict; this is the case
where the fetch was allowed and either has not happened or has not
finished.

The fact the page lacks is one the server holds: the trace is served by
`bga view`'s own handler, so this process sees Perfetto's `GET` arrive
and complete, and nothing asks it. `UX-521`.

## What this round did not do

No code. Four filings and this document, per the shape a review round
takes here — a round that fixes what it finds stops being able to see
the next thing.
