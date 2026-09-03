# UX-607: a paragraph in the guide is a two-file change

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-584 (the derived figure), UX-590, UX-603 (both blocked by it) | **Found by:** round 84, twice in one round by two tracks | **Serves:** anyone adding a paragraph to the fixing guide | **Topic:** docs

## Motivation

`UX-584` derives `docs/contributing/fixing-guide.md`'s size into a
sentence, and that sentence is in **two** documents — the guide and
`docs/contributing/rules.md`. Measured at round 84's base:

```text
fixing-guide.md   41,358 B     round(B/1024) == 40
41 KB begins at   41,472 B     headroom  114 B
```

So a paragraph over 114 B forces an edit to the rules card as well.
In a round that runs parallel tracks, the card belongs to a different
track, and two items stopped on it in the same round:

- `UX-590` shipped the `--format` row (81 B) and **not** §6's command
  vocabulary (~920 B), leaving 15 registered commands unheld.
- `UX-603` did not close the guide's half of its own item: 33 B left,
  and the shortest honest sentence is ~44 B.

Neither is a defect in those items. The coupling is the defect: a
figure derived to one byte makes every prose edit a coordination
problem, and the figure's purpose was to stop the *guide's own size*
drifting, not to price paragraphs.

## Required Fix

The size is stated once and the second document references it, or the
figure is bucketed to a width that prose cannot cross by accident —
whichever, argued from what the figure is for. A guard holds the
chosen shape so a third copy cannot appear.

## Out of Scope

- `UX-584`'s reason for deriving the figure at all — declined: it is
  right, and this is about where the derived value is *repeated*.

## Acceptance Test

A 1 KB paragraph added to the guide, and no second document red.

## Outcome (round 85, 2026-09-03) — 🔴 fix landed, row not moved

**Premise: half falsified — the figure had already moved.** Filed at
41,358 B / 114 B; measured at this track's base `d4a3d04`:

```text
$ stat -c '%s' docs/contributing/fixing-guide.md      41,439 B
  round(B/1024) == 40 · 41 KB begins at 41,472 B      headroom 33 B
```

`UX-603`'s 33 B is the live number; 114 B was two edits stale.

**Chosen shape: bucket, not state-once.** The figure is for a *reading
decision* — card first, guide by paragraph — and that decision turns on
the guide being an order of magnitude larger than the card, not on 40
against 41. `UX-584` derived it so the guide's own size could not drift
in prose; one-byte resolution was an accident of `round(B/1024)`, and
it is the whole coordination cost. So the width becomes 10 KB
(`GUIDE_KB_STEP`), both sentences read `~40 KB`, and both documents keep
the argument at the point a reader needs it. State-once was rejected:
the card's number is what stops a session opening the whole guide, and
moving it into the guide puts it where the reader has already gone.

**Close.**

```text
band [35,840, 46,081) B   width 10,241 B   headroom 4,641 B  (was 33 B)
$ PYTEST_XDIST= python3 -m pytest \
    tests/unit/test_the_process_documents_derive_their_figures.py -q
17 passed in 0.43s
$ make lint      All checks passed!
```

**Acceptance Test** — 1 KB of paragraph appended to the guide:

```text
$ python3 -c "...append 1,023 B..."   guide now 42,463 B
$ PYTEST_XDIST= python3 -m pytest <this file> -q
17 passed in 0.41s          # no second document red
```

**Mutations.**

| mutation | anchor confirmed | red | count |
|---|---|---|---|
| `GUIDE_KB_STEP = 1`, 1 KB paragraph in place | line 101 | `…carries_the_derived_sentence[rules.md]` + `[guide]`, `…a_paragraph_does_not_move_the_stated_figure`, `…band_is_what_bought_the_headroom`, `…no_third_document…` | 5 failed, 12 passed |
| `the fixing guide is 40 KB` into `release-guide.md` | line 120 | *green* — see below; after the fix, `…no_third_document…` + `…scan_finds_the_copies…` | 2 failed, 15 passed |
| `_size_population()` drops `CLAUDE.md` | line 141 | `…scan_reaches_the_day_one_summary` | 1 failed, 16 passed |

**A clause that did not discriminate as written.** The third-copy scan
matched `\bthe (?:whole )?guide\b|\bfixing-guide\b`, and a copy writing
`the fixing guide is 40 KB` matched neither — `the guide` does not
match `the fixing guide`, and the hyphen is not in prose. Broadened to
`\bfixing[- ]guide\b|…`; the mutation reds after, and the row above
records both runs. Reach: a copy that states the size without naming
the guide at all (`the card is 5 KB against 40 KB`) is still unseen.

**`BGA_SKIP_SELECTOR=1` on both commits, and why.** Four guards are
red at this track's base `d4a3d04`, verified by stashing this diff:
`…topic_from_the_closed_set` (`UX-611`'s `report`), `…partial_is_not_
wholly_made_of_closed_filings` (Directions 8/9), `…every_module_is_on_
the_map` (`bga/capacity_model.py`), `…check_reports_a_clean_tree_as_
clean`. Their fixes are in `README.md` and `docs/design/directions.md`,
which this track does not own. None moved.

**Deviation from the Required Fix.** None. The second disjunct was
taken and argued above; the guard is four clauses in `UX-584`'s file
rather than a new one, because a second `_kb` would be the drift this
item is about.
