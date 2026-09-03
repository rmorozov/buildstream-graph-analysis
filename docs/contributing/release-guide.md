# Release guide

A release here records a **contract state**, not a date. The argument
is [Direction 10](../design/directions.md); this is the procedure.

If you are looking for what changed between two versions, that is
[`CHANGELOG.md`](../../CHANGELOG.md), not this file.

## What a release is for

`bga` reads its own past output as input — `@last`/`@prev`, the
baseline set, `cache-trend`, `store-aggregate` all open artifacts
written by whatever `bga` was installed at the time. Two questions
follow, and they have different answers:

| question | answered by |
|---|---|
| can my parser read this document? | the **contract version** (`analyze/v1`) |
| which build produced this artifact? | the **package version**, in the producer stamp (`UX-249`) |
| which contract states shipped together? | the **release row** in `CHANGELOG.md` |

The package version is *provenance*. It is never the compatibility
signal: it is a lossy summary of twelve independent contracts, and
comparing it would refuse across upgrades that moved nothing. What a
reader compares is the contract set — that is `UX-250`'s job.

## When to cut one

Two conditions, both measured, neither a date:

1. **A contract moved** — a schema version bumped, a subcommand or flag
   added, renamed or removed. A release with an identical contract
   state to the last one is a patch release and only worth cutting if
   something else makes it worth installing.
2. **A review row exists** at or after the previous release's
   closed-row marker, in
   [`../audits/architecture-review.md`](../audits/architecture-review.md).

Condition 2 is the whole documentation half, and it is deliberately a
*reference* rather than a second checklist. `UX-241` already owns the
review cadence; a release that ran its own doc sweep would be a second
mechanism racing the first for one job, and two hand-maintained copies
of one fact drifting apart is the single most-repeated defect in this
repository's history. **A release consumes the review. It does not
duplicate it.**

## The version is derived, not chosen

Compare the contract state recorded on the previous release row with
the state now:

| what changed | kind | pre-1.0 |
|---|---|---|
| a contract's version bumped, or a command or flag removed or renamed | `breaking` | MINOR |
| a new contract, command or flag, and nothing removed | `extending` | MINOR |
| neither | `patch` | PATCH |

Pre-1.0 both `breaking` and `extending` move MINOR, which is why the
row records the **kind** as well as the number: `0.2.0 → 0.3.0` cannot
say which it was while the major is pinned at 0, and a consumer needs
to know.

`tests/unit/test_a_release_records_a_contract_state.py` derives the
kind from the two rows' recorded states and fails if the version
increment disagrees. A version somebody picked by feel is a number with
no meaning, and this repository has spent thirty rounds refusing those.

## Cutting one

1. **Confirm the review.** `docs/audits/architecture-review.md` has a
   row at or after the previous release's closed-row marker. If it does
   not, run a review first — that is a different session (`§6a`).
2. **Record the state.** The contract set is `bga.contracts.ids()`; the
   command set is what `bga --help` lists. Both go in the release
   section's fenced `state` block, which is what the derivation reads.
3. **Freeze the row you are superseding.** The previous release's
   state block gains a `digest:` line as its first line, and stops
   being editable without the guard saying so (`UX-550`). Only the
   newest row is checked against the tree; every row below it is
   checked against its own digest, because that clause was satisfiable
   by rewriting the last row and for five rounds that was the cheaper
   path — `0.3.0` carried five contracts that did not exist on its
   date. Print the digest with:

   ```bash
   python3 -c "import sys; sys.path.insert(0, 'tests/unit'); \
     from test_a_release_records_a_contract_state import _states, state_digest; \
     print(state_digest(_states()['0.3.0']))"
   ```

4. **Derive the version** from the table above and bump
   `bga/__init__.py` and `pyproject.toml` together — the guard checks
   they agree with the newest release row.
5. **Write the head**: what this release is about in a paragraph, the
   contract delta in a sentence, and the upgrade note when there is
   one. This is the only part that is written rather than derived, and
   it is the part worth reading.
6. **Generate the body**: `bga release-notes <from> <to>` emits the
   closed rows between two markers, grouped by topic. Do not hand-write
   it — the narrative already exists in `closed.md` and a third copy
   would drift (`UX-252`).
7. **Carry the review's open findings.** Any finding the review filed
   that is still open is named in the head, so "we knew" is on the
   record rather than in someone's memory.
8. **Tag** `v<version>` on the release commit.

## What a release does not do

- **It does not fix documentation staleness.** `UX-241`'s review does;
  the release only refuses to proceed without one. Claiming otherwise
  would be the second-trigger mistake wearing a different hat.
- **It does not gate on a date.** There are no external consumers yet
  and nothing to deploy. A monthly release would be ceremony generating
  no information.
- **It does not publish.** Distribution is a separate decision; this is
  about the tool being able to say what it is.
