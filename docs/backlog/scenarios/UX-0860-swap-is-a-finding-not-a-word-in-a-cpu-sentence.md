# UX-860: swap is a finding, not a word in a CPU sentence

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-676 | **Found by:** round 120, the user (a 16-core, 32 GB host, `--builders 16 --jobserver auto`) | **Serves:** R5 (the build swapped from here to here, and these elements were running) | **Topic:** analysis | **Area:** bga | **Shape:** judgement

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

## Outcome

**Gap measured.** `_row()` computed `window["swapped_out"]` and dropped
it; `_INTERVAL_COLUMNS` had no column; `findings.py` had no finding
reading `overcommitted_intervals` at all - confirmed by grep before the
change.

**Close measured**, `tests/unit/test_the_cores_were_or_were_not_binding.py -q`:
`25 passed in 0.42s` (one window, no-swap, many-windows span cases). The
guard is `TestTheRulesAreWhatTheyClaim` (envelope tests, real
`envelope.compute`, the actual guard the task names since
`test_memory_envelope.py` is `UX-104`'s unrelated finding) plus the new
`TestSwapIsAFinding` class. Wider sweep of every guard the surfaces
touch (`test_the_documents_keep_up_with_the_contracts.py`,
`test_why_bga_believes_what_it_believes.py`,
`test_every_finding_reaches_a_fixture.py`,
`test_docs_links_and_commands.py`, `test_ci_builds_a_generated_project.py`,
`test_cache_effectiveness.py`, plus the 169-file `test-touching`
selection run in four batches): `397 passed, 1 skipped` /
`1450 passed, 1 skipped` combined, zero failures on the final run.

**Mutation table:**

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| `test_the_swap_column_is_declared` | drop `swapped_out` from `_INTERVAL_COLUMNS` | yes, names the missing key | 1 failed |
| `TestSwapIsAFinding.test_no_swap_is_no_finding` | drop the `if not rows: return []` guard | yes, `min()` on an empty sequence | 1 failed |

Both reverted from the scratchpad's copy (`falsify` step 4) and
confirmed green after.

**No-swap census gap.** The only committed capture with a CPU series
(`tests/fixtures/host_cpu`) never swaps, so `swap-observed` cannot be
reached by a clone; declared in `tools/dev_finding_coverage.UNREACHABLE`
with a reason, per the existing `build-failed`/`failed-task-time`
pattern.

**Deviation.** `docs/spec/specification.md` §32.5 lists top-level
published *documents*, not per-column contract rows for
`overcommitted_intervals` - so nothing there names an interval column
to extend, and it is unedited (confirmed by reading 1639-1690 and
1607-1639). Also touched, not in the task's declared Surfaces:
`bga/provenance.py` (`_CLAIMS['swap-observed']`, required by
`test_why_bga_believes_what_it_believes.py`'s exhaustiveness guard) and
`tests/unit/test_ci_builds_a_generated_project.py` (its
`UNREACHABLE`-set assertion needed the third id).

The schema prose ships in every export, whether or not a run's host
series ever swaps: measured either side in one worktree (`UX-667`'s
method, `tools/bga_view.py`'s `export()` against the committed
fixtures at `ede1ce6f` and at this commit) - `golden` 468,388 ->
468,809 (+421 B, bound 474,000 holds); `macro_micro` 527,889 ->
528,230 (+341 B, bound 528,000 -> 529,000, `test_the_report_you_can_attach.py`
raised); `PAGE_BUDGET_B`'s page half unmoved at 324,864 B on both
(no viewer/source change).

Deviation (merge): the verifier held once - the macro_micro export ran
230 B over its bound, the schema prose shipping in every export - and
the track measured both fixtures either side and raised the one bound;
at merge the four rows that moved the same bound landed together at
533,000, and the guide's key count re-derived to 295 with `UX-861`'s.
`docs/spec/specification.md` Part 32 carries no per-column row for
the intervals, so it stayed untouched; `swap-observed` is UNREACHABLE
in the coverage census because no committed capture swaps.
