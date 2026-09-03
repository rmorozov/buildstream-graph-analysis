# UX-597: three release rows and no tag

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-251 (a release is a contract state), UX-581 | **Serves:** anyone trying to check out a release this repository claims to have made | **Topic:** docs

## Motivation

Direction 10's item 5. Measured in round 83:

```text
CHANGELOG.md   three release rows
git tag | wc -l   0
```

`release-guide.md` step 8 cuts the tag, and it has never been
executed. Nothing in the tree reads a tag either, so the omission is
invisible to every guard.

## Required Fix

Either the three tags are cut against the commits their rows name, or
step 8 is retired and the release guide says what stands in for a tag
— and whichever it is, a guard reads it, so the next release cannot
leave the same gap.

## Out of Scope

- Re-arguing what a release is (`UX-251`) — declined: this is the step, not the definition.

## Acceptance Test

Mutation: add a fourth release row with no tag — red naming the row.
