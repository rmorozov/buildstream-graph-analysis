# UX-769: the count guard matches a task id, not a count

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Serves:** the branch whose CI reds on a figure nobody wrote | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-503` and `UX-471` removed two counts from the agent documents
because both moved without anyone deciding anything. Their guards check
the count is gone by substring:

```python
rows = len(json.loads((REPO / "tests/ci_reference.json").read_text())["files"])
text = (REPO / ".claude/skills/verify/SKILL.md").read_text(encoding="utf-8")
assert str(rows) not in text
```

A substring is not a count. `verify/SKILL.md:148` cites the row that
removed the figure — `` `UX-503` `` — and the reference reached 503
rows on CI, so the guard matched its own citation:

```console
$ python3 -c "print(len(json.load(open('tests/ci_reference.json'))['files']))"
488
$ # CI, run 34140771782, job test (3.11), head 9e24e0f:
FAILURE test_the_verify_skill_no_longer_counts_the_reference
  AssertionError: the verify skill states the reference's row count (503)
$ python3 -c "
from pathlib import Path
t = Path('.claude/skills/verify/SKILL.md').read_text()
print('488 present:', '488' in t, '/ 503 present:', '503' in t)"
488 present: False / 503 present: True
$ grep -n 503 .claude/skills/verify/SKILL.md
148:**After adding a test file, do nothing.** `UX-503`: a file the
```

Local green, CI red, on the same commit — the reference is adopted on
the default branch (`UX-503`) so the two sides count different rows.
The sentence the guard checks is *"the skill states the reference's row
count"*; the population it reads is *any occurrence of those digits*,
which includes every `UX-` id in the file. The guard names `UX-503` in
its own failure message and is broken by that same string.

Line 148 predates this branch (`3ac4816`), so the defect is latent on
`main` and fires whenever the adopted count collides with a cited id.
`test_the_researcher_no_longer_counts_the_backlog` is the same shape
against `.claude/agents/researcher.md`.

## Required Fix

Both guards match a **number**, not a digit run: strip `UX-\d+` before
searching, and require the remaining match not to be part of a longer
number. The failure message keeps naming the row, since that is what a
reader needs.

## Out of Scope

- The counts themselves. `UX-503` and `UX-471` decided those figures do
  not belong in the documents; this row is only the instrument.
- The reference's adopt job — its behaviour is `UX-503`'s design and
  correct; it is what makes the two sides disagree, not a fault.

## Acceptance Test

```console
$ python3 -m pytest tests/unit/test_the_process_documents_derive_their_figures.py -q
```

green with a reference forced to 503 rows, and red when a real bare
count is written into either document.

## Outcome

The gap, measured. CI run 34140771782, job `test (3.11)`, head `9e24e0f`:

```console
FAILURE test_the_verify_skill_no_longer_counts_the_reference
  AssertionError: the verify skill states the reference's row count (503)
$ python3 -m pytest tests/unit/test_the_process_documents_derive_their_figures.py -q
23 passed in 0.92s          # locally, where the reference has 488 rows
```

The close, measured. Both guards strip `UX-\d+` before searching and
require the match not to sit inside a longer number:

```console
$ python3 -c "print(len(json.load(open('tests/ci_reference.json'))['files']))"
503                         # reference forced to CI's count
$ python3 -m pytest tests/unit/test_the_process_documents_derive_their_figures.py -q
23 passed in 1.27s
```

| # | mutation | reddened |
|---|---|---|
| M1 | revert to `str(rows) not in text`, reference at 503 | `test_the_verify_skill_no_longer_counts_the_reference` — reproduces the CI failure |
| M2 | append `The reference carries 503 rows today.` to the skill, fix in place | the same test — a real bare count still reds |

M1 proves the fix load-bearing; M2 proves it did not defang the guard.

Deviation: none. `researcher.md` carries no colliding id today, but its
guard had the identical shape and was fixed with the same helper rather
than left to fire later.
