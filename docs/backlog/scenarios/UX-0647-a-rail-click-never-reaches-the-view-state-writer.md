# UX-647: a rail click never reaches the view-state writer

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-211 (URL state), UX-225 (the working set travels in the link), UX-640 (which measured it) | **Found by:** round 87, track B, settling a question UX-640 got half right | **Serves:** anyone who navigates by the rail and then shares the link | **Topic:** viewer

## Motivation

`wireViewState` delegates from `#report`. The rail is not inside it:
`app.js:915` inserts the contents block after `#actions-group`, a
**sibling** of the report. So no rail click reaches the writer, and
the fragment it should have refreshed is replaced by the bare anchor
the link carries.

Measured on the exported `macro_micro` page, served, Chromium:

```text
report.contains(rail entry)                   false

after collapsing `floors`
  #~c=floors&v.elements=All+elements&n.binary_cost=25%3Acalls
after clicking rail `elements`
  #elements
after the next click anywhere inside #report
  #elements~c=decision%2Cfloors&v.elements=All+elements&…
```

The document keeps the state — `data-collapsed="true"` survives the
navigation — so nothing looks broken on screen. Only the **link**
loses it, and only until the reader happens to click something inside
the report, at which point it silently comes back. A reader who
navigates by the rail and copies the URL at that moment hands over a
report with their working set stripped.

`UX-640` recorded this as measured-and-not-a-defect on the reasoning
that `captureView()` re-derives the query from the DOM. It does — but
only when it runs, and for a rail click it never does. The half that
was right is that the hrefs are `#${key}` and not bare `#`.

## Required Fix

The writer hears the controls that change the view, wherever they are
drawn. Either the rail is inside the delegation root, or the wiring
covers both — decided by whether the rail is part of the report or
chrome around it, which is a question `app.js:910`'s comment already
answers for reading order and should answer once for events too.

The guard is the measurement above: collapse a section, click a rail
entry, and read the fragment without any further interaction.

## Out of Scope

- The fold-timing defect — `UX-646`, same writer, a different reason
  the fragment lags.
- Where the rail is drawn. `UX-208` put it there for reading order,
  and this row must not move it to make an event listener simpler.

## Acceptance Test

Served, both fixtures: set any view state, click a rail entry, and the
fragment still carries the query with no further click. A mutation
restoring the `#report`-only delegation reddens it.

## Outcome (round 88, 2026-09-04) — 🟢 Done

**Premise:** held. `wireViewState` delegated from `#report`, the rail
is its sibling, and no rail click reached the writer.

### The gap, measured

Served, `macro_micro`, Chromium, at `a5bca33`: collapse a section,
click a rail entry, touch nothing else.

```text
report.contains(rail entry)                     false
after collapsing `decision`
  #~c=decision&v.elements=All+elements&n.binary_cost=25%3Acalls
after clicking rail `readers`
  #readers
after the next click anywhere inside #report
  #readers~c=decision&v.elements=All+elements&n.binary_cost=25%3Acalls
data-collapsed on `decision`, throughout        true
```

The document keeps it throughout; only the link loses it.

### After

```text
after clicking rail `readers`
  #readers~c=decision&v.elements=All+elements&n.binary_cost=25%3Acalls
```

The listener moved to `root.ownerDocument`; `captureView` still reads
`root`. The rail did not move — `app.js:910` places it as chrome above
the report, so the wiring covers both, which is the branch the Required
Fix names. **`UX-646`'s mechanism lands in this commit and is
load-bearing here**: the anchor's navigation rewrites the fragment
after the click dispatch, so a write made during it is overwritten.

`tests/unit/test_a_rail_click_reaches_the_writer.py`, **8 passed** in
3.93s (MEDIUM, tiered on landing): two served fixtures, plus three node
clauses that hold the wiring where there is no Chrome.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| M1 | `const on = root` — the `#report`-only delegation | 4 failed / 24 passed: the served query clause (`'decision' in ['']`) and all three wiring clauses. Nothing in `UX-646`'s file |
| M2 | the delegated-`click`-only write (`UX-646`'s defect) | this item's served query clause, plus 5 there and 2 in `UX-642`'s file |

M2 is recorded here because it reddens *this* served clause too; the
three node clauses stay green under it, which is what says they hold
the delegation and not the timing.

**A guard that did not discriminate at first:** the fold file's node
harness read its listeners off `root.ownerDocument` only, so M1
reddened it for something that is not its claim. It reads them from
wherever the wiring put them now.

### Deviation from the Required Fix

None on the fix. Four surfaces outside the Decomposition, each forced,
and two derived documents left for the orchestrator - the index rows
and `fixing-guide.md`'s test-file count:

- `test_the_report_you_can_attach.py`: the `macro_micro` bound,
  475,000 → 480,000. +320 B of source lands the export at 474,987, and
  that bound had **375 B** of headroom at `a5bca33`, not the ~4.9 KB
  its note claimed. Re-measured and argued there.
- `test_the_rail_takes_a_step.py`: reads the **anchor half**. A rail
  press writes the query beside the section now.
- `test_the_page_has_a_reader.py`, `test_the_fold_says_how_deep_it_goes.py`:
  wait one turn before reading the hash, the write being deferred.

```text
make test-touching   20 file(s) selected · 583 passed, 3 skipped in 39.99s
make lint            ruff + PyMarkdown, All checks passed!
make test            26 failed, 6931 passed, 125 skipped in 263.56s - 19
                     `bst` ("Cache too full", pre-existing here), 5 the two
                     index rows, 2 `fixing-guide.md`'s test-file count.
```
