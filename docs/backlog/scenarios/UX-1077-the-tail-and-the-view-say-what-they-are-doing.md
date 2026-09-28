# UX-1077: the snapshot tail and bga view run minutes of work with no progress and no timing

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R1, R5 | **Topic:** cli | **Area:** tools | **Shape:** mechanical

## Motivation

After `bst` exits only three phases draw a ticker (census, artifact
contents, `bst show`). Silent, measured at the largest size tried
([the audit](../../audits/perf-snapshot-view-2026-09-28.md)):

```text
phase                       says            5,002 el / 192k proc
Plane 2 report              one line, then   20.9s
gzip of the raw log         nothing          16.0s (417 MB)
_analyze                    nothing          35.6s
write_element_slice         nothing          18.6s
_compare                    "$ bga compare"  49.3s
bga view --export           nothing          54.9s before "Wrote"
```

## Decomposition

Input classes: a TTY, a pipe, `--no-progress`; a build that failed; an interrupted tail. Journeys: `bga snapshot` and `bga view` (serve and export).

## Required Fix

In `tools/bga_snapshot.py` and `tools/bga_view.py`: Every post-build phase of `bga snapshot`, and `bga view`'s analyze,
compare and timeline steps, announce through `bga.progress` and end
with their elapsed seconds; the snapshot's last line totals the tail
(`bga's own time after the build: N s`). Non-TTY output keeps one line
per phase.

## Out of Scope

Making any phase faster (`UX-1072`..`UX-1076`).

## Acceptance Test

`tests/unit/test_the_tail_says_what_it_is_doing.py`: With `BGA_FORCE_PROGRESS=1`, a snapshot on the golden store prints
one announcement and one elapsed line per phase, and the total line;
`--no-progress` prints the total line only. Mutation: remove one
phase's announcement, and the guard reds.

## Outcome

**Gap measured:** the new guard run against the base tree (`46f21ac`,
`git archive HEAD`), second snapshot on the golden run
(`tests/fixtures/golden/mixed_task_kinds`), `BGA_FORCE_PROGRESS=1`:
`assert [] == ['Plane 2 rep...compare', ...]` - no phase of seven
printed an elapsed line and no total line was printed; piped, 2 of 7
phases announced themselves (`assert 2 == 7`); `bga view`'s export and
compare printed nothing before `Wrote` (`{'analyze', ..., 'timeline'}
<= set()`). 5 failed.

**Close measured:** one recorder, `bga.progress.timed(name, say)`:
the announcement (TTY or piped), an `  <name>: N.Ns` line (TTY or
`BGA_FORCE_PROGRESS` only), nothing under `BGA_NO_PROGRESS`, and a row
in an in-process ledger either way. Wrapped: the tracer's `Plane 2
report` and `run directory`, the snapshot's `raw log gzip`, `analyze`,
`element slice`, `compare`, `store size`; `bga view`'s `analyze`,
`compare`, `timeline`. `progress.timed_build()` times the build
subprocess alone. The snapshot's last line before UX-738's exit line:
`bga's own time after the build: N.Ns (the build: N.Ns)`.
`pytest tests/unit/test_the_tail_says_what_it_is_doing.py` -> `5 passed
in 1.10s`. `make test-touching` -> `253 file(s) selected ... 5067 passed, 75
skipped in 291.07s`.

Recorder cost, 1,202-element store (`gen-synthetic --store --seed 1
--layers 20 --width 60`), each tail step bare and inside `timed`,
median of 5 (`cost.py`, `BGA_NO_PROGRESS=1`):

```text
step          bare_median_s  timed_median_s  peak_rss_kb
analyze               1.406           1.254      104804
element slice         0.000           0.001       90468
compare               2.471           2.352      104844
store size            0.000           0.000      104844
empty timed(): 31.6 us per phase over 10000
```

31.6 us x 7 phases is 0.2 ms against a 3.6 s tail: below the noise
between the two arms.

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| `analyze`'s `timed` in the snapshot replaced by `if True:` | `test_each_phase_is_announced_and_timed`, `test_a_pipe_keeps_one_line_per_phase` | 2 failed, 3 passed |
| the gzip phase's `timed` removed | the same two | 2 failed, 3 passed |
| the tracer's `Plane 2 report` `timed` removed | the same two | 2 failed, 3 passed |
| `timed` announces nothing | the same two + `test_view_times_its_analyze_compare_and_timeline` | 3 failed, 2 passed |
| `timed` prints no elapsed line | `test_each_phase_is_announced_and_timed`, `test_view_times_...` | 2 failed, 3 passed |
| the elapsed line printed on a pipe and under `--no-progress` too | `test_no_progress_prints_the_total_only`, `test_a_pipe_keeps_one_line_per_phase` | 2 failed, 3 passed |
| `progress.total_line()` removed from the tail | `test_each_phase_is_announced_and_timed`, `test_no_progress_prints_the_total_only` | 2 failed, 3 passed |
| `timed_build()` taken off the `with` around `run_wrapped` | `test_the_build_wall_is_timed_around_the_build_alone` | 1 failed, 4 passed |
| `bga view`'s compare through bare `_capture` | `test_view_times_its_analyze_compare_and_timeline` | 1 failed, 4 passed |
| `bga view`'s timeline `timed` removed | `test_view_times_its_analyze_compare_and_timeline` | 1 failed, 4 passed |

Reverted from the copy: `5 passed in 1.10s`.
