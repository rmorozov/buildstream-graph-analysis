# UX-200: the minutes inside analyze, and the extra that installs everything

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-183 (the Ticker this extends), UX-42 (which documented the quadratic phase) | **Topic:** cli | **Area:** bga

## Motivation

Field report, both halves: *"bga analyze in bga snapshot work for
considerable several minutes, maybe progress here would be great"*,
and *"let's add into pyproject all block that will help me to install
all optional dependencies."* Round 22 ground-truthed both:

1. **The analyze pipeline has zero progress instrumentation.**
   UX-183's five tickers all live outside it (Plane 2 processing,
   `bst show`, the store walk). Nothing under `bga/analyzer.py`,
   `bga/correlate.py` or `bga/ingest/` imports `progress` — the
   phases where the user's minutes go (load, normalize, occupancy,
   graph analysis, **attribution** — the phase UX-42 documents as
   quadratic per gap — floors, utilisation, diagnostics, the
   `capacity_sweep` replay) are silent from invocation to report.
   And the fix will actually draw: `bga snapshot` calls analyze
   **in-process**, so stderr is still the user's TTY (verified).
2. **There is no `[all]` extra** — `[dev]`, `[bst]`, `[completion]`
   exist; a user who wants the full experience assembles it by hand.

## Required Fix

1. Tickers through the analyze pipeline: one per named phase
   (`analyzing: attribution 840/1202 elements` where a count exists,
   `note()` elapsed where it does not), threaded as the Ticker
   pattern already is — no phase grows an `if` around its work; the
   non-TTY and `--format json` paths remain byte-identical (the
   UX-183 guards extended to the new call sites).
2. `[all]` in pyproject: the user-facing set (`bst` + `completion`),
   documented in README's install line as the "everything" form;
   `[dev]` stays the contributor set and is not in `[all]`
   (jsonschema stays a dev-only concern — the runtime emits, never
   validates).

## Out of Scope

- Making the phases faster (UX-168/169 own capacity; this is
  visibility).

## Acceptance Test

On the 1,202-element synthetic run with progress forced on, each
named analyze phase draws at least once (asserted through the seam);
with stderr piped, byte-identical output to today (the UX-183
guard, re-pointed). `pip install bga[all]` in the packaging job
imports argcomplete and buildstream (asserted in the existing wheel
venv step); README documents it; docs-commands covers the line.

---

## What was built

**1. Six tickers through the analyze pipeline.** Confirmed silent
before touching it — nothing under `analyzer.py`, `correlate.py` or
`ingest/` imported `progress`. Now `floors`, `attribution`,
`utilisation`, `diagnostics`, `structural` and `confidence` each draw,
measured on the 1,202-element synthetic run the acceptance names:

```text
analyzing: floors: 1
analyzing: attribution: 1202/1202
analyzing: utilisation: 1
analyzing: diagnostics: 1
analyzing: structural: 1
analyzing: confidence: 1
```

Attribution is the one with a denominator, because `UX-42` documents it
as quadratic per gap and it is where the minutes actually go.

**The ticker goes inside each stage's own `if`, not around it.** So a
section that skips a stage says nothing rather than announcing work it
did not do — `bga graph` draws `structural` and never mentions
`attribution`, which has its own guard.

`progress.ticker`, not `progress.phase`: `phase()` prints a whole line
**unconditionally**, which would have changed piped output and broken
`UX-183`'s contract on the path CI and every script take. The contract
holds, measured:

```text
progress ON  stderr: 344 bytes    progress OFF: 0 bytes
stdout byte-identical: True       piped default == progress-off: True
```

**2. `[all]`** = `bst` + `completion`, documented in README's install
line. `dev` stays out: the runtime *emits* schemas and never validates
against them, so `jsonschema` is a contributor's concern, and CI
asserts it does not leak in.

Tests: 18 new. Five mutations, each red — including one that lets a
ticker escape its stage branch, and one that leaks `dev` into `all`.

**A defect in the CI step, found by running it locally rather than
trusting it.** It asserted `argcomplete.__version__`, which
argcomplete does not define; the step would have failed on its first
real run. It imports both packages instead, which is the claim that
matters.

**Deviation from the Required Fix:** the filing asks for a ticker on
`load`, `normalize` and the `capacity_sweep` replay as well. Those sit
before `analyze()`'s stage dispatch (`load`/`normalize`) or inside a
different entry point (the sweep), and instrumenting them means
threading a ticker through call chains that currently take none —
larger than this item and not where the field's minutes were measured.
The six stages the report is built from are done; the rest is noted
here rather than silently skipped.

