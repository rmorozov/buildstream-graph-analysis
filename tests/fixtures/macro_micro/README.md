# `macro_micro` — a dual-plane run, committed

One `bga snapshot` of
[`examples/06-macro-micro-optimization`](../../../examples/06-macro-micro-optimization),
taken 2026-08-21, kept here so the guards that check pasted figures
against the tool can run in a clone.

They could not, before. Round 37's first attempt pointed them at the
snapshot `bga snapshot` had written into
`examples/06-macro-micro-optimization/.bga/runs/`, which is **ignored by
design** — `bga snapshot` writes a `.gitignore` containing `*` into
every store it creates (`UX-126`), because captures are build artifacts
(`UX-189`). The guards passed on the machine that had run the build and
failed on every other one, which is exactly the defect `UX-213` named.

## What was kept, and what was dropped

`run/` is verbatim: the three documents `bga`'s loader reads
(`run-context.json`, `graph.json`, `trace.json`), 11 KB together. The
snapshot's `chrome_trace.json` and `sources.json` are not needed by
anything here.

`plane2.json` is the capture's Plane 2 report **without its
`processes` array** — 813 per-process records, 458 KB of the original
584 KB. Everything else is verbatim.

Dropping it changes nothing the guards read, measured rather than
assumed:

```text
                full report      without `processes`
cores_busy      1.603977885512677   1.603977885512677
pinned          ['core.bst']        ['core.bst']
envelope @ 4    613.69921875 MB     613.69921875 MB
elements measured           9                     9
```

`peak_memory.per_element` carries the peaks the memory envelope sums,
and the capacity summary reads the aggregates — neither walks the
process list. A guard that needs per-process records needs a different
fixture, and should say so rather than reaching for this one.

## What it is used by

- `tests/unit/test_the_journey_reaches_what_if.py` (`UX-246`) — every
  `bga whatif` figure the journey guide pastes.
- `tests/unit/test_the_builders_question_has_a_document.py`
  (`UX-242`/`UX-243`) — every constraint line and envelope figure
  `docs/guides/cli.md` pastes.

Both **recompute** rather than compare against a stored expectation, so
a change in what the tool says reddens them.
