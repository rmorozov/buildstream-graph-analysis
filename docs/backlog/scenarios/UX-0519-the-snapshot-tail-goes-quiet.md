# UX-519: the snapshot's tail goes quiet in the one phase that has no line

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-183` (the progress module), `UX-518` (batch first) | **Found by:** round 77, field report — *"take considerable time on big projects... at least show progress?"* | **Serves:** the user watching a capture that has stopped saying anything | **Topic:** capture | **Area:** tools

## Motivation

`UX-183` gave the long phases a moving line, and the capture's tail is
where it is missing. Every `bst`-driven phase in
`tools/bst_native_build_tracer.py` draws one except the one the field
report names:

```text
tools/bst_native_build_tracer.py:1240  progress.ticker("parsing trace", total=total_lines)
tools/bst_native_build_tracer.py:1540  progress.ticker("pairing processes", total=None)
tools/bst_native_build_tracer.py:2935  progress.ticker("census", total=len(elements))
tools/bst_show_to_graph.py:253         progress.ticker("bst show")
```

`read_artifact_contents` has none, and it runs *between* the census and
the report — so the last thing a user sees is the census finishing, and
then nothing until the report prints. `UX-518` measures what that
silence costs today: ~11 minutes on a project the size of
freedesktop-sdk's published capture.

The half the report also names is already handled and worth recording so
this row does not get re-filed: `bst show --deps all` is one invocation
with an elapsed ticker, put there by `UX-183` for exactly this reason —
*"there is nothing to count — `bst` is a subprocess and its stdout is the
payload, not a progress stream. Elapsed seconds are the honest signal."*

## Required Fix

- The phase draws a line. After `UX-518` it is one subprocess, so the
  honest signal is the one `bst show` uses — elapsed seconds, not a
  count of elements that no longer exist as separate steps. If `UX-518`
  lands as bounded chunks instead, the count is chunks completed.
- The claim this row closes on is **coverage**, not one line: no phase
  that can exceed a stated threshold is without a ticker. A guard that
  reads the module for `ticker(` calls is not that claim — it would pass
  on a ticker created and never fed.

## Out of Scope

- `UX-183`'s rules, which stand: `stdout` untouched, `stderr` only when
  it is a TTY, `BGA_NO_PROGRESS=1` absolute. A new line obeys them
  because it uses the same module, and a line that reached a piped
  stderr would be the defect `UX-183` exists to prevent.
- Making the phase faster, which is `UX-518`.

## Acceptance Test

A capture of `examples/09-fine-grained-siblings` with
`BGA_FORCE_PROGRESS=1`, its stderr captured, showing a line for the
artifact-contents phase between the census line and the report — and the
same capture with the stderr **piped**, showing the phase lines whole and
no carriage return anywhere in the bytes.

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

`read_artifact_contents` alone, forced-TTY stderr captured, `bst` 2.7.0:

```text
examples/09 (nothing built): 11 elements, 124.79s, 0 paths, 0 frames drawn
examples/06 (all cached):    11 elements,   2.79s, 8413 paths, 0 bytes drawn
```

Two minutes and three seconds of the phase the field report named, and
not one byte about either.

### After

Same two runs, same instrument:

```text
11 elements, 91.33s, 0 paths
  | artifact contents: 1/1
  | artifact contents: 1/1 retry 1/11
  ...
  | artifact contents: 1/1 retry 11/11
```

```text
$ BGA_FORCE_PROGRESS=1 bga capture report 06.rawlog --project-dir \
    examples/06-macro-micro-optimization --json >/dev/null   # cat -A
^M  parsing trace: 0^M   ^M^M  artifact contents: 1/1^M   ^M^M  census: 1/11^M
```

Piped, the same command unforced: **0 stderr bytes, 0 carriage
returns**, stdout `cmp`-identical to the forced run. 124.79s against
91.33s is `bst` startup variance on the failing path, not this change.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | a new `_read_one_by_one` planted: a loop calling `_list_contents`, no ticker | `test_it_feeds_a_ticker[bst_native_build_tracer]`, naming line 3377 — 1 failed, 6 passed |
| A2 | `loops_that_shell_out`: `loops = [...]` → `loops = []` | `test_the_detector_sees_a_phase_shaped_like_the_real_one` — 1 failed, 5 passed, and A1's clause went *green*, which is what it is for |
| A3 | `total=len(groups)` → `total=len(elements)` | `test_a_batch_per_frame`, `1/500` for `1/3` — 1 failed, 5 passed |
| A4 | the `tick.note(...)` retry line → `pass` | `test_the_retry_says_it_is_retrying` — 1 failed, 5 passed |
| A5 | `bga/progress.py` `Ticker.step`: `if not self._on:` → `if False:` | `test_nothing_reaches_a_pipe` — 1 failed, 5 passed |

Reverting the whole change reddens 4 of the 6 clauses (the reproduction).

**Dropped, did not discriminate:**
`test_the_phase_is_named_between_the_others` (the label is in the drawn
bytes) — `test_a_batch_per_frame` compares the frames verbatim, so every
mutation reddening one reddened both. **A mutation rejected, not
counted:** cutting `_spawners` to one level left all six green — the
real chain is one level (`read_artifact_contents` → `_list_contents` →
`subprocess`), so it did not touch what the guard reads.

### Deviation from the Required Fix

The Acceptance Test named a *capture* of `examples/09`, which cannot run
here — `bst show` fails at resolve, `bulk.bst [line 9 column 8]:
Specified path 'files/bulk' does not exist`. Instrument instead:
`read_artifact_contents` over `examples/09`'s elements, plus `bga
capture report --project-dir` over the committed `examples/06` capture,
the same `load_and_summarize` path. `examples/09` has nothing built, so
its figures are the **retry** path and `examples/06`'s the healthy one;
both pasted, neither standing for the other. Elapsed-seconds animation
inside a single batch was rejected: it needs `bst show`'s `Popen` poll
loop, which `UX-518`'s `subprocess.run` double does not survive and
which `UX-197` shows costs an orphan-on-Ctrl-C contract.

```text
$ make lint          ruff + pymarkdown, All checks passed!
$ make test-touching 1023 passed, 32 skipped in 147.65s (59 files)
```

Committed with `BGA_SKIP_SELECTOR=1`: `UX-522`'s hook resolves its repo
from its own path, which for a worktree agent is the **shared**
checkout, so it ran the selector on 8 files that are not this diff.
`make test-touching` above is this worktree's.
