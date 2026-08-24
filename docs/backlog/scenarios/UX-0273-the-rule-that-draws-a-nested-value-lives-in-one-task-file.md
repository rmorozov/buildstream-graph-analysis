# UX-273: the rule that draws a nested value lives in one task file

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-267 | **Serves:** the maintainers, R8 | **Topic:** docs

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

## Outcome — 🟢 Fixed & Verified

The viewer chapter gained the value rule beside the hint rule, and the
acceptance test passes on the phrase it named:

```text
$ git grep -n "width, not depth" -- docs/design/
docs/design/architecture.md:561:- **A value is drawn by width, not depth** (`UX-267`, round
```

The bullet sits directly under *"The page is schema-driven"*, which is
where the confusion was: that bullet tells a maintainer what a field is
*called* and where it sits, and said nothing about what happens to its
**value**. The new one covers the three renderings — inline, bounded
table, fold — the separate rule for long text (a long **value**
truncates with the whole thing kept; a long **explanation** does not,
because the sentence is the point), and the one thing a reader would
otherwise get wrong on their own:

> Depth is deliberately not the criterion, and that is the whole choice:
> a two-level object of four fields reads fine inline, and a flat one of
> forty does not.

**Clause 2 held, and is the half with teeth.** The thresholds are named
(`OBJECT_INLINE_FIELDS`, `ARRAY_INLINE_ITEMS`, `CELL_TEXT_CAP`) and
their values are not restated, so a later round that retunes them moves
one number in one file. Clause 3's link to Direction 12 carries the
argument and the before-picture, so the chapter states the rule without
re-arguing it.

**The guard** — `tests/unit/test_the_value_rule_has_a_home.py`,
10 tests. It checks the rule is in the chapter, that all three branches
are named, and — both directions — that every constant the rule rests on
is named in the chapter *and* still exported by `bga/viewer/app.js`. The
reverse direction is not decoration: a document pointing at a name the
module has renamed is worse than one that copied the number, because it
reads as checkable and is not.

`test_the_chapter_does_not_restate_the_numbers` enforces the clause that
made this item worth filing rather than fixing casually. It is written
as a *threshold claim* check — `\d+ (fields|items|entries|characters)`
matched against the exported values — rather than as a ban on the digits
`4`, `6` and `160`, which would have fired on "round 36" and on `UX-267`
in the same paragraph. A guard that has to be worked around is a guard
that gets deleted.

Falsified, seven mutations:

```text
M1  remove the bullet (the state review 2 found)  -> 6 of 10
M2  drop the fold branch                          -> test_it_names_all_three_renderings
M3  drop the depth sentence                       -> test_it_says_depth_is_not_the_criterion
M4  name two of the three thresholds              -> names_the_constant[CELL_TEXT_CAP]
M5  name a constant the module never exported     -> names_the_constant[CELL_TEXT_CAP]
M6  rename CELL_TEXT_CAP in app.js                -> test_the_constant_exists[CELL_TEXT_CAP]
M7  write "objects of 4 fields or fewer"          -> does_not_restate_the_numbers
```

M5 and M6 are the same defect approached from its two ends — the
document drifting from the module, and the module drifting from the
document — and they redden different tests, which is what makes the pair
worth having rather than one of them.
