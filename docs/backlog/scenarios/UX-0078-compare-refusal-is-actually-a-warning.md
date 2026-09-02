# UX-78: the compare "refusal" the docs promise is actually a warning

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Topic:** cli

## Motivation

`README.md:165` promises "a refusal if the two runs don't look like the
same project or the same cache scenario", and
`docs/guides/real-project.md` repeats it twice more, once under a list of
things the tool guarantees ("`bga compare` refuses rather than producing
a meaningless delta"). The code deliberately does the opposite — both
checks *flag, don't block* (`bga/compare.py:191-196`, `:213-217`) — and
the live behavior is a confident verdict over nonsense:

```text
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

`docs/guides/cli.md:193` says "a warning", so the documentation also contradicts
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
`docs/guides/cli.md` updated to match whatever ships.

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
4. The README/guide sentences and `docs/guides/cli.md` quote the same behavior.

## Fix Implemented

The documented philosophy won: `bga compare` refuses by default, with a
distinct exit code, and prints no comparison.

```text
$ bga compare tests/fixtures/golden/mixed_task_kinds <real fdsdk run>
Refusing to compare these runs (shared_elements):
  - baseline has 4 element(s), candidate has 126 - only 0 shared element UID(s)
    (less than half) - these runs may not be the same project
Pass --allow-mismatch to compare anyway (the comparison is then printed with the
warning above, as it was before UX-78).
$ echo $?
6
```

All four acceptance criteria, verified live on that pair and on fixtures:

1. Exit **6** naming `shared_elements`; `--allow-mismatch` exits 0 and
   prints the old warning plus the comparison.
2. A caches-off run against an incremental one exits 6 naming `run_mode`.
3. `--fail-on-regression` on a mismatched pair exits **6, not 4** — the
   sharpest form of the defect, since a CI job keying on 4 would have
   read an artifact-path bug as "your build got slower".
4. `README.md`, `docs/guides/real-project.md` and `docs/guides/cli.md` now quote
   the same behaviour, including the exit code and the escape hatch.

Two details worth stating:

- **The refusal happens before the comparison is printed or written.**
  Printing arithmetically-correct nonsense beside a refusal would leave a
  reader to decide which of the two to believe.
- **The checks are published structurally** as `mismatches[]`, each
  `{check, message}` with a stable `check`, so a consumer keys on
  `shared_elements`/`run_mode` rather than on prose — the same posture
  `UX-75` established for the analysis findings.

The `--allow-mismatch` path also gained the caveat the old message
carried ("treat every figure below with real skepticism"), which now sits
where there really is a comparison below it.

Tests: 7 new in `tests/unit/test_compare_mismatch_refusal.py`, including
the gate-cannot-mistake-a-mismatch case and a guard that an ordinary
comparable pair is unaffected. Suite: 1118 → 1125.

## Verification Log

Fixed 2026-08-18. The live refusal above is `bga compare` against the
capture published as `5eda28a`; the exit codes were read from the shell,
not from the source.
