# UX-860: swap is a finding, not a word in a CPU sentence

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-676 | **Found by:** round 120, the user (a 16-core, 32 GB host, `--builders 16 --jobserver auto`) | **Serves:** R5 (the build swapped from here to here, and these elements were running) | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

The capture samples `pswpin`/`pswpout` every tick into
`host-samples.jsonl` and `bga/utilisation/envelope.py` folds a window's
`swapped_out` into its `overcommitted` verdict - then `_row()` drops the
count, `_INTERVAL_COLUMNS` has no column for it and `bga/findings.py`
has no finding reading the envelope at all. A user whose build hit swap
found nothing on the page: the one sentence that knows says
"overcommitted - load above N cores or pages written to swap", a CPU
frame with swap as an aside.

## Required Fix

`bga/utilisation/envelope.py` publishes `swapped_out` (pages) on each
`overcommitted_intervals` row and `bga/schemas.py` adds the column
(additive, no bump); `bga/findings.py` gains `swap-observed`, present
when any row's `swapped_out` is over zero, naming the windows' span and
the elements building in them; the text report and the machine chapter
carry it; `docs/spec/specification.md` §32.5's contract row names the
column.

## Decomposition

Input classes: no swap, one window, many windows; the journey it
extends is R5's overcommitted machine, now with the swap it saw.

## Out of Scope

Per-element memory attribution during the swap window - `UX-682`'s
shape; PSI memory, which reaches only the jobserver ledger (`UX-850`).

## Acceptance Test

`tests/unit/test_memory_envelope.py` gains a case: a host-samples
fixture with `pswpout` rising in one window - the row carries the count
and `swap-observed` names the window and its elements; mutation: drop
the column - red.
