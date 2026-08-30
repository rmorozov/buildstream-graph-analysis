# UX-414: two sections fall into "Everything else", and the guard's fixture cannot see it

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** UX-400's sweep, first run | **Serves:** anyone navigating a two-plane report | **Topic:** viewer

## Motivation

[`bga/viewer/chapters.js`](../../../bga/viewer/chapters.js) says of the
fallback chapter:

```js
// The last chapter, for a section with no entry and no rail. It is not
// a hiding place: `test_the_report_has_chapters` asserts it is empty on
// both runs, so a section that lands here reddens a guard rather than
// disappearing into a bucket.
```

That guard is green, and two sections are in the bucket. `chapterFor`
resolved against the analyze payload of `tests/fixtures/macro_micro`:

```text
restructuring rail= undefined chapter= more
binary_cost   rail= undefined chapter= more
findings      rail= undefined chapter= decide
readers       rail= undefined chapter= decide
```

Neither is in `CHAPTERS` and neither declares a `bga:rail`, so both
land under a heading that says nothing about them. `binary_cost` has
been there since `UX-370`; `restructuring` since `UX-407`, this round.

The guard is not wrong, its fixture is: `_boot_chapters` exports a
**single-plane** run, and both sections only exist when Plane 2 is
present. Measured on `tests/fixtures/golden/mixed_task_kinds`:

```text
restructuring present: False   binary_cost present: False
```

So "asserts it is empty on both runs" is true of the two runs that
fixture has, and neither of them is a run where either section exists.

## Required Fix

- File both sections in `CHAPTERS`. `binary_cost` answers "where did
  the time go" at the program level; `restructuring` answers "what if
  I change this" - it is a list of edges to delete.
- Give `test_the_report_has_chapters` a two-plane boot, so the
  fallback-chapter clause is asserted over a payload that publishes
  every section rather than the subset one fixture emits.

## Out of Scope

- The chapter *ordering* question. This is about a section having a
  chapter at all.

## Acceptance Test

- `UX-400`'s `test_every_swept_population_is_filed_under_a_chapter`
  goes green with an empty ledger, and the ledger entry is deleted in
  the same commit as the fix.
- `test_nothing_falls_through_to_everything_else` runs on a two-plane
  export and stays green.

## Outcome (round 65, 2026-08-30) — 🟢 Done

### The filing's premise is false, and the reason is a harness bug

Neither section was in "Everything else". Both declare `bga:rail: act`
and `chapterFor` falls back to the rail, so both landed in **"Where
did the time go?"** — measured on the rendered two-plane export,
`[section, rail, chapter]`:

```text
[["readers","decide","decide"], ["findings",null,"decide"],
 ["restructuring","act","time"], ["binary_cost","act","time"]]
```

The `more` reading came from `UX-400`'s sweep, which resolved the rail
as `app.hintsOf(node)[format.RAIL]` — and `RAIL` is a module-private
constant `format.js` does not export:

```text
$ node -e 'const f = await import("./bga/viewer/format.js");
           console.log("RAIL =", JSON.stringify(f.RAIL))'
RAIL = undefined
```

So the expression was `hints[undefined]`, every rail came back
`undefined`, and every section not listed in `CHAPTERS` resolved to the
fallback. **The fifth harness bug in this sweep**, joining the four its
own docstring records, and the second this round after the card count.
The reading goes through `format.heading(key, hints).rail` now, which
is the call the page itself makes and which applies the page's own
`?? "raw"` default.

`chapters.js`' claim that the fallback "is not a hiding place" is
therefore **correct**, and `test_the_report_has_chapters` was not
hollow about it.

### The defect underneath, which is real

`restructuring` is a list of dependency edges nothing ever reads — the
answer to *what if I change this*, written as edges to delete. Its rail
put it under *Where did the time go?*, one heading away from the blast
control and the what-if planner that answer the same question.

Both sections are named in `CHAPTERS` now — `restructuring` under
`change`, `binary_cost` under `time`, where its rail had it and where
it belongs.

### Nothing could have caught it, and now something does

The fallback clause catches a section with **no** chapter. A section
with a `bga:rail` always has one, so *filed under the wrong heading* is
invisible to every clause in that file. `PLANE2_CHAPTERS` names the two
and asserts where they land, which is what both mutations below redden.

### The two-plane boot, and the sidecar that would have made it hollow

`_boot_chapters` takes a fixture now, and the fallback clause is
parametrised over both. The two-plane leg needed one more thing than
the filing says: `plane2.json` is a **sibling** of the run directory,
not a file inside it, so `copytree(run)` produces a single-plane copy
of a two-plane fixture — a second leg that costs a boot and measures
the same page. The copy carries the sidecar, and
`test_the_two_plane_run_publishes_more_than_the_one_plane_run` asserts
the second fixture really does publish the sections the leg exists for.

Re-tiered with the measurement: `4.9s → 14.7s`, still medium.

### Mutations verified red and reverted (3)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| D1 | `restructuring` unfiled again — it falls to its rail, into `time` | `test_the_two_plane_sections_are_where_they_answer`; 1 failed, 14 passed |
| D2 | `binary_cost` moved to the `decide` chapter | the same clause; 1 failed, 14 passed |
| D3 | the `plane2.json` sidecar not copied | `test_the_two_plane_run_publishes_more_than_the_one_plane_run`, naming both sections; 1 failed, 13 passed |

D1 is the one that proves the fallback clause could never have caught
this: with `restructuring` unfiled,
`test_nothing_falls_through_to_everything_else` stays **green on both
legs**, because the rail gives it a chapter — the wrong one.

### Deviation from the Required Fix

- **The Motivation's central claim did not survive measurement**, and
  the fix changed shape accordingly: both sections are filed, as the
  filing asks, but for being under the *wrong* heading rather than
  under none. Recorded rather than quietly re-aimed.
- The Acceptance Test's first clause — *`UX-400`'s
  `test_every_swept_population_is_filed_under_a_chapter` goes green
  with an empty ledger* — is met, though the ledger was empty in
  reality before this round too. The clause it now makes is narrower
  and true: a section with neither an entry nor a rail.
