# UX-76: the headline block ranks the same five elements three times, and one of the three has been quietly wrong since `UX-70`

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-70` (done — which introduced the regression below)

## Motivation

`Key Findings` on round 9's real capture is 21 lines, of which 13 are
three separate rankings over the same handful of elements:

```
  Where the time is: 4 element(s) are 80.3% of the 3610.5s critical path
    components/_private/cmake-stage1.bst  1569.8s (43.5% of path)
    components/openssl.bst                 672.1s (18.6% of path)
    components/doxygen.bst                 513.5s (14.2% of path)
    components/bison.bst                   144.2s ( 4.0% of path)
  Elements Most Worth Optimizing First (by what optimizing them would actually save ...):
    1. components/_private/cmake-stage1.bst (1569.8s, 43.5% of the critical path) - ...
    2. components/openssl.bst ...
    3. components/doxygen.bst ...
  Highest Criticality Elements:
    1. components/openssl.bst (100% probability of being on critical path)
    2. components/_private/cmake-stage1.bst (100% probability ...)
    3. components/_private/buildsystem-cmake.bst (100% ...) [structural: stack, ...]
```

Three headings, three orderings, largely the same names. The third is the
worst offender: on a build where the critical path is deterministic,
"100% probability of being on the critical path" is true of every element
on it and distinguishes nothing — and its third entry is a `stack` the
report itself annotates as having no work to speed up. A reader's first
glance is spent reconciling three lists instead of reading one.

## The regression `UX-70` introduced

`UX-70` changed `_heaviest_on_path` to sort by realizable saving. That
was right for "what to optimize first" — and `_format_time_concentration`
("Where the time is") consumes the same helper, so it silently changed
meaning too. Same capture, before and after:

| | `bga_ref` `1143f2b` (round 9) | `74c94e3` (now) |
|---|---|---|
| headline | 4 elements are **94.0%** of the path | 4 elements are **80.3%** of the path |
| listed | cmake-stage1, openssl, **python3 (17.7%)**, doxygen | cmake-stage1, openssl, doxygen, **bison (4.0%)** |

`components/python3.bst` is the **third largest element on the critical
path**, and the block whose entire job is to say *where the time is* now
omits it in favour of one three-and-a-half times smaller. The
concentration figure it prints is understated by 13.7 points as a result.

Both numbers are individually defensible — python3 is 17.7% of the path
and worth only 3.2% to fix, which is exactly `UX-70`'s point — but "where
the time is" is a question about duration, and it is now answered with a
different quantity than its own heading claims.

## Required Fix

1. **`_format_time_concentration` sorts by duration.** It is the "where
   is the time" block; the saving-ranked list is the block directly
   below it, and the two being ordered differently is the *content*, not
   an inconsistency to smooth over.
2. **Merge the three rankings into one table.** One row per element with
   columns for duration, share of path, and realizable saving — the
   reader compares them at a glance instead of re-reading three lists,
   and the interesting disagreement (python3: big share, small saving)
   becomes visible rather than hidden by which list it fell out of.
3. **Drop or demote "Highest Criticality Elements"** when the criticality
   probabilities are degenerate (all 100%). It earns its place on a graph
   with real schedule variance and says nothing on a deterministic
   replay; a structural `stack` must never be one of its three entries
   (`UX-34`'s rule, applied here too).
4. **Keep the block short.** The headline exists to be read first; every
   line it spends restating an ordering is a line the reader spends not
   reaching the recommendation.

## Out of Scope

- The detailed sections below the headline, which are reference material
  and are allowed to be long.
- Removing `criticality_probability` from the JSON. It is a real signal
  on a non-degenerate graph; this is about what the headline shows.

## Acceptance Test

1. On round 9's capture, "Where the time is" reports 94.0% across
   cmake-stage1, openssl, python3 and doxygen — the four largest — and
   `python3.bst` is present.
2. The ranked recommendation still leads with cmake-stage1, openssl,
   doxygen by realizable saving, unchanged from `UX-70`.
3. `Key Findings` names each element at most once.
4. No structural element appears in any headline ranking.

## Fix Implemented

The three rankings became one table, and the two orderings that were
being conflated are now separate functions over the same population:
`_path_elements_by_duration` (where the time is) and `_heaviest_on_path`
(what a fix is worth). Round 9's capture, `Key Findings`, before and
after:

```
before (13 lines, 3 rankings)              after (8 lines, 1 table)
  Where the time is: 4 elements, 80.3%       Where the time is: 4 element(s) are 94.0% of the
    cmake-stage1  1569.8s (43.5%)            3610.5s critical path - this build is chain-bound,
    openssl        672.1s (18.6%)            not scheduler-bound
    doxygen        513.5s (14.2%)              cmake-stage1  1569.8s (43.5% of path)  -> fixing it saves 1569.8s (43.4%)
    bison          144.2s ( 4.0%)              openssl        672.1s (18.6% of path)  -> fixing it saves  522.5s (14.5%)
  Elements Most Worth Optimizing First:        python3        639.8s (17.7% of path)  -> fixing it saves  114.1s ( 3.2%)
    1. cmake-stage1 ... would save 1569.8s     doxygen        513.5s (14.2% of path)  -> fixing it saves  513.5s (14.2%)
    2. openssl ... would save 522.5s           -> these elements must get faster, or come off the chain
    3. doxygen ... would save 513.5s           -> work them in this order (by what a fix is worth,
    Note: 77% of elements have zero slack         which is not the order above): cmake-stage1, openssl, doxygen
  Highest Criticality Elements:                Note: 77% of elements have zero slack - this graph is a
    1. openssl (100% probability)                 mesh of near-equal chains ...
    2. cmake-stage1 (100% probability)
    3. buildsystem-cmake (100%) [structural]
```

`python3.bst` is back where it belongs — third by duration — and the row
that restores it is also the row that shows why it is *not* third by
value (114.1s, 3.2%). That disagreement was the most useful thing in the
report and it was previously invisible, hidden by which of two lists an
element happened to fall out of.

Three further things fell out of the merge:

- **The concentration figure is right again**: 94.0%, not 80.3%.
- **The chain-bound verdict moved onto the table's own heading.** It used
  to live on the second ranking's heading, which meant merging would have
  deleted it on any build that is *also* execution-bound — the ordinary
  case on a real capture, and the one this was measured on.
- **The degenerate criticality list is dropped.** On a deterministic
  replay every element on the path scores 1.0, so a ranking of them ranks
  nothing; it also held `buildsystem-cmake.bst`, a `stack`, in its third
  slot. Structural elements are now excluded from it outright (`UX-34`'s
  rule), and the list is skipped entirely when every entry scores 1.0. It
  still renders, unchanged, on a graph with real schedule variance.

Tests: 3 new in `tests/unit/test_headline_points_at_the_time.py` pinning
duration ordering, the fix-order line, and each element being named once;
1 new in `tests/unit/test_report_key_findings.py` for the dropped
degenerate list, with the existing zero-probability guarantee re-pointed
at a non-degenerate fixture so it still tests the filter.

## Verification Log

Filed 2026-08-18 (round 10 preparation). The two headline variants are
the published `analyze.txt` of the capture `5eda28a` (produced at
`bga_ref` `1143f2b`) and `bga analyze capture/run` re-run locally at
`74c94e3` on that same `run/` directory.
