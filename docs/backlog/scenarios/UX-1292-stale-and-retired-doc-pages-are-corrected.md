# UX-1292: the stale claims the docs audit found are corrected, and the retired stub is removed

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** none | **Found by:** the docs audit (2026-10-02, findings 1, 7, 9, 10) | **Serves:** R1, R5 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_viewer_question_count_is_the_codes.py`

## Motivation

`docs/design/roles.md:43` says R5 has "no queueing model, no arrival
rates", though `capacity-model/v1` ships through
`bga snapshot --capacity N,RATE`. README.md:117 and
`what-the-viewer-answers.md:53,86` say the viewer serves "eighteen"
questions; `bga.provenance.TRACE_QUERIES` holds 24 keys (whether the
page serves all 24 is unverified). `continuous-build-improvement.md:12-16`
still says it waits on "a one-line move" as of 2026-09-20.
`guides/optimization-walkthrough.md` is a 14-line retired stub.

## Required Fix

R5's cell names only what is still missing (arrival rate measured,
not typed; a price per builder). The viewer count is read from the
code, and a guard ties the prose to it. The design note's status is
dated to its real state. The stub is deleted and inbound links point
at `real-project.md`.

## Out of Scope

The restructure (UX-1289, UX-1290).

## Acceptance Test

`grep` for each stale phrase returns nothing; the count guard reddens
when `TRACE_QUERIES` gains a key and the prose does not.

## Outcome (2026-10-02) — 🟢 Done

**Premise:** held for three of four; falsified for the count -
`TRACE_QUERIES` keys are the 24 *claims* that open a question, and the
page serves 18 questions, so "eighteen" was right and stays.

### The gap, measured

```text
$ node --input-type=module -e 'const {QUESTIONS}=await import("./bga/viewer/questions.js"); console.log(QUESTIONS.length)'
18
$ python3 -c "from bga.provenance import TRACE_QUERIES as T; print(len(T), len({q for v in T.values() for q in v}))"
24 18
roles.md:43   "no queueing model, no arrival rates, no price on a builder"
continuous-build-improvement.md:12-20   "Status: proposed ... Two documents now wait on that one-line move"
              section 8's rows UX-895..UX-906: 12 of 12 Done
$ git grep -c 'optimization-walkthrough\.md' HEAD -- ':!docs/backlog' ':!docs/audits'
              19 lines in 18 files (14 of them example 04's comments)
README.md:117 "sorts all eighteen canned questions" - guarded by nothing
```

### After

```text
$ grep -rn 'no queueing model, no arrival rates\|one-line move' docs/design README.md    (nothing; rc=1)
$ git grep -c 'optimization-walkthrough\.md' -- ':!docs/backlog' ':!docs/audits'        (nothing)
$ ls docs/guides/optimization-walkthrough.md     No such file or directory
$ python3 -m pytest -q tests/unit/test_the_viewer_question_count_is_the_codes.py tests/unit/test_docs_links_and_commands.py
60 passed
```

R5's cell names `capacity-model/v1` and only what is missing (an arrival
rate measured, a price per builder). The design note is dated
2026-10-02, its twelve rows closed, still unnumbered. Inbound links go
to `real-project.md` (architecture, examples/README) or, where they
cite example 04's transcript (example comments, `ci.yml`, `UX-0005`),
to `audits/optimization-walkthrough-04.md`. The new guard ties
README.md and both guide sentences to `QUESTIONS.length`.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| A1 | `QUESTIONS` gains a 19th entry, prose unchanged | 1 failed: README + 2 guide sentences want "nineteen" |
| A2 | README.md "sorts all eighteen" -> "seventeen" | 1 failed: README wants "eighteen" |
| A3 | guide "Ten of the eighteen" -> "sixteen" | 1 failed: guide wants "of the eighteen questions" |

The Acceptance Test's clause "reddens when `TRACE_QUERIES` gains a key"
is not asserted: a claim gaining a key adds no question, so a guard
reading it would red on a correct page.

### Deviation from the Required Fix

The count is read from `bga/viewer/questions.js`, not `TRACE_QUERIES` -
the task's premise for it measured false.
