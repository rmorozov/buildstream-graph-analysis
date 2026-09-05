# UX-451: the hand-off's refusal sentence is written into a 208px column

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 70, the half of `UX-435` that could not be measured | **Serves:** the reader whose hand-off failed — the only reader who ever sees this sentence | **Topic:** viewer | **Area:** bga/viewer

## Motivation

`#handoff` is the status line inside the rail's hand-off group.
`app.js` writes into it, and one of the things it writes is a refusal:
a sentence of roughly 300 characters explaining that Perfetto's CSP,
or the size threshold, or the pop-up policy stopped the trace opening.

The rail is 240px wide and the group inside it measures 208px. Three
hundred characters at `.82rem` in a 208px column is on the order of
fifteen lines — in a sticky column, on the screen of a reader who has
just had something fail.

`UX-435` bounded the group's *resting* height and left this alone, for
a stated reason: **the sentence could not be produced to measure.** It
appears only when a hand-off actually fails, which needs Perfetto to
refuse a real trace, and a width chosen without seeing it rendered
would be the unmeasured claim this repository forbids. `UX-435`'s guard
therefore bounds the group with the status line **empty**, which is
honest about what it measured and silent about this.

## Required Fix

- **Produce the sentence.** Drive the failure rather than waiting for
  it: `wireTheHandoff` decides from `perfettoCanFetch` and the size
  threshold, both of which a guard can force. Then measure the group
  with the sentence in it, at both viewports, served.
- **Give it a width that is not the rail's**, or a shape that does not
  need one — the same three options `UX-435` weighed for the fallbacks
  apply here, and the third of them (fold the refusal into the status
  line) is what created this.
- **Extend `UX-435`'s bound to the failed state**, so the group is
  bounded in the mode *and* the state where it is largest. That is the
  same rule one step on, and leaving it out is what this row records.

## Out of Scope

- **What the sentence says**: `UX-326` made the tool's sentences
  contracts and this changes where one is drawn, never its wording.
- **The rail's width**: 240px is settled, as `UX-435` also recorded.
- **`UX-435`'s resting bound**, which is measured and holds; this adds
  a state to it rather than replacing it.

## Acceptance Test

```bash
cd examples/06-macro-micro-optimization
bga snapshot -- bst build all.bst
bga view @last --port 8931 --no-browser
```

Force a refusal, measure `#actions-group` at 1440x900 and 390x844 with
the sentence rendered, and paste both. The height is under a stated
bound, and a mutation restoring the sentence to the rail's width
reddens the guard.

## Outcome (round 71, 2026-08-31) — 🟢 Done

### The sentence, produced

`UX-435` could not measure this because the refusal needs Perfetto to
refuse a real trace. It can be driven instead, and the first Required
Fix bullet says how: `wireTheHandoff` reads the size threshold from
`run.trace_inline_max_bytes`, which the server publishes, so a server
started with `TRACE_BUDGET_B = 0` puts every trace over it. The other
half of the condition - that `ui.perfetto.dev`'s own `connect-src` does
not allow this origin - is **already true** of the ephemeral port
`serve(port=0)` binds, and was not forced at all.

Measured served on `tests/fixtures/with_timeline`, through Chromium,
with the refusal driven that way:

```text
                      group          share of rail   status line
1440x900   before   208x408px            50.7%        204x297px
            after   208x106px            13.2%          (empty)
 390x844   before   327x248px            80.0%        326x204px
            after   327x62px             50.0%          (empty)
```

294 characters. In a 204px column that is **297px of a sticky rail** -
about twenty lines, on the screen of the reader who has just had
something fail. The item guessed fifteen; it was worse.

`106px` and `62px` are not new numbers: they are exactly the resting
figures `UX-435` measured. The group returns to its resting height in
the refused state, which is why `BOUND_PX` and `BOUND_SHARE` are
**unchanged** rather than raised, and why the third Required Fix bullet
is met by the fix rather than by a looser bound.

### The shape it got

The second bullet's first option: **a width that is not the rail's**.
`#handoff-refusal` is a sibling of `#actions-group`, so it stays in the
content column when `app.js` moves the group into the rail at boot, and
it has its own grid band spanning both panes.

```text
                banner
1440x900     649x106px    max-width: 68ch inside a 1024px content band
 390x844     327x222px    the whole viewport - there is no second column
```

