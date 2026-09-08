# UX-795: the focus guard measures after a fixed sleep, and one runner was slower

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-638 (the guard), UX-691 (the flake ledger this should reach) | **Found by:** round 109, on PR #215's head 8b4012ee | **Serves:** the branch that goes red on one of four matrix runners for a page it never touched | **Topic:** guards | **Area:** bga-viewer | **Shape:** bounded

## Motivation

```console
$ # CI run 34211863206, test (3.10), head 8b4012ee
FAILED tests/unit/test_focus_keeps_the_reading_position.py::TestTheReaderComesBackToWhereTheyWere::test_the_table_is_back_on_the_same_screen
AssertionError: the table moved 1022px within the viewport, 300 -> -722
$ # the same commit: test (3.9), (3.11), (3.12) green; here, three runs:
1 passed in 6.18s / 2.28s / 1.90s
$ git diff --stat 0dc755f4 8b4012ee -- bga/viewer/ tests/unit/test_focus_keeps_the_reading_position.py
(empty)
$ sed -n 122p tests/unit/test_focus_keeps_the_reading_position.py
    time.sleep(0.3)
```

The `two_presses` fixture presses twice, sleeps 0.3 s and reads the
table's top. On one runner the page had not settled: the restore
landed 1022 px off, above the viewport, and the guard read a
displacement the viewer never made. `UX-418`'s rule — seconds are never
guarded across machines — applies to a wait as much as to a duration.

## Required Fix

In `tests/unit/test_focus_keeps_the_reading_position.py`, replace the
fixed sleep with a settle: poll `scrollY` and the table's top until two
consecutive animation frames agree (or a bounded 2 s elapses, then
measure anyway and say so in the message). The clauses keep their
tolerances.

## Out of Scope

- The viewer's restoration itself — three runners and this machine
  restore within 300 px; `UX-638` closed that.

## Acceptance Test

The fixture's settle is exercised by a page whose layout is delayed
(a `setTimeout` reflow injected before the second press): the guard
waits and passes; with the fixed sleep restored, the same page reds.

## Outcome

**The gap measured.** `_TWO_PRESSES`'s final read fired 60ms after the
second press, fixed, then read `window.scrollY` and `deep`'s top
straight into `endY`/`endTop`. Replaced with `settleReading`: polls
`(scrollY, top)` on `requestAnimationFrame`, resolves once two
consecutive frames agree or 2000ms elapse, and reports `timedOut` for
the assertion messages to name.

**The close measured** (`_delayed_layout_script`, a page with a spacer
armed on the second press's own click listener, landing and shrinking
away over 500ms - built from `_TWO_PRESSES`'s own source, not a copy):

```console
$ python3 -m pytest tests/unit/test_focus_keeps_the_reading_position.py -k TestTheSettleWaitsOutADelayedReflow -v
test_the_settled_read_passes PASSED
test_the_fixed_sleep_reds PASSED
$ # the raw numbers behind both:
settled: moved=0px, viewport=900, -722 -> -722 -> PASS
fixed sleep restored: moved=2716px, viewport=900, -722 -> 1994 -> RED
$ # the file, three times:
11 passed in 5.62s / 11 passed in 6.39s / 11 passed in 5.66s
```

**The mutation table.**

| mutation | reddened | count |
|---|---|---|
| `agree = prev !== null && ... ` -> `agree = true` (settle resolves on the first frame, like the old fixed wait) | `test_the_settled_read_passes` | 1 failed, 10 passed |
| `if (presses !== 2) return;` -> `return;` first (reflow never arms) | `test_the_fixed_sleep_reds` | 1 failed, 1 passed (class only) |

Both reverted from the pre-mutation copy in the scratchpad, not
`git checkout --`; the file returned to 11 passed after each.

`make test-touching`: 32 files, 1259 passed, 3 skipped. `make lint`:
clean against the baseline. One false positive found and fixed along
the way: `document.createElement` inside the injected-reflow JS
string tripped `test_the_dom_shim_is_one_instrument.py`'s textual
census (it reads any file naming `createElement` as a second hand-built
DOM shim); switched to `insertAdjacentHTML`, the pattern `tests/pages.py`
already documents for this exact false positive.
