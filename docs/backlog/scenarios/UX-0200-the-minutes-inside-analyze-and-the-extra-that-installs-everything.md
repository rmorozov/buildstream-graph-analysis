# UX-200: the minutes inside analyze, and the extra that installs everything

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-183 (the Ticker this extends), UX-42 (which documented the quadratic phase)

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