Not a fold, and not a rewrite. `UX-326` makes the sentence a contract,
so `announceHandoff(status, text, {refused})` decides *where* a state is
drawn and never a word of it; the classification is the call site's,
because a threshold on `text.length` would be a number nobody could
argue. Exactly one of the two elements holds the state at a time - the
short path clears the banner, the long path clears the line - so
`UX-371`'s repeated text does not reappear as the same sentence twice.

### The 240px the first attempt measured

Worth recording, because it is the item's own defect one level in.
The banner was given `max-width: 68ch` and no grid area, and CSS
auto-placement put it in **the rail's column**: 240x315px at 1440x900,
a `max-width` that cannot widen a track. The measurement is what
caught it - the fix looked right in the source and was the same defect
in a different element. `R2` below is that state, kept as a mutation.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| R1 | the refusal goes back into the rail's status line | `..._group_holds_its_resting_bound_while_refused[1440-900]`, both `..._sentence_is_not_written_into_the_rail`, both `..._rail_says_nothing_it_has_no_room_for` (8 failed, 8 passed) |
| R2 | the banner loses its grid band, and auto-places into the rail's column | `..._sentence_is_not_written_into_the_rail[1440-900]` — `the banner is 240px, under the 600px measured` (1 failed, 7 passed) |
| R3 | the banner is a child of the group, so it travels into the rail | both `..._group_holds_its_resting_bound_while_refused`, both `..._sentence_is_not_written_into_the_rail` (4 failed, 4 passed) |
| R4 | the sentence is truncated to 80 characters to fit rather than moved | both `..._refusal_really_rendered` — `assert 80 >= 250` (2 failed, 6 passed) |

R4 is the one that matters most: without `REFUSAL_MIN_CHARS`, every
bound in the file could be met by shortening the sentence, which is
what the Out of Scope section forbids.

### What it cost the suite, and the tier

The file gained a second served page and a second browser. Measured
single-process on the same machine either side:

```console
$ PYTEST_XDIST= python3 -m pytest \
    tests/unit/test_the_handoff_box_is_measured_served.py --durations=0 -q
before  14.22s
 after  28.78s
```

Past `LARGE_FLOOR_S` (15.0), so it moves from medium to large - and the
comment beside it in `tests/tiers.py` said "14.2s, just under the large
floor", which is a note about a file one clause from crossing it.

`tests/ci_reference.json`'s row was **scaled, not re-measured**:
`11.63 x (28.78 / 14.22) = 23.54`. Scaling by a file's own before/after
ratio on one machine keeps the shift normalisation that document's
append recipe is careful about, because the runner cancels; re-measuring
would cost the CI round-trip the recipe already says every new file over
the medium floor costs. It is a ratio and not a CI reading, and the
document now says so - if the drift gate disagrees on the next run, its
printed line over that run's shift replaces this.

### One guard corrected, one row filed

`test_the_palette_is_validated.py` reddened: the banner tints with
`var(--warn)` and named no non-colour channel (styleguide §4.3). It has
two - the element does not render at all in any other state, and it is
`role="status"` - and they are declared in `CHANNELS` rather than the
tone being dropped.

`tests/skip_reasons.py` reddened too, at 56 unresolvable against a
ceiling of 55: the new fixture coined a second `pytest.skip(NO_BROWSER)`
beside the one `served` already had. The ceiling was **not raised** -
both fixtures now depend on one `can_drive_a_page` fixture, which is
`UX-321`'s "one gate, asked in one place" applied to fixtures, and
leaves the count at 55.

`make test-tiers` is red on **three files this item did not touch**,
measured on the unmodified tree at 18.39s (listed medium), 1.36s (listed
small) and 0.74s (listed small, and therefore *not* drift - the parallel
run's report was contention). Filed as `UX-455` rather than fixed here.

### Deviation from the Required Fix

- **None.** All three bullets: the sentence is produced by driving the
  threshold, it is measured at both viewports served, it has a width
  that is not the rail's, and `UX-435`'s bound now holds in the failed
  state as well as the resting one - unchanged.
- The Acceptance Test's `bga snapshot -- bst build all.bst` was not run:
  `bst` is not installed in this environment, and the fixture the
  command exists to produce is committed as
  `tests/fixtures/with_timeline`, which is what every figure above was
  measured on. The forcing and the measurement are the parts of that
  test that carry the claim, and both were done.

### The suite

```console
$ make lint
All checks passed!

$ make test
5477 passed, 28 skipped, 1 warning in 282.77s (0:04:42)
```
