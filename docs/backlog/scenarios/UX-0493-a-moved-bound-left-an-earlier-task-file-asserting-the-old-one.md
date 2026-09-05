# UX-493: a bound moved and the task file that presents it as current was not annotated

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** `UX-469` moved the figure; `UX-132` is the rule | **Found by:** architecture review 10 | **Serves:** the round that reads `UX-479`'s Outcome for the export bound and gets a number the tree has not had since the same day | **Topic:** docs | **Area:** tools

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

**Round 75, 2026-09-02.** A parallel `implementer` track; merged here.

**Clause 1 — the annotation.** `UX-0479`:285, five lines under the
stale sentence, naming `UX-469`, `406,000 → 411,000` and the tree's
`("golden", GOLDEN, 411_000)` at 407,265 B. Form copied from
`UX-0458`:188, not invented.

```console
$ git grep -n "406,000" docs/backlog/scenarios
UX-0469-...md:215:`golden`'s bound moved 406,000 → 411,000 with the
UX-0479-...md:280:with that table pasted above it; golden's 406,000 stands.
UX-0479-...md:285:> **Annotated by `UX-493` (round 75): golden's 406,000 did not stand.**
```

**Clause 2 — the other moved figures, each recorded.**

| figure | tree now | verdict |
|---|---|---|
| golden `406,000` | 411,000 | **stale → annotated** |
| `macro_micro` `458,000` | 458,000 (457,284 B, 716 B headroom) | checked, clean |
| `macro_micro` `450,000` | superseded | clean as history — both sites are past-tense Outcomes |
| finding census counts | 24 \| 22 \| 2 \| 0 | clean — all 16 sites are pasted fenced runs |
| trace census counts | `Plane 1: 4 reached, 0 shared, 2 dropped…` | clean as history |
| golden `403,318` | 407,265 B | clean — no backlog site |

**Clause 3 — the decision: the grep can be mechanical, the verdict
cannot.** Seventeen of the eighteen occurrences above are correct *as
history*, and telling those from `UX-0479`:280 is reading a sentence.
A pass/fail there would be fixing guide §5 shape 1. But round 73's
failure was not a wrong judgement — the review's own words are "`git
grep 406,000 docs/backlog/scenarios` … It was not run." So the grep is
what was built: `--figures` (and `--move`, unprompted) prints the
figures a diff removed that the backlog still writes, says explicitly
that each is a judgement, and always returns 0. 0.18s over 490 files.

Replayed against `UX-469`'s real commit, on the backlog as it stood at
that commit's parent:

```console
$ python3 tools/dev_close_task.py UX-469 --figures --diff ux469.diff \
    --scenarios .../before/docs/backlog/scenarios
§3.6: 1 figure(s) removed by this diff, 1 still written.
  406,000
    UX-0479-...md:280  with that table pasted above it; golden's 406,000 stands.
  Each is a judgement: annotate the file, or record it in your Outcome
  as history. Nothing here decides that.
```

One hit, and it is the defect. No false positives on that commit.

**The first implementation was wrong, and its guard is why.**
Subtracting added figures across the *whole* diff printed `0 figure(s)
removed` on `UX-469` — because that commit wrote `406,000 → 411,000`
into its own task file, cancelling the figure it had moved. A commit's
record of a move is not the move undone. Fixed per file; M1 is that.

**Mutations.** `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` cleared;
baseline and post-revert both 18 passed in 0.71s.

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | whole-diff `gone - kept` (the bug shipped first) | `..._own_record_does_not_cancel_the_figure` | 1 failed, 17 passed |
| M2 | `_FIGURE` separator `[,_]` → `[,]` | 3 clauses | 3 failed, 15 passed |
| M3 | backlog side joins digit groups with `""` | 2 clauses | 2 failed, 16 passed |
| M4 | summary printed only when there are hits | 2 clauses | 2 failed, 16 passed |
| M5 | `skip` filter disabled | `..._not_reported_against_itself` | 1 failed, 17 passed |

M2 and M3 are the same property from opposite sides, so the
normalisation is a distinction rather than a rename.

**A guard that does not discriminate cleanly:**
`..._not_reported_against_itself` asserts on `"none still written"`,
which M4 also reddens. M5 shows it *does* discriminate for its own
property, but the assertion is coarser than the claim.

**Deviation from the Required Fix:** none. `--figures` is not in the
module docstring — that is at the register's 25-line cap and "older
ones only shrink"; `--move` printing it unprompted carries it instead.
