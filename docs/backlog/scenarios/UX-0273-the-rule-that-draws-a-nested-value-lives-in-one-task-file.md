# UX-273: the rule that draws a nested value lives in one task file

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-267 | **Serves:** the maintainers, R8 | **Topic:** docs

## Motivation

Found by review 2 (`UX-241`). Round 36 gave the viewer a rule that now
decides how **every** nested value in the report is drawn — an object
of four fields or fewer is inlined into its cell, a wider one becomes a
bounded table, a longer one folds; the choice is made on **width, not
depth**. It governs `renderStructured` and therefore every schema field
that carries an object or an array.

Where that rule is written down:

```text
$ git grep -c "width, not depth" -- docs/
docs/backlog/scenarios/UX-0267-every-object-is-a-details-called-object.md:1
```

One line, in the task file that shipped it. The architecture's viewer
chapter — the place a maintainer adding a schema field reads, and the
place `UX-233` was filed to keep current — describes the *hint*
mechanism in detail:

```text
docs/design/architecture.md, "## The viewer axis":
  "**The page is schema-driven.** ... Sections, columns, units and
   hover text come from the *view-hints* the published schemas carry
   (`bga:quantity`, `bga:question`, `bga:columns`, `bga:rail`,
   `bga:markers`, ...), so a field that gains a description in
   `bga/schemas.py` gains a tooltip in the page with no page edit."
```

and says nothing about what happens to the field's **value**. A
maintainer reading that chapter learns that adding a field is free and
does not learn that its shape decides its rendering, that
`OBJECT_INLINE_FIELDS = 4` and `ARRAY_INLINE_ITEMS = 6` are the
thresholds, or that a field longer than `CELL_TEXT_CAP = 160`
characters will be truncated with a fold. This is the same shape as
`UX-244`: a live convention whose only home is the code that
implements it.

It is worth more than a docstring because it is the answer to a
question schema authors will actually ask — *how will this show up?* —
and because the thresholds are tuned numbers that a later round will
move, at which point a document that names them is the thing that
notices.

## Required Fix

1. The architecture's viewer chapter gains the value rule beside the
   hint rule: width not depth, the three outcomes, and the three
   constants by name.
2. The constants are named, not copied — the document points at
   `bga/viewer/app.js`'s exported names rather than restating `4`, `6`
   and `160` where they can drift.
3. `docs/design/directions.md`'s Direction 12 (round 35) is the
   argument; the architecture chapter is the *statement*, and links to
   it rather than repeating it.

## Out of Scope

- Documenting each renderer function. The chapter describes mechanisms,
  not the module's API.
- A guard that the constants and the prose agree numerically. Clause 2
  removes the numbers from the prose, which is the cheaper fix; if a
  guard falls out of it, that is a bonus.

## Acceptance Test

`git grep "width, not depth" -- docs/design/` returns the architecture
chapter. A reader who has read only the viewer chapter can predict
which of the three renderings a new object-valued schema field will
get.
