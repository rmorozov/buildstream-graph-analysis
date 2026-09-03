# UX-556: the spec still says "the last four are written but not printable"

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** `UX-549` (which fixed the architecture's copy) | **Found by:** `UX-549`'s track, which could not edit ground truth | **Serves:** anyone counting contracts from the spec | **Topic:** docs

## Motivation

`UX-549` derived five counted figures rather than restating them. One
of the five had a second copy the item could not touch:

```text
docs/design/architecture.md:965   "The last four rows are written but not printable"   -> fixed
docs/spec/specification.md:1671   the same sentence                                    -> still there
```

Six rows are written but not printable, not four, and they are not
last — nine read-never-written rows follow them. The architecture's
copy is now derived from `bga.contracts.unprintable()`; the spec's is
a literal, and `docs/spec/specification.md` is ground truth that a
round may not edit outside the Part 32 registry.

## Out of Scope

- Editing the spec here: declined, because that is the rule this
  repository is built on and one wrong count is not the reason to
  break it. This row exists so the count is not forgotten instead.
- Re-deriving the architecture's copy — `UX-549` closed that.

## Required Fix

Decide who may correct ground truth and by what route, then take it.
The two candidates: a Part 32 registry entry that carries the derived
count so the prose can point at it rather than restate it, or an
explicit amendment procedure for a factual error in a Part outside 32.
Either way the decision is the deliverable, not the edit.

## Acceptance Test

`docs/spec/specification.md:1671`'s claim agrees with
`len(bga.contracts.unprintable())`, or the spec points at the derived
figure instead of carrying one — with the route that permitted the
change written down.

## Outcome (round 81, 2026-09-03) — 🟢 Done

### The gap, measured

```text
$ sed -n 1671p docs/spec/specification.md
The last four are **written but not printable**: they are on-disk
$ python3 -c "from bga import contracts as c; \
    print(len(set(c.unprintable()) - set(c.superseded())))"
6
```

Wrong twice: the set is six, and four rows follow it rather than
preceding nothing. `unprintable()` alone reads 15 — it carries the 9
superseded ids too, so the sentence's own citation was loose as well.

### The decision, which is the deliverable

**The premise was wrong, and that is what closed the row.** The
sentence is at line 1671; Part 32 spans 1515-1788. It is *inside*
Part 32, which the rule has always permitted editing. `UX-549`
deferred it reading "the Part 32 registry" as the table alone, and
this row inherited that reading without checking the line numbers.

So the governance question is not "who may correct ground truth" but
"where does Part 32 end", and it is now written where the rule lives
(`CLAUDE.md`): **the whole Part — the table, and the prose counting
the table's own rows.** A rule permitting a row's correction but
forbidding the sentence that counts the rows is not a boundary.
Everything outside Part 32 is unchanged and still read-only.

The second half of the decision: **a counted figure there is guarded,
never restated.** A number in prose that nothing checks is what
produced both copies of this error.

### After

```text
$ sed -n 1671p docs/spec/specification.md
The six above the retired rows are **written but not printable**: they
$ BGA_EXPECT_DEV=1 python3 -m pytest \
    tests/unit/test_a_counted_figure_is_derived.py -q
13 passed in 0.29s
```

`TestTheSpecCountsItsOwnTable` derives both halves from the table's own
rows — the count from `unprintable() - superseded()`, the position by
reading the last four rows and the six above them.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| M1 | the old sentence back ("The last four are…") | the count clause — 1 failed, 1 passed |
| M2 | `host/v1` moved above the written-not-printable block | the position clause — 1 failed, 1 passed |
| M3 | "The five above the retired rows" | the count clause — 1 failed, 1 passed |

M1 and M3 hit the count, M2 the position, so the two clauses
discriminate separately rather than one covering both.

### A guard of my own that did not discriminate

The first `_spec_contract_rows` bounded the table at `# Part 33` and
swept up `UX-540`'s *inputs* table further down the Part, putting
`trace/v9`, `graph/v9` and `run-context/v9` among the retired rows. It
failed loudly rather than passing wrongly, which is the only reason it
is a note and not a defect.

### Deviation from the Required Fix

**One.** The Required Fix offered two candidates — a Part 32 registry
entry carrying the derived count, or an amendment procedure for a Part
outside 32. Neither was needed: the sentence was never outside the
permitted region. The deliverable is still a decision, but it is a
*boundary* decision, and the edit followed from it rather than needing
a new route.
