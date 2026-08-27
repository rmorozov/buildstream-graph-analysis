# UX-329: the terminal and the viewer disagree about Plane 2

**Priority:** High | **Status:** 🟢 Done Done | **Depends on:** UX-202 (plane2_coverage), UX-297 (the report beside the run) | **Serves:** R1, R2 | **Topic:** analysis

## Motivation

Stranger walk friction 15, against `bga view --help`'s own promise
that "the viewer and the terminal can never disagree about what a
run says": on a snapshot carrying `plane2.json`, `bga analyze
@last` publishes `plane2_coverage: null` and never mentions
Plane 2 exists — while `bga view @last` on the same alias serves
the same schema with `plane2_coverage` fully populated, because
the viewer auto-attaches the sibling file and `analyze` requires
`--plane2` and never hints at it (`correlate` auto-finds it too —
analyze is the odd one out). And the absence grammar conflates two
absences: `has_timeline: false` and the export's "no raw Plane 2
log, so there is no timeline to carry" read as "Plane 2 absent"
when the Plane 2 *report* is present and only the raw log was
dropped — a stranger cannot tell "not captured" from "captured,
log not kept".

## Required Fix

`analyze` auto-attaches the sibling `plane2.json` exactly as
`correlate` and the viewer do (one discovery function, three
callers), `--plane2` remaining the override; where the file exists
and is not attached (explicit `--no-plane2`?) the report says so.
The absence grammar splits: "Plane 2 not captured" vs "Plane 2
captured; raw log not kept (no timeline)" — one sentence pair,
used by the terminal, the page and the export (the UX-156
absence-is-stated rule, applied to the plane).

## Out of Scope

- Timeline regeneration from anything but the raw log (nothing
  can conjure it; the sentence just stops implying more).

## Acceptance Test

On the fixture with a plane2 sibling: `analyze` and `view` publish
identical `plane2_coverage` (byte equality — the help's promise
becomes a guard); on a run with report-but-no-raw-log the page and
terminal print the "captured; log not kept" sentence, on one with
neither the "not captured" sentence (both asserted; mutation:
collapse the two sentences → red).

## Outcome (round 47, 2026-08-27) — 🟢 Done

### The disagreement, on one run

```text
$ bga analyze <snapshot>/run --format json | jq .plane2_coverage
null
$ (bga view's payload for the same run)
{"processes": 813, "opens_coverage": 1.0, "source": {"schema": "plane2/v1", …}}
```

One run, one schema, two readers, two answers — against `bga view
--help`'s own sentence that "the viewer and the terminal can never
disagree about what a run says".

### After

```text
analyze plane2_coverage == {"opens_coverage": 1.0, "processes": 813, "source": {…
view    plane2_coverage == {"opens_coverage": 1.0, "processes": 813, "source": {…
BYTE-EQUAL: True
absence equal: True
```

### One discovery function, three callers

The import mattered less than the **policy**. `bga correlate` and `bga
view` each found the sibling and applied a size bound; `analyze` did
neither. Two copies of a rule, and the copies disagreed — the same
shape as `UX-325`, one level up.

`bga/plane2.py` now holds it: `attachable(run_dir)` returns the report
to attach and, when there is one it will *not* attach, the sentence
saying why (`UX-296`'s 64 MB bound, which moved here from
`tools/bga_view.py` with its measurement). `bga view` calls it,
`_attach_plane2_capacity` calls it, and a clause asserts both call
sites by name — because what let them drift was having two.

`--plane2` still overrides (a clause plants a different report and
checks the override wins); `--no-plane2` declines and **says so**.

### The absence grammar, split three ways

One sentence used to cover three situations a reader cannot tell apart:

| | before | after |
|---|---|---|
| never captured | "this run kept no raw Plane 2 log, so there is no timeline to carry" | "Plane 2 was not captured for this run…" |
| captured, log dropped | *the same sentence* | "Plane 2 was captured — its report is beside this run — but the raw trace log…" |
| declined | *silence* | "Plane 2 was captured and this report was asked not to read it (`--no-plane2`)…" |

The first is a machine that could not trace; the second is a complete
measurement missing only its timeline; the third is the reader's own
flag. `absence()` asks the filesystem itself rather than taking a
caller's boolean — three readers call it, and a parameter is a way for
three readers to disagree again.

Published as `plane2_absence` (additive to `analyze/v2`, so no bump),
printed by the terminal, and used by the export.

### What the change exposed

Auto-attaching made the fixture two-plane, and **eleven** tests went
red. Every one was worth reading rather than patching:

* **four tests used a two-plane run as their example of "a run without
  Plane 2"** — including `test_without_plane2_the_block_is_absent_not_empty`,
  which analyzed the real `examples/06` capture. That capture has a
  `plane2.json` beside it; the clause only ever passed because
  `analyze` refused to look. They now use a genuinely single-plane run
  or `--no-plane2`, and one of them asserts that its fixture really has
  no sibling, so it cannot quietly become vacuous again;
* **`UX-288`'s population sweep** flagged two pairs. Both were checked
  before being excused, and both are coincidences of an 11-element
  corpus: five `worst_redundancy` findings with **different signatures,
  commands and durations** naming the same nine elements, and
  `lib-c.bst`'s three unread dependencies matching `joint_saving`'s
  three. The exclusion is *derived* — a key every `element_join` row
  answers for itself is a measure, not a selection — with a positive
  control planting a duplicate on **one** row to prove the exclusion is
  not a hole;
* **`UX-289`'s page guard** found a real duplication, and this is the
  finding of the round. The page draws `element_join` as a second
  whole-population table — and it has done so for **every real viewer
  since `UX-215`**, because `bga view` has attached the sibling since
  `UX-203`. Measured on the tree *before* this change:

  ```text
  BEFORE UX-329, through `bga view`: element_join present = True | rows = 11
  ```

  The guard never saw it because its fixture reached the page through
  `analyze` **without** `--plane2` — the one configuration a viewer
  never has. That is the same defect as this item, in an instrument.
  Filed as [`UX-338`](UX-0338-the-page-draws-the-element-population-twice.md)
  and listed in the guard's expectations as a known duplication rather
  than filtered out, so it reads as carried, not as acceptable.

### Mutations verified red and reverted (4)

Counts are what the runs printed.

| # | mutation | reddened |
|---|---|---|
| C1 | `attachable` returns `(None, None)` — `analyze` stops finding the sibling, the `UX-329` defect exactly | **2**: byte-equality and attaches-without-being-told. *Not* the absence-equality clause — with neither reader attaching, the two still agree, which is a fair thing for it to say |
| C2 | `CAPTURED_NO_RAW_LOG = NOT_CAPTURED` — the two sentences collapsed, the filing's own suggested mutation | **1**: the three-sentences clause, and **only** that one |
| C3 | `absence()` returns `None` always | **5**: the declined clause, both absence clauses, the terminal clause, the export clause |
| C4 | the viewer finds the sibling itself again instead of routing through `plane2_shape.attachable` | **1**: the one-discovery-function clause — the mechanism, not its result, which is why that clause reads the source |

**C2 is the one worth writing down.** Collapsing the two sentences
reddens exactly one clause, because every other clause compares against
`plane2.CAPTURED_NO_RAW_LOG` — and the mutation changes that constant
too, so they all still pass. A guard written only as "the right sentence
is printed" would have been blind to the exact defect this item is
about. `test_the_three_are_actually_different_sentences` exists for
that, and the mutation is what proved it was needed rather than
decorative.

### Deviation from the Required Fix

- The filing asked "(explicit `--no-plane2`?)" tentatively. The flag is
  there, and it is what the negative-space tests now use — without it
  there is no way to *ask* for a single-plane analysis of a two-plane
  snapshot, which four existing tests needed.
- `--plane2`'s help lost a line and `--no-plane2` gained one, to stay
  inside `UX-158`'s 45-line cap. Both flags are listed; neither is
  hidden.
- `UX-338` is filed, not fixed. It is `UX-289`'s subject, it predates
  this change by twenty rounds, and folding the join into the one
  element table is a viewer change this item's Required Fix does not
  ask for.
