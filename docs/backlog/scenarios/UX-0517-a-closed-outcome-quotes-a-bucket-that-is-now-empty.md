# UX-517: a closed Outcome quotes a bucket that is now empty

**Priority:** Low | **Status:** 🟢 Fixed & Verified | **Depends on:** `UX-507` (which emptied it), `UX-132` (the rule) | **Found by:** review 11, question 3 | **Serves:** the round that reads `UX-501` to learn what the derivation does and takes its 223 as current | **Topic:** docs

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

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

The bucket the two sentences state as a fact about the tree, read from
the derivation itself:

```text
$ python3 -c "…tools/dev_close_task.py… Counter(topics().values())"
rows 534
unclassified 0
closed rows 512
closed with no Topic header derivable: 0
```

Zero, over 512 closed rows. `UX-501:89` says **223 of the 489** predate
the header and `UX-501:122` says the derivation "says `unclassified`
where there is none" — both true of round 75's tree, both read as
current.

### After

Both sentences carry a dated clause naming `UX-507`; every original
word and the figure itself are unchanged.

```text
$ git grep -n 'unclassified' docs/backlog/scenarios/UX-0501-*.md
UX-0501-…md:89:else `unclassified`. `closed.md` has no Topic column and **223 of the
UX-0501-…md:106:| N5 | `index_header()` drops the `unclassified` row | 2 clauses |
UX-0501-…md:122:instead and says `unclassified` where there is none — **no longer true
```

:89's paragraph now ends "Filed as `UX-507`, **which classified all 223
on 2026-08-31: the bucket has held 0 rows since**"; :122 carries "**no
longer true since `UX-507` (2026-08-31)**"; :106 is `N5`, the mechanism,
which the filing exempts.

### Mutations verified red and reverted (0)

None, and the absence is the finding: this item adds no guard. §3.6 is
"judgment-shaped and cannot be a hard test" (`UX-132`), and a guard
grepping an Outcome for its annotation is the shape `falsify` warns
about — it matches the sentence arguing for the annotation. `UX-507`'s
guard holds the mechanism already.

The line budget did bind: `UX-501`'s Outcome was **79 of 80** lines, so
the blockquote form (`UX-107`, `UX-118`) did not fit at 3 lines each.

```text
$ PYTHONPATH=. python3 -c "…_outcome_lines(UX-0501)"
80
$ make lint
All checks passed!
$ make test-touching
No test file names any of 2 changed file(s)  <- both are task files
$ make test-small
4 failed, 3295 passed, 38 skipped in 80.65s
```

The four are one cause and it is not this diff: `--check` reports
`UX-516`/`UX-517` as 🟢 files under 🔴 rows, and the row move is the
orchestrator's by rule.

`BGA_SKIP_SELECTOR=1` on this commit. `UX-522`'s hook resolves its
repo from its own path, so from a worktree it runs the selector on the
**shared checkout** — it reported 8 changed files and 404 test files
where this tree has 2 and 0. The selector on this tree is green.

### Deviation from the Required Fix

The annotation is an inline dated clause, not the blockquote `UX-107`
and `UX-118` used: the Outcome sat at 79 of the 80-line cap and two
blockquotes cost 6. One paragraph of `UX-501` was re-wrapped at 74
columns to free the line, word-for-word identical — asserted in the
edit script, not by eye.

Out of scope and left alone, for a row of its own:
`tools/dev_close_task.py:270` and `:539` carry the same 223 as the
rationale for `TOPIC_UNKNOWN`, and `docs/audits/architecture-review.md:114`
is the review that found this.
