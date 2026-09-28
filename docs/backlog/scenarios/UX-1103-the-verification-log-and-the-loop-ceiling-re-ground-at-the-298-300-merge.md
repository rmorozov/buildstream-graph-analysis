# UX-1103: the verification log and the loop ceiling re-ground at the #298/#300 merge

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1064, UX-1073, UX-1101 | **Found by:** round 150 | **Serves:** whoever reads `architecture.md`'s Verification Log or the selector ceiling next | **Topic:** contracts | **Area:** bga | **Shape:** mechanical

## Motivation

Merging `origin/main` (#298, eaaeda85) into round 150 reddened two
guards neither side could see alone. `UX-1064`'s `bga bundle --resolve`
row (20ba0c64) is not reachable from `f813b4b`, the commit the
`UX-1101` entry credits, so the Verification Log read stale. And each
side raised the touching selector's max 172 -> 173 on its own test
naming `bga.cli`; merged, the selection reads p90 61, max 174 against
a 38/60/173 ceiling. Third, a semantic seam: the anonymized export
refuses a capture-layout row with no treatment, and `UX-1078`'s
`tail.json` had none: "BundleError: 1 capture-layout row with no
anonymized treatment: tail.json", 45 failures and 8 errors over eight
anonymized-bundle files. A call's `verb` is its argv joined, so it can
name an element (`bst artifact list-contents app.bst`).

## Required Fix

`docs/design/architecture.md`'s Verification Log gains one entry
credited to `UX-1103`, re-grounded at this merge. The selector
`CEILING` in `tests/unit/test_the_loop_stays_fast.py` takes the +1 the
session allotted: p90 61, max 174. `tail.json` is `transform`
(`bga/disclosure.py`) under a `tail/v1` policy: timings, bytes and
`exit` class C, phase names class B on a `tail_phase` vocabulary that
refuses an unknown name, and `phases[].calls[].verb` class F, rebuilt
by 6.2's command grammar (`bga/bundle.py` `_COMMAND_PATHS`) as
`plane2/v3`'s command strings are. `anonymized-bundle.md` stage 4
gains the row.

## Out of Scope

Trimming the test files that name `bga.cli`; either side's own Outcome.

## Acceptance Test

`tests/unit/test_the_verification_log_is_true.py` and
`tests/unit/test_the_loop_stays_fast.py` pass on the merged tree.
`tests/unit/test_the_tail_travels_anonymized.py`: a tail whose call
names a fixture uid exports with the uid absent and its timings kept,
and every literal `progress.timed` name under `bga/` and `tools/` is on
the vocabulary.

## Outcome

Gap measured: `test_nothing_landed_after_the_commit_the_entry_credits`
failed, "credits UX-1101 (f813b4b); 1 substantive commit(s) have
changed architecture.md since: 20ba0c64". `test_the_selection_is_a_fraction_of_the_suite`
failed, "{'median': 38, 'p90': 61, 'max': 174} against {'median': 38,
'p90': 60, 'max': 173}, over a suite of 677 files".

Close measured: one entry added, dated 2026-09-28, credited to
`UX-1103`: `analyze/v6` **63 top-level properties** (`bga analyze
--schema`), **26 emitted ids** (`bga.contracts.ids()`); unchanged by
PR #298, which added no contract. `CEILING` = median 38, p90 61, max 174,
the merged reading over 677 files. Both files pass. The eight
anonymized-bundle files: 130 passed. The new guard: 3 passed.
`dev_sizes.py --adopt --force`: `bga/disclosure.py` file_lines
546 -> 565, `bga/bundle.py` 925 -> 926, the policy's own rows.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| `CEILING` max 174 -> 173 | `test_the_loop_stays_fast.py` | 1 failed / 46 |
| the new entry's heading credits `UX-1101` again | `test_the_verification_log_is_true.py` | 1 failed / 31 |
| `tail.json` dropped from `TREATMENTS` | `test_the_tail_travels_anonymized.py` | 2 failed / 3 |
| the `tail/v1` verb row dropped from `_COMMAND_PATHS` | same | 1 failed / 3 |
| the verb declared class C, kept verbatim | same (residue scan: `lib0.bst`) | 1 failed / 3 |
| `raw log gzip` dropped from the vocabulary | same | 1 failed / 3 |

Deviation: none from the Required Fix.
