# UX-446: a third ceiling, and no reader-facing document has it

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** review 8, checklist item 3 — `UX-430`'s own §3.10 debt, one round later | **Serves:** anyone whose export drops the timeline and goes looking for the reason | **Topic:** docs

## Motivation

`UX-430` added `TRACE_TRACK_BUDGET`, a second bound on the Perfetto
handoff in the unit Perfetto actually spends. Two documents still say
there is one.

`docs/guides/cli.md` publishes the ceilings as a table of exactly two
rows, and the second says the trace's byte figure is

> the **gzipped trace** before it is base64-encoded — one part of the
> data half, and the only part either ceiling singles out

`docs/design/styleguide.md` §3g opens:

> `tools/bga_view.py:601` carries **the only bound** the Perfetto
> handoff has

Both were true when written and neither is now. A reader whose export
refuses for **16,832 tracks** reads a table of byte ceilings, finds the
trace comfortably under the one it names, and has nowhere to go.

`git grep TRACE_TRACK_BUDGET -- docs` returns nothing: the number the
refusal quotes is stated in one docstring and in no document.

## Required Fix

- **The ceilings table carries all three**, each in its own unit and
  each saying what to do when it is the one that bit — for tracks that
  is `--planes 1` or `--only-element`, which `cli.md` already documents
  a section earlier and does not connect to the refusal.
- **§3g's opening sentence closes**, the way §4e's did in round 70:
  the section is a rule with a worked example, and the example's "only
  bound" is now the thing the rule fixed.
- Check the same sentence has not been copied elsewhere —
  `docs/guides/what-the-viewer-answers.md` states the 4 MiB transport
  change and may or may not imply exclusivity.

## Out of Scope

- **The bound's value** — one sample, and `UX-445` holds it.
- **The narrowing flags themselves**: documented by `UX-430` in
  `cli.md`'s `bga timeline` section. This item connects them to the
  refusal rather than describing them again.

## Acceptance Test

`git grep -c TRACE_TRACK_BUDGET -- docs` is non-zero; the ceilings
table has a tracks row naming the flags; and §3g no longer opens on a
claim `UX-430` falsified. A mutation adding a fourth bound in a fourth
unit and leaving the table at three must redden a guard — which means
this item ends with the table derived from the constants rather than
written beside them, or with a guard that compares the two.

## Outcome (round 71, 2026-08-31) — 🟢 Done

### The gap

```console
$ git grep -c TRACE_TRACK_BUDGET -- docs
(nothing)
```

Three bounds in the code, two in `cli.md`'s table, and the one a reader
is most likely to hit named in a docstring. `docs/design/styleguide.md`
§3g opened on "carries the only bound the Perfetto handoff has" - which
was true when written and had been falsified by §3g's own consequence.

### After

```console
$ git grep -c TRACE_TRACK_BUDGET -- docs
docs/audits/architecture-review.md:1
docs/backlog/scenarios/UX-0430-...:2
docs/backlog/scenarios/UX-0445-...:6
docs/backlog/scenarios/UX-0446-...:3
docs/backlog/scenarios/closed.md:1
docs/design/styleguide.md:1
docs/guides/cli.md:2
```

The table carries all three, each in its own unit and each with what to
do when it is the one that bit. The tracks row names `--planes 1` and
`--only-element` - documented a section earlier in `cli.md` and, until
now, connected to nothing.

### Checked against the constants, not maintained beside them

The Acceptance Test asks for a mutation adding a **fourth** bound in a
fourth unit to redden something. That means the table cannot simply be
rewritten, so `bga_view.CEILINGS` declares the set and
`test_the_ceilings_reach_a_reader.py` closes the loop three ways:

- every `*_BUDGET*` this module exports is in `CEILINGS` - read off
  `dir(view)`, so a fourth constant is in the population the moment it
  exists, whatever it is called;
- every declared ceiling has a row in the table;
- the table names none that does not exist.

The first is the one the acceptance test names, and it fails **before**
anyone has to notice the prose.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| E1 | a fourth bound (`TRACE_FLOW_BUDGET`) added and the table left at three | `test_every_budget_constant_is_declared_a_ceiling` (1 failed, 4 passed) |
| E2 | the tracks row's remedy replaced with "it is refused" | `test_each_row_carries_the_remedy_its_registry_entry_names` (1 failed, 4 passed) |
| E3 | the tracks row deleted | that clause and `test_every_declared_ceiling_has_a_row_a_reader_can_find` (2 failed, 3 passed) |
| E4 | §3g's opening restored to the falsified claim | `test_the_styleguide_no_longer_says_there_is_only_one` (1 failed, 4 passed) |

### A remedy I had to correct before it shipped

The registry's first draft said the byte ceiling's remedy was
"`--no-trace`". **There is no such flag.** `bga view --export` writes
the report whatever its size and prints a note - "said, not enforced: a
report that large is still the user's report" - and `export()`'s
`with_trace` parameter has no command line. Caught by looking for the
flag rather than by a guard, which is worth recording: the guard checks
that a remedy is *there*, and only a reader checks that it is true.

### The third document

`docs/guides/what-the-viewer-answers.md` did **not** imply exclusivity:
its 4 MiB sentence is about the transport changing shape, so the item's
third bullet finds nothing to correct. It gained a bullet
anyway, because that guide is about *when to drop into Perfetto* and
the track bound is the one case where the answer changes: the trip has
to be made with fewer lanes rather than not at all.

### Deviation from the Required Fix

- **None.** All three bullets, and the acceptance test's condition is
  met by the registry rather than by a second copy of the table.

### The suite

```console
$ make lint
All checks passed!
```

(the full-suite line is in `UX-447`'s Outcome - the two documentation
items were verified in one run.)
