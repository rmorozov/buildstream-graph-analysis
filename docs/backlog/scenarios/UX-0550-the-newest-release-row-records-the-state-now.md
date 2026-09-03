# UX-550: the newest release row records the state *now*, not the one it shipped

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-252 (the generated release body) | **Serves:** anyone answering "what changed between the bga I installed and the one I have" | **Topic:** contracts

## Motivation

Architecture review 12. `CHANGELOG.md` opens with *"What changed
between the `bga` you installed and the one you have now"* and *"A
release here records a **contract state** … as they stood"*. It cannot
answer either, because the newest row is edited rather than succeeded:

```text
release 0.3.0   dated 2026-08-27, marker 332 closed rows
  block first written 2026-08-28 (bc15935):  18 contracts, 31 commands
  block today:                               23 contracts, 32 commands
  retro-fitted into it:  analyze/v5  bundle-manifest/v1  capture-layout/v1
                         host-samples/v1  plane2/v3  +  the `bundle` command
closed rows today                            537   (0.3.0's marker: 332)
```

None of those five contracts and no `bga bundle` existed on 2026-08-27.
`analyze/v4 → v5` is a **breaking** move (three keys removed, `UX-535`)
and it now sits inside a row whose `kind` cell was decided for a
different reason, 205 closed rows earlier.

**The mechanism that produces it.**
`test_a_release_records_a_contract_state.py::test_the_recorded_state_is
_the_real_one_for_the_newest_release` asserts the newest row's set
equals `contracts.ids()` *today*. That clause is satisfiable two ways —
cut a release, or rewrite the last one — and for five rounds the second
has been the cheaper. `git log -L 101,103:CHANGELOG.md` shows four
commits doing it (`f495e12`, `929ee8d`, `fab3307`, `3c93633`), none of
them a release.

This is the round's own recurring shape one layer up: a guard another
path already satisfies.

## Required Fix

Decide which, and make the guard hold only that one:

- **Cut 0.4.0** at the current state, leaving 0.3.0's block as it was
  written — the reading the prose already assumes; or
- **say the newest row is the working state** and give it a version
  that admits it (`0.4.0-dev`), so "as they stood" is not claimed of a
  row that moves.

Either way the guard needs a second clause: an *older* release row's
recorded state must not change once written. That is the mutation the
present one cannot see.

## Out of Scope

- The release procedure itself (`docs/contributing/release-guide.md`)
  beyond the sentence this changes.
- Re-deriving 0.2.0's block: it has not been edited since it was
  written, which is the property this item wants of every row, so it is
  the example rather than the work.

## Acceptance Test

`git log -L` over the newest release's state block shows one commit;
a mutation that edits a *superseded* release's contract list reddens.

## Outcome

**Round 81, 2026-09-03. Decision: cut 0.4.0.** The alternative
(`0.4.0-dev`) was rejected on two measurements: `bga.__version__` and
`pyproject.toml` are two of the three copies of the newest row's
number, and renaming the row would have retired `0.3.0` from the ledger
rather than correcting it. `0.3.0`'s block is restored verbatim from
`bc15935` — 18 contracts, 31 commands.

**The gap, before:**

```text
$ git log -L 101,103:CHANGELOG.md --format="%h %ad %s" --date=short -s
3c93633 2026-09-02 fix: the merge's own eleven failures, and UX-547 filed
fab3307 2026-09-02 fix(UX-535): the graph's shape is published once, analyze/v5
929ee8d 2026-08-29 fix(UX-384): a redundancy finding is bounded by its row (plane2/v3)
f495e12 2026-08-29 fix(UX-381): the capture directory is a contract, and Part 32.6 states it
bc15935 2026-08-28 Close UX-359: the mutation that survived twice was the guard's fault
```

Five commits, none a release, on a row dated 2026-08-27.

**Closed** — the newest release's state block (`CHANGELOG.md:93-94`):

```text
$ git log -L 93,94:CHANGELOG.md --format="%h %ad %s" --date=short -s
5c66a21 2026-09-03 wip(UX-550): cut 0.4.0, restore and freeze 0.3.0
```

`0.4.0` records 23 contracts and 32 commands, kind `breaking` (derived:
`analyze/v4→v5`, `plane2/v2→v3`), closed-row marker 537, review 12 at
537 ≥ 332.

**The second clause.** A superseded row carries `digest: <12 hex>` as
the first line of its state block — sha256 over `contracts:`/`commands:`
sorted. The newest row carries none: it is the one the tree answers
for, and freezing it would give that check the second satisfying path
this item was filed against. `git log -L` cannot be the guard —
`actions/checkout@v4` is depth 1, so a history-reading clause would be
vacuous in CI (`UX-213`'s defect). The digest is readable in any clone.

**Mutations verified red and reverted (4):**

| mutation | reddened | printed |
|---|---|---|
| `analyze/v5` added to 0.3.0's contract list | `test_a_superseded_releases_state_matches_its_digest` | `0.3.0: records digest 2b0a95deffe4, its state hashes to ffc4f315d104` |
| `bundle-manifest/v1` added to 0.2.0's list | same clause, naming 0.2.0 | `hashes to 61c66ff45c00` |
| 0.2.0's `digest:` line deleted | `test_a_superseded_release_is_frozen_by_a_digest` | `superseded release(s) recording no digest: ['0.2.0']` |
| a `digest:` added to 0.4.0 | `test_the_newest_release_carries_no_digest` | `release 0.4.0 is the newest row and carries a digest` |

Neither contract-list edit moves the derived `kind`, so the pre-existing
clauses stayed green through both — which is the gap this item names.

**Limit of the instrument, stated:** the digest makes an edit *fail*,
not impossible; rewriting the block and its digest together still
passes. That is a deliberate act rather than the cheapest path, which
is the whole difference this item is about.

**No guard of mine failed to discriminate here.**

**Deviation from the Required Fix:** none, plus one repair the fix
required: `docs/design/architecture.md`'s Verification Log was stale by
a day after `UX-540` touched the file (`test_the_verification_log_is_true`),
re-grounded in the same commit.

Committed with `BGA_SKIP_SELECTOR=1`: the selector's only red is
`test_the_table_status_matches_the_task_files`, the index row this track
does not own (`UX-501` gives it to the orchestrating session).

**Tier:** `make test-small` — 3,473 passed, 39 skipped, 40.39s, 5
failures, 4 of them the index rows this track does not own
(`UX-540`'s marker) and one the log above, now green. `make lint` clean.
