# UX-491: the drift gate's own line has no route a reader can reach

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** `UX-476` built the same route for the candidate | **Found by:** round 73, closing `UX-488` | **Serves:** the round that has to pair a run's printed shift with the spread it recorded and cannot read the first one | **Topic:** guards

## Motivation

`UX-476` added a `::group::the same document, for a reader without the
artifact` block so the reference candidate could be read by an API
client with no artifact access. `UX-488` used it, and found the other
half missing.

The **gate's own line** — the one that says how many files were
measured, at what shift, over what population — is printed by
`tools/dev_tier_drift.py --against` to stderr, in a step that runs
before the candidate. A GitHub log-reading client returns only a
bounded tail of a job's log, and on a full-suite job the candidate
document (nearly 400 lines) fills it. So on run `33544888654` the
recorded `spread` could be read and the gate line that should be paired
with it could not:

```text
candidate  {'files': 377, 'shift_files': 138, 'shift': 1.069, ...}
gate       (above the returned tail)
```

`UX-488` had to take its pairing from the previous run instead, and
said so. The pairing is the check that `UX-476` item 2 actually landed,
so it should not depend on how much of a log a client happens to get.

## Required Fix

- The gate's summary reaches a reader who can only read a log tail —
  the same `::group::` treatment the candidate got, or the line
  repeated in the candidate step, or the numbers carried in the
  candidate document itself.
- Whatever it becomes, `UX-488`'s Acceptance Test — a run's printed
  shift beside the spread it recorded, from **one** run — can be met
  without the artifact.

## Out of Scope

- The gate's verdict logic, which `UX-476` settled.
- Downloading the artifact — the route `UX-457` built, which works and
  is not the thing at fault here; it is simply not available to every
  reader, which is what this row is about.

## Acceptance Test

One CI run's gate line and its recorded `spread`, both pasted, both
read from that run's log alone.

## Outcome

**Round 75, 2026-09-02.**

**The gap.** `UX-488` could read run `33544888654`'s recorded `spread`
and not the gate line it had to be paired with — the gate prints two
steps and one ~400-line collapsed document before the end of the job,
and a log-tail reader gets the document.

**The close.** `--against` writes the line it printed to `--summary
PATH` on **every** return; the candidate step prints that file after
its `::endgroup::`. The line stays the gate's own — recomputing it in
the later step would make the shift and the spread agree by
construction (§5), which is the check `UX-476` item 2 wanted.

**Acceptance Test — run `33581936314`, `test (3.11)`, from that run's
log alone, consecutive lines:**

```text
  "spread": {
    "files": 368,
    "shift_files": 142,
    "shift": 0.994,
    "min": 0.101,
    "p25": 0.805,
    "p75": 1.107,
    "max": 8.284
  }
}
##[endgroup]
the drift gate's line, repeated for a log-tail reader:
tiers ok: 399 file(s) measured against ci_reference.json (github-actions
ubuntu-latest, test (3.11), -n auto), this run x0.99 from 142 file(s)
over 1s, IQR 0.14
```

Printed shift **x0.99**, recorded `spread.shift` **0.994**, one run,
adjacent in the tail. That is `UX-488`'s pairing, made.

**Mutations.** `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` cleared.

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | the gate step drops `--summary` | `..._is_printed_where_a_log_tail_reader_gets_it`, `..._lands_after_the_document` | 2 failed, 7 passed |
| M2 | the line moves inside the `::group::` | `..._lands_after_the_document`, `..._does_not_fail_the_printing` | 2 failed, 7 passed |
| M3 | the stale-agreed branch stops writing | `..._a_stale_runner_that_repeated_still_leaves_a_line` | 1 failed, 8 passed |
| M4 | `done()` writes nothing at all | 8 of the 9 branch clauses | 8 failed, 1 passed |
| M5 | the later step re-runs `--against` | `..._does_not_recompute_the_shift` | 1 failed, 8 passed |
| M6 | the `\|\|` fallback goes away | `..._a_gate_that_never_ran_does_not_fail_the_printing` | 1 failed, 8 passed |
| M7 | the line drops the shift | `..._carries_the_shift_the_gate_printed` | 1 failed, 8 passed |

M4 leaves exactly one clause green — `..._no_summary_asked_for_writes_no_file`,
which asserts absence — so the set discriminates in both directions.

**A mutation that turned out not to mutate.** M2's first attempt
replaced `endgroup + line` with `line + endgroup`; a comment block sits
between them in the file, so the replacement matched nothing and the
guard "passed" against an unchanged workflow. Falsifying a guard means
checking that the mutation landed, not only that the edit ran.

**The claim the guards hold** is not "some branch writes a summary" but
that **no return path of `_against` leaves the file absent** — nine
clauses, one per branch, including the two `stale` verdicts `UX-508`
added and the `waiting`/`recorded` paths `UX-503` added.

**Deviation from the Required Fix:** the third option it offered —
carrying the numbers in the candidate document — is deliberately not
taken. `spread.shift` is `shift_of`, the same function the gate
divides by, so a document that also carried the gate's line would have
the two agreeing by construction and check nothing.

**Two commits, not one.** The Acceptance Test is a CI run (§7), so the
mechanism landed first and this Outcome second. That is the shape any
CI-only acceptance test has here, and `UX-500` should read it as such.
