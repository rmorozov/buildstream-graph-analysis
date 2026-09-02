# UX-519: the snapshot's tail goes quiet in the one phase that has no line

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-183` (the progress module), `UX-518` (batch first) | **Found by:** round 77, field report — *"take considerable time on big projects... at least show progress?"* | **Serves:** the user watching a capture that has stopped saying anything | **Topic:** capture

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

## Outcome

_Not started._
