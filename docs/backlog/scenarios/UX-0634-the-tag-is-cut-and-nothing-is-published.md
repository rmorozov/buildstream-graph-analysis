# UX-634: the tag is cut and nothing is published

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-597 (which made step 8 real), UX-252 (do not write a third copy) | **Found by:** round 86, proposed by the repository's owner | **Serves:** anyone reading this project's releases on GitHub rather than in the tree | **Topic:** docs

## Motivation

Step 8 of the release guide is one line — *"Tag `v<version>` on the
release commit"* — and stops there. A reader who arrives at the
repository's releases page sees a bare tag: no title, no description,
nothing that says what the release is for.

The text already exists. Step 5 writes *"what this release is about in
a paragraph, the contract delta in a sentence, and the upgrade note
when there is one"*, and that paragraph is exactly what a release
description should carry:

```text
$ sed -n '/^## 0.4.0/,/^\*\*Contract delta/p' CHANGELOG.md
## 0.4.0 — a capture you can carry (2026-09-03)

Named for what it makes possible: a capture leaves the machine that
took it. …
```

So this is not a writing task. It is a step that stops one move short
of publishing what it already produced, and `UX-252`'s rule applies:
the description is **cut from** the CHANGELOG head, never written a
second time, or the two drift the way the narrative and `closed.md`
would have.

## Required Fix

Step 8 covers the whole publish: the tag, and a GitHub release whose
description is the CHANGELOG section's head — cut, not rewritten. A
guard reads the guide for that step and reads `CHANGELOG.md` for the
thing being cut, so a release section that opens with a table instead
of a paragraph reddens before the release is made rather than after.

Whether the cut is manual or a command is the implementer's call,
argued: a `bga release-notes` already exists for the body, and a second
tool for four lines of head may not earn itself.

## Out of Scope

- Publishing the existing three releases retrospectively — declined
  here: `v0.2.0` is `UX-633`'s open question and the answer changes
  what its description would say.
- The body's generation (`UX-252`, step 6) — right, and unchanged.

## Acceptance Test

A release section whose head is a table rather than a paragraph,
reddening the guard that reads it.

## Outcome (round 86, 2026-09-04) — 🟢 Done

**Premise held.** Step 8 was one line and nothing in the tree read a
release description:

```text
$ git show d8dfc46:docs/contributing/release-guide.md | grep -n '^8\.'
107:8. **Tag** `v<version>` on the release commit.

$ git grep -l 'GitHub release' d8dfc46 -- tests/ docs/
(nothing)
```

### After

Step 8 now covers the publish and names the cut. The head is defined by
a boundary that already exists — the section's title down to its
`**Contract delta:**` line — so no new marker was added to `CHANGELOG.md`
for a guard to read.

`TestEveryReleaseCarriesItsOwnDescription`, five clauses:

```text
version   head    first prose line
0.4.0     17 ln   Named for what it makes possible: a capture leaves …
0.3.0     22 ln   Named for the rule it finally finishes. `UX-190` sai…
0.2.0     13 ln   The first recorded release, and it is named for what…
MAX_HEAD_LINES = 24
```

**32 passed** in `test_a_release_records_a_contract_state.py`.

The bound is 24 against a measured worst case of 22 — two lines of
headroom, deliberately tight. A release description that runs past a
screen is the failure this row exists to catch, and a bound with room
for a fourth paragraph would not catch it.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| N1 | guide drops "cut from `CHANGELOG.md`" | the guide clause alone |
| N2 | guide never says "GitHub release" | the guide clause alone |
| N3 | `0.4.0`'s head opens with a table row | the prose clause alone |
| N4 | `_release_heads` collects nothing (`collecting` left `False` at each head) | `…has_a_head_to_cut`, 1 failed / 4 passed |

N4 is recorded with its false start: the first `sed` did not apply —
its indentation did not match the line — and the run came back green,
which reads exactly like a guard that does not discriminate. Re-applied
with the right indentation it reddened. **A mutation that appears not
to land is two hypotheses, not one**; this round it was the cheaper one,
and the round before it was not.

### Deviation from the Required Fix

The Required Fix left "manual cut or a command" to the implementer,
argued. **Manual.** `bga release-notes` earns itself because the body
is derived from the backlog and would be transcription otherwise; the
head is three paragraphs a human already wrote in step 5, and a command
to copy them would be a second place for the boundary to be defined —
the guard reads the same boundary the guide states, and one definition
is the point of `UX-252`.
