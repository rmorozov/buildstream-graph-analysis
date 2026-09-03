# UX-558: the failure's name is 3,800 lines from the end of the job that also runs the gate

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-554 (which added the naming step), UX-441 and UX-491 (which set the rule) | **Serves:** the reader who has the log and not the browser | **Topic:** guards

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
