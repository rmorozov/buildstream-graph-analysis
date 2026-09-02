# UX-196: the views that make the numbers self-evident

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-193 (the shell these views live in), UX-170 (the band), UX-171 (the blast table), UX-103 (cache-trend) | **Topic:** viewer

## Motivation

Direction 7's scenario list, filed as the second wave once UX-193's
shell exists. Three views where a drawing says what sentences have
been straining to:

1. **The band, drawn.** Compare's noise band as a horizontal strip,
   baseline runs as dots, the candidate as a marker — inside,
   outside, or in UX-170's disputed region (outside the band, inside
   the observed range: the marker lands *between* the strip's edge
   and the dots' extent, and the paradox that took a paragraph
   becomes one glance). The refusal verdicts render as the banner
   they are.
2. **The store trend.** The run store as a small timeline: per
   snapshot, total duration (dot), verdict against its baseline
   (color), cache-trend hit rate (line) — `--list` made visual, the
   "is this project drifting" question answered by shape. Failed /
   interrupted / suspended snapshots marked, not hidden.
3. **The blast explorer.** The Shared Sources table with each row
   opening its blast (direct elements, closure, kinds, work — the
   `bga blast` answer rendered); a search box accepting url / path /
   element, backed by the same resolution the CLI uses (served
   through a tiny query endpoint that calls the same function —
   still no viewer-side semantics).

All three render from published JSON plus at most one addition:
scenario 2 needs a `store/v1` listing payload (`--list`'s data as
JSON — which the CLI should gain anyway, one flag, same source of
truth).

## Required Fix

The three views, in the generic-rendering discipline (custom drawing
only where the generic table cannot say it — the band strip and the
trend line are the two custom SVGs, each under ~100 lines, no
library); `bga snapshot --list --format json` producing `store/v1`;
the blast query endpoint calling `bga/blast.py`'s existing function.

## Out of Scope

- The dependency-DAG view (Direction 7 defers it deliberately —
  waits for a concrete question and its own vendoring decision).
- Any recomputation in the browser beyond layout.

## Acceptance Test

The band view on the round-17 fixture store renders the disputed
region case with the marker between band edge and observed extent
(geometry asserted from the data attributes); the trend view marks
the failed and interrupted snapshots distinctly; the blast search
returns byte-identical JSON to `bga blast --format json` for the
same target (served endpoint vs CLI, digest-compared);
`--list --format json` validates against `store/v1` and the text
`--list` derives from the same rows.

---

## What was built

**`store/v1`** first, because two of the three views needed it.
`bga snapshot --list --format json`, and the text listing now renders
from the *same rows* — a second walk of the store would be a second
answer to what is on disk. Every snapshot carries its stamp, size,
alias and `incomplete_reason`.

**The band, drawn.** The case it exists for is `UX-170`'s disputed
region, and the geometry assertion is that paragraph made checkable:
band 100–110 s, baselines observed 95–118 s, candidate 114 s — the
marker must land past the strip's right edge and short of the dots'
extent. It does, and collapsing the three-way answer to
inside/outside reddens it.

**The store trend.** Incomplete snapshots are drawn as squares rather
than dropped. Both mutations were run: drawing them as circles reddens,
and *filtering them out* reddens — a trend that quietly omitted them
would answer "is this project drifting" with a curated subset.

**The blast explorer.** A search box that is purely transport: the
target goes to `blast.json?target=…`, which calls `bga.blast.blast`.
Verified against the real `examples/06` capture — `core.bst`,
`lib-a.bst` and `app.bst` all returned **byte-identical** documents to
`bga blast --format json`. `measure=False`, because a page should not
block on the whole `UX-168`/`UX-169` pipeline; the payload says
`measured: false`, which is the honest answer.

Two custom SVGs, guarded to stay two, with a guard that the code
contains no statistics vocabulary — the payloads already carry the band
edges, the observed extent and the verdict, and a viewer that did its
own arithmetic would be a second implementation of the analysis whose
first act would be to disagree with the first one.

Tests: 17 (`tests/unit/test_the_views_that_draw.py`). Seven mutations,
each red.

### Four defects, three of them in guards

1. **`_incomplete_reason` never worked.** It passed the run *directory*
   to `load_run_context`, which takes the run-context **file** — and
   caught bare `Exception`, so every row came back `None` and the
   listing quietly claimed no snapshot had ever been incomplete. The
   swallow-a-real-error shape this round has been fixing all the way
   through, written fresh. The catch now names the three failures a
   listing should survive.
2. **A geometry guard insensitive to the axis.** Narrowing the axis to
   the band alone pushed the candidate marker to x=125 — off a canvas
   0–100 wide — and the ordering assertion stayed green, because the
   ordering holds however the axis is chosen. It now also asserts
   everything drawn is on the canvas.
3. **A mutation that wrote the right answer.** The blast-endpoint guard
   was falsified by setting `resolved_as = "element"` — which is what
   `work-a.bst` legitimately resolves to, so the mutation was a no-op
   and proved nothing. Re-run against `keying`, it reddens.
4. **Two of this round's own earlier guards were too crude.** The
   no-CDN guard flagged `http://www.w3.org/2000/svg` — an XML namespace
   identifier, never dereferenced — and the no-arithmetic guard flagged
   the word "regression" in a caption *quoting what compare declines to
   call the result*. Both narrowed to what they meant.

**Deviation from the Required Fix:** the blast endpoint answers with
`measure=False`. The item says "calling the same function the CLI
uses", which it does; declining the measured half is a latency choice
for an interactive page, it is visible in the payload, and `bga blast`
on the command line still measures by default.

