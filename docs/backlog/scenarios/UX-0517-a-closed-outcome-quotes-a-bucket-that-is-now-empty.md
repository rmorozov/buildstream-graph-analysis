# UX-517: a closed Outcome quotes a bucket that is now empty

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** `UX-507` (which emptied it), `UX-132` (the rule) | **Found by:** review 11, question 3 | **Serves:** the round that reads `UX-501` to learn what the derivation does and takes its 223 as current | **Topic:** docs

## Motivation

`UX-501`'s Outcome states the bucket as a fact about the tree:

```text
docs/backlog/scenarios/UX-0501-the-index-is-derived-not-merged.md:89
  ... else `unclassified`. `closed.md` has no Topic column and **223
  of the 489** closed rows predate the header, so no topic can be
  derived for them

:122  ... the derivation reads the task file's header instead and says
  `unclassified` where there is none.
```

`UX-507` classified all of them the same day this review ran. The
derived table now has no `unclassified` line and the bucket holds zero
rows. Both figures were true when written and are read as current — the
shape `UX-132` exists to annotate.

The mutation table at :106 is **not** affected: `N5` describes dropping
the `unclassified` row from `index_header()`, which still discriminates
(`UX-507` re-ran it).

## Required Fix

Annotate both sentences the way `UX-132` prescribes — dated, naming
`UX-507`, without rewriting what the round measured. `UX-501`'s figures
were right about its own tree and stay on the record.

## Out of Scope

- `TOPIC_UNKNOWN` itself, which `UX-507` decided to keep and guarded.
- Any other Outcome. `git grep -n '223 ' -- docs` returns one other hit
  and it is a task id (`UX-223`), not a figure.

## Acceptance Test

`git grep -n 'unclassified' docs/backlog/scenarios/UX-0501-*.md` shows
every remaining mention either annotated or describing the mechanism
rather than the tree's state.

## Outcome

_Not started._
