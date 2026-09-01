# UX-493: a bound moved and the task file that presents it as current was not annotated

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** `UX-469` moved the figure; `UX-132` is the rule | **Found by:** architecture review 10 | **Serves:** the round that reads `UX-479`'s Outcome for the export bound and gets a number the tree has not had since the same day | **Topic:** docs

## Motivation

Fixing guide §3.6: a fix annotates the task file whose figure it
invalidated, in the same commit. Round 73 broke it inside its own
round.

`UX-0479`'s Outcome, closed earlier in round 73:

```text
Not one byte of page. `macro_micro`'s bound moves 450,000 → 458,000
with that table pasted above it; golden's 406,000 stands.
```

`UX-0469`, closed later the same round:

```text
`golden`'s bound moved 406,000 → 411,000 with the ...
```

and the tree:

```console
$ sed -n '664,665p' tests/unit/test_the_report_you_can_attach.py
    # 411,000 leaves 3,735 B.
    ("golden", GOLDEN, 411_000),                       #  407,265 B
```

So `UX-479`'s file asserts, as a settled outcome, a bound the tree
stopped carrying hours later, with nothing beside it to say so. The
sentence's own subject is stale recorded figures, which is what makes
it worth a row rather than a quiet edit.

`git grep 406,000 docs/backlog/scenarios` is the check §3.6 names, and
it would have found this. It was not run.

## Required Fix

- `UX-0479`'s Outcome carries a §3.6 annotation naming `UX-469` and
  the value the tree has.
- The same `git grep` is run for the round's other moved figures —
  the census counts and `macro_micro`'s 458,000 — and each is either
  annotated or recorded as checked and clean.
- Whether the §3.6 check can be mechanical at all is the question
  worth answering while here: `dev_close_task.py` already edits four
  places at close time and knows the item number.

## Out of Scope

- Rewriting `UX-479`'s measurement. It was right when it was made;
  §3.6 annotates, it does not revise.
- The bound itself, which `UX-469` moved with the page/data split
  pasted and is not in dispute.
- A general figure guard over every document, which is `UX-132`'s own
  scope and was declined there for good reasons.

## Acceptance Test

```bash
git grep -n "406,000" docs/backlog/scenarios
```

returning only annotated occurrences, with the annotation naming
`UX-469` and 411,000.

## Outcome

_Not started._
