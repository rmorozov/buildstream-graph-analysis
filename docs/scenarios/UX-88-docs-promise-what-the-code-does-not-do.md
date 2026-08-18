# UX-88: a documentation-drift sweep — the docs promise things the code does not do

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-78 (the one behavioral item, filed separately)

## Motivation

A full claims-vs-reality audit (round 10) checked every substantive
README/cli.md claim against the code and live runs. One finding was
behavioral and is filed as UX-78; the rest are documentation stating
something checkably false or stale. Individually small; together they
erode exactly the trust the report's numbers depend on. The checklist,
each item verified against source or a live run:

1. **README quick start shows the wrong output.** `README.md:23`'s
   command (`bga analyze tests/fixtures/golden/mixed_task_kinds`)
   produces `Total Duration: 0.0s`, confidence 0.88, a 3-element path;
   the block at `README.md:28-50` is byte-for-byte the output of
   `make dev-run ARGS=--large`. Show each command's real output.
2. **Efficiency Score formula wrong in cli.md.** `docs/cli.md:77` says
   `LB / total duration`; the code computes `LB / horizon`
   (`bga/analyzer.py:410` — whose own comment at `:397` also still says
   total_duration). On the golden fixture the two differ 1.00 vs 0.875.
3. **Exit code 4 is documented too narrowly.** `docs/cli.md:341` says
   4 = `--fail-on-regression` only; it is also returned by the UX-54
   build-failure gate and `--fail-on-low-confidence`, including when
   only the efficiency gates were requested (`bga/cli.py:295-334`). A CI
   consumer keying "4 = slower" mis-triages a failed build.
4. **`docs/cli.md:82`** ("Key Findings … presentation-only … JSON
   unaffected") predates UX-75 and contradicts `docs/cli.md:96`.
5. **No published list of `findings[].id` values** anywhere, though
   cli.md calls `id` "part of the contract" CI keys on. Publish the full
   set (15 in `bga/findings.py` + correlate row ids).
6. **The band-mode example is not a runnable invocation.**
   `README.md:167`'s `--baseline-run A --baseline-run B --band-k 3.0`
   omits the required positional baseline; verified exit 2. Show the
   real shape.
7. **`--calibration-dir` documented nowhere** user-facing
   (`bga/cli.py:794-801`); `--invocation-log`/`--argv-log`/`--raw-log`
   likewise `--help`-only (the default-behavior half is UX-80).
8. **`README.md:136`'s category list omits untracked head/tail** while
   claiming the listed categories "sum to exactly the total build time";
   on the README's own fixture untracked tail is 12.5%.
9. **`--cold` with no history prints nothing at all** in text
   (`bga/report/text.py:386`), not the documented "reported as
   unavailable" (`docs/cli.md:151`).
10. Smaller: compare verdict values omit `not comparable …`
    (`bga/compare.py:285`); "verbatim" JSON snippets omit the `rows`
    array; `docs/architecture.md:280` lists UX-60 as Done vs the
    backlog's 🟡; `docs/architecture.md:217` "all 22 scenario files"
    (there are 76); `docs/ingestion-pipeline.md` fact 5 contradicted by
    P4-11/UX-52 and by its own §403-425; correlate accepts `-f csv` and
    silently renders text (`bga/cli.py:513-515`); README's dev section
    omits that `make test` needs `.[dev]`; `examples/06/optimized`'s
    lib-f comment says codegen is "the one element that actually
    consumes it" while the baseline's UX-46 note says measurement showed
    it does not.

## Required Fix

Fix every numbered item in place (docs edits; the two one-line code
comments in 2 may be corrected in the same commit). Where behavior and
docs disagree, this task fixes the *docs* to the current behavior —
except where a separately filed item (UX-78, UX-80) will change the
behavior, in which case the doc lands with that item.

## Out of Scope

- Behavioral changes (UX-78, UX-80, UX-87).

## Acceptance Test

For items 1, 2, 6 and 9: run the quoted command and confirm the doc now
shows what actually happens. For item 5: every id emitted across the
fixture corpus (`grep`ing real `--format json` output) appears in the
published list. A re-run of the audit's claim checklist over the edited
docs finds zero remaining discrepancies.
