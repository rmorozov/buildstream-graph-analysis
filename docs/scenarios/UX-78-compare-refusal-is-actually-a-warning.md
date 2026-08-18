# UX-78: the compare "refusal" the docs promise is actually a warning

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** —

## Motivation

`README.md:165` promises "a refusal if the two runs don't look like the
same project or the same cache scenario", and
`docs/real-project-guide.md` repeats it twice more, once under a list of
things the tool guarantees ("`bga compare` refuses rather than producing
a meaningless delta"). The code deliberately does the opposite — both
checks *flag, don't block* (`bga/compare.py:191-196`, `:213-217`) — and
the live behavior is a confident verdict over nonsense:

```
$ bga compare tests/fixtures/golden/mixed_task_kinds <real cmake run>
Verdict: REGRESSED  (total duration +16.91s, +105668.8%, 0.02s -> 16.92s)
  Warning: baseline has 4 element(s), candidate has 11 - only 1 shared
  element UID(s) (less than half) - these runs may not be the same project...
exit=0
```

With `--fail-on-regression` that pair exits **4** — the same exit code as
a genuine regression. In CI, the most likely way to feed `compare` two
unrelated runs is an artifact-path bug, and the pipeline would report
"your build got slower" instead of "your job is comparing the wrong
things". The one place that *does* refuse is the `--baseline-run` set
path (`ValueError` on identity mismatch, `bga/compare.py:369-376`), so
the tool currently has two contradictory philosophies about the same
hazard, and the docs describe only the one that is not the default.

`docs/cli.md:193` says "a warning", so the documentation also contradicts
itself.

## Required Fix

Pick one philosophy and align code and docs. The right one is the
documented one: comparisons across project identity or cache scenario
should **refuse by default** with a distinct exit code (6 is free;
4/5 are taken by the gates) and a one-line reason naming the check that
failed, with an explicit `--allow-mismatch` escape hatch that restores
today's warn-and-compare behavior (the guide's own "compare against
another incremental run" advice needs the cross-mode case to stay
*possible*, just not silent). All three README/guide sentences and
`docs/cli.md` updated to match whatever ships.

## Out of Scope

- The definition of run identity itself (UX-07 settled it).
- Multi-run baseline mechanics (they already refuse).

## Acceptance Test

1. `bga compare <golden fixture> <any real run>` exits 6 with a message
   naming the shared-element check; with `--allow-mismatch` it exits 0
   and prints today's warning + comparison.
2. `bga compare <caches-off run> <incremental run>` (fixture pair) exits
   6 naming the cache-scenario check; `--allow-mismatch` restores the
   comparison.
3. `--fail-on-regression` on a mismatched pair exits 6, not 4 — a CI job
   keying on 4 can no longer mistake a plumbing bug for a regression.
4. The README/guide sentences and `docs/cli.md` quote the same behavior.
