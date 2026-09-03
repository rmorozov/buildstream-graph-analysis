# UX-558: the failure's name is 3,800 lines from the end of the job that also runs the gate

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-554 (which added the naming step), UX-441 and UX-491 (which set the rule) | **Serves:** the reader who has the log and not the browser | **Topic:** guards

## Motivation

`UX-441` set the rule: the failure stays the last thing in the log.
`UX-491` named the reader it is for — one with the log and not the
artifact, "a terminal, an API client, a proxy that blocks the
artifact's blob host". `UX-554` added a step that names the failing
tests. All three are satisfied on three of the four matrix jobs and
none of them on the fourth.

The `test` job's steps, derived:

```text
10. The failing tests, named          <- UX-554
...
14. Tiers match CI's own record of them   <- the gate that exits 1
16. This run's timings, for refreshing the reference  <- ~400 lines
17. Upload it, so refreshing the reference needs no scrolling
18. This run's touching map, for adopting
19. Upload it, so the adopt job can merge it
```

Steps 12-19 run only on 3.11. So:

```text
test (3.12), 669 lines total   step 10's output sits 4 lines from the end
test (3.11), 3,992 lines total step 10's output sits ~3,800 lines from the end
```

Measured on round 81's own PR. On 3.12 the name was immediately
legible and identified `UX-546`'s clause in one fetch:

```text
1 test(s) failed, named here because the log tail above may be truncated (UX-554):
  FAILURE ...TestTheServerKnowsWhetherTheTraceWasFetched::test_a_second_reader_is_a_second_fetch
          AssertionError: assert {'fetches': 1, 'bytes': 785} == {'fetches': 2, 'bytes': 785}
```

On 3.11, three separate tail fetches at 12, 42 and 48 lines returned
only artifact-upload and cleanup noise; the GitHub API's log tail is
clamped by size, and the reference document is inside the clamp.

The `::group::` around the document collapses it **in the browser
only** — over the API it is 400 plain lines like any other. So the
`UX-491` reader, the one the group was written to protect, is the one
reader it does not protect.

## Required Fix

A decision between two rules that now conflict on one job:

- `UX-476` wants the reference document in the log, for a reader
  without the artifact.
- `UX-441`/`UX-491`/`UX-554` want the failure last.

The cheapest reconciliation is order: run the naming step **last**, or
repeat its line after step 16 the way `UX-491` repeats the gate's. The
other is to stop printing the document and lean on the
`ci-reference-candidate` artifact plus `UX-457`'s route — but that
reopens exactly what `UX-476` closed, so it is a decision, not a tidy.

Whichever, a guard must assert the naming step is the last step that
writes to the log on every job that has one.

## Out of Scope

- `UX-557`, the cause filter that made 3.11 red in the first place.
  Different mechanism, different fix; this row is about reading the
  log, not about what put a failure in it.
- The size of the reference document. `UX-441` already measured it and
  chose the file-plus-one-line shape.

## Acceptance Test

On a job whose suite failed and whose drift steps ran, the last 40
lines of the raw log contain the failing test's id.

## Outcome (round 81, 2026-09-03) — 🟢 Done

**Premise:** held — the failing id sat ~3,800 lines from the end of 3.11's log and 4 lines from the end of 3.12's.

### The decision

**Move the naming step last in the `test` job**, not repeated after the
document, and the document keeps printing.

`UX-491` met this conflict and *repeated* the gate's line, because the gate's
exit code is the job's verdict at its own position and the step cannot move. The
naming step has no such constraint — it exits 0 by design and gates nothing — so
a reorder buys the same property as a second copy plus a summary-file hand-off.
**Repeating it: rejected** on that. **Dropping the document: rejected** — it is
`UX-476`'s route for the reader whose egress denies the artifact's blob host.

### The gap, measured

`test_the_ordered_steps_leave_the_id_in_the_tail` replays the `test`
job's own `run:` scripts, in the workflow's order, on the 3.11 red
path, against a CI-shaped junit. Under M1 — the naming step back at
step 10 of 20, the arrangement this row was filed against:

```text
AssertionError: the failing id is not in the last 40 of 1265 lines; a
reader with the log and not the artifact cannot name what failed.
The tail is:
      "tests/unit/test_what_if_you_could_choose_the_fixes.py": [
```

1,265 lines of a 1,266-line log stand between the id and the end, the
last 40 being the document's tail — round 81's 3,800-of-3,992 at this
reference's size (161 testcases against CI's ~400).

### After

Same replay, same 1,266-line log, the step last:

```text
the id 'test_a_second_reader_is_a_second_fetch' is at line 1265 of 1266,
which is 2 line(s) from the end
```

1,265 lines from the end to 2; the clause pair is `2 passed, 131 deselected in
0.96s`. `UX-491` is not undone: on the other red path — gate red, suite green — the
naming step prints **1 line** (`the junit records no failure - the suite failed
elsewhere`), so the repeated gate line lands 1 line from the end rather than at it.

### Mutations verified red and reverted (4)

`PYTHONDONTWRITEBYTECODE=1`, `__pycache__` cleared. Counts are what the
run printed.

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | naming step back to step 10 of 20 | both clauses | 2 failed, 131 deselected |
| M2 | the step deleted outright | both, and `UX-554`'s `..._names_the_failures_on_the_failure_path` | 3 failed, 136 passed |
| M3 | one step appended after it | `..._is_the_last_step_of_its_job` | 1 failed, 1 passed |
| M4 | the document stops printing | `..._leave_the_id_in_the_tail`'s own discriminator | 1 failed, 1 passed |

M3 reddened the ordering clause and **not** the tail clause, correctly:
one appended line buries nothing, so the two are not one guard twice.
M4 is the tail clause guarding its own discriminator — the document
gone, the log is 11 lines, and it says so rather than passing.

### Deviation from the Required Fix

None. The Required Fix asked for a decision between named candidates
and a guard on the ordering; both are above.

```console
$ make test-touching   638 passed, 3 skipped in 18.69s; 3 red, one fact
$ make lint            ruff + PyMarkdown, All checks passed!
```

Those 3 are all `UX-558: table says 🔴, file says 🟢`. The index row is
the orchestrating session's after the merge (`UX-501`), so this commit
used `BGA_SKIP_SELECTOR=1`; setting the row back to 🔴 turns all three
green, so nothing else of this change is in them. The 12 other files
reading `ci.yml`: 283 passed. The clauses cost 0.22s, no tier list.
