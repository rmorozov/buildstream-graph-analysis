# UX-346: two thirds of the page is the schema's own sentences

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-220 (the numbers that need a sentence have one), UX-317 (apparatus in its place) | **Serves:** every reader of the report | **Topic:** viewer

## Motivation

`UX-220` gave every declared quantity a sentence, sourced from the
contract so it cannot drift from the payload. That was right. What was
never decided is *where the sentence goes*, and the answer the page
settled on is: beside the value, always, for every value.

Measured on a real boot at 1440x900, counting the words a reader
actually sees:

```text
                words on the page   of which always-on notes
golden                     3,448           2,510   (72%)
macro_micro                5,026           3,388   (67%)
```

Two thirds of the report is prose that is identical on every run. It
does not describe *this* build; it describes the field. And it is
printed **twice over** — every term also carries a `?` door offering
the same sentence on demand:

```text
Hit share      ?   0.0%   Cache hits as a share of lookups.
Built elements ?   11     Elements that actually built, rather than
                          coming from cache.
Category us    ?   2.7 s  Wall-clock in the attribution category this
                          finding is about.
```

The value is three characters. The sentence is nine words. The `?` is
an affordance for a sentence already on screen.

**What it costs beyond ink.** The page is 18,148 px on `macro_micro` —
twenty screens. Two thirds of the words being run-invariant is most of
the reason. It also flattens the type: a finding's *conclusion* and the
glossary entry for one of its fields are set at the same size, weight
and colour, so nothing on the screen looks more important than anything
else.

**The one place the sentence earns its permanence** is a value whose
meaning a reader cannot guess and would misread — `UX-343` wrote 157 of
them for exactly that reason. That is an argument for the sentence
existing and being one click away, not for printing it beside a number
whose label already says what it is.

## Required Fix

The description is on the `?` door and not beside the value. The door
already exists, is already keyboard-reachable, and already carries the
contract's own sentence — this deletes the duplicate, not the feature.

Two exceptions stay inline, and are the whole exception list:

- a value whose *name* is misleading without it (`critical_path_length`
  is `UX-345`'s case; the general shape is a number whose unit or
  population is not derivable from its label);
- a value the schema marks as a caveat rather than a description —
  the "not a measurement" class `UX-129` and `UX-275` write, which is a
  warning and belongs where the number is.

Both are declared in the contract rather than decided per call site, so
the page cannot drift back.

## Out of Scope

- Deleting or shortening the sentences. They are `UX-220`'s contract
  and `UX-326`'s rule that the tool's sentences are contracts; this is
  about altitude only.
- The `->` gloss under a finding's title. That sentence states what
  happened in this run rather than what the field means, so it is
  content and not apparatus.

## Acceptance Test

On both committed fixtures, always-on note words are under 25% of the
page's words, measured the way the figures above were. Every sentence
removed from beside a value is reachable from that value's `?` door,
asserted by walking every term and opening its door. The two declared
exceptions render inline and nothing else does.

## Outcome (round 52, 2026-08-28) — 🟢 Done

### The gap, measured

`UX-317` built the door in round 41 and it never shut. Measured in
Chrome at 1440x900 on the golden export, before this item — the
sentence's own state, its computed style, and its box:

```text
sentence.hidden                 true
getComputedStyle(s).display     "inline"
getBoundingClientRect()         458 x 15
marker aria-expanded            "false"
```

`[hidden]` is a UA rule at specificity (0,0,0). `.description` sets
`display: block`, and the wide breakpoint sets `display: inline`, both
at (0,1,0). Both beat it, so **every sentence rendered on every load**
and the `?` toggled a property with no visual effect at all.

That is what the always-on prose was. Counted by role on the two
committed exports, at the commit this item was worked from:

```text
             height       words    sentence words        described
golden       11,120 px    3,466    1,479  (42.7%)        86 / 86 on screen
macro_micro  21,533 px    6,283    2,312  (36.8%)       146 / 146 on screen
```

**The filed figures were 72% and 67%, and they are wrong.** The round-52
census counted `.pairs dd` whole — the *value* cell — so every number on
the page counted as prose. The figures above count
`[data-role="description"]`, which is the population the item is about.
The instrument was the defect twice in one round; `UX-343`'s census was
the other.

### After

```text
             height       words    sentence words        inline   doors
golden       10,423 px    2,303      249  (10.8%)        12 / 86     74
macro_micro  20,417 px    4,514      442  ( 9.8%)        23 / 146   123
```

And the mechanism, measured the same way:

```text
closed   display "none"    box   0 x  0    aria-expanded "false"
open     display "inline"  box 458 x 15    aria-expanded "true"
closed   display "none"    box   0 x  0
```

### One rule, and why it is one rule

```css
.description[hidden] { display: none; }
```

(0,2,0) against (0,1,0), so it wins in both blocks wherever it sits in
the file. Nothing else in the viewer changed to close the door.

Paper gets the same answer as the screen, deliberately: a printed
report carrying every field's definition is the glossary nobody asked
for, and the declared exceptions print because they are not behind a
door at all. `UX-317`'s print clause still holds — it forbids a
`@media print` rule that hides a description or its marker, and there
is none.

### The exceptions are declared, not decided at the call site

`bga:inline` names one of two reasons, and the page reads it the way it
reads every other hint:

| reason | the test | declared on |
|---|---|---|
| `name` | the label invites a reading the value does not have, or invites none at all | 14 keys — `useful_share` (a share of *capacity*), `share_of_path`, `share_of_host`, `builders`, `effective_cpus`, `host_cpu_count`, `cores_busy`, `wall_clock_share_us`, `t_infinity_observed`, `horizon_us`, `started_at_us`, `path_us`, `criticality_probability`, `builders_change` |
| `caveat` | reading the number without the sentence changes what a reader would *do* | 10 keys — `recommended_builders` (a hypothesis, not a setting), `t_infinity_cold`, `checks_ran`, `oversubscribed`, `undersubscribed`, `cpu_accounting_available`, `effective_cpus_source`, `unaccounted_us`, `unmatched_ends`, `sum_of_individual_us` |

A declared exception draws **no `?`** — a door beside a sentence already
on screen is the duplication this item is about — and `UX-317`'s marker
clause now reads `markers == described - inlined` rather than
`markers == described`.

**A sixth caveat candidate was dropped rather than declared.**
`certified_headroom_us` is a finding's evidence key *and* a key of the
decision block, and the two carry different sentences — "zero means the
scheduler is not the constraint" against "repeated here from `floors`".
A name that renders inline in one block and behind a door in another is
`UX-341`'s drift under a new heading, and the guard that caught it is
the one asserting every declared key on the page renders inline.

### Verification

```text
make lint    pymarkdown + ruff, all checks passed
make test    4384 passed, 21 skipped
guard        17 passed (2 fixtures x 8 clauses, plus the three static ones)
```

### Mutations verified red and reverted (6)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `fc45f94`.

| # | mutation | reddened |
|---|---|---|
| D1 | `.description[hidden] { display: none }` removed — the defect itself | 8 clauses: *"golden: 1479 of 3466 words (43%) are the schema's own sentences, against a bound of 25%"*, *"macro_micro: 1803 of 5041 (36%)"*, and *"a closed door already showing its sentence: ['primary', 'violation_count', 'category_us', …]"* |
| D2 | `bga:inline: "loud"` on `share_of_path` | `test_every_declaration_names_one_of_the_two_reasons` |
| D3 | `INLINE` on `decision.scheduling_gap_us` with its `description` removed | `test_every_declaration_has_a_sentence_to_keep_inline` |
| D4 | `describedTerm` draws a `?` beside an inline sentence too | 5 clauses, including `UX-317`'s `markers == described - inlined` |
| D5 | `INLINE` dropped from `hintsOf`'s key list — the page stops seeing the declaration | `test_a_declared_exception_really_does_render_inline` on both fixtures |
| D6 | every described value treated as inline (`hintsOf(child)[INLINE] ?? "name"`) | 8 clauses, including *the page renders these inline and the contract does not declare them* and the 25% bound |

### What this did not do

The page is 10,423 px and 20,417 px — 11.6 and 22.7 screens. Removing
the prose took **8%** and **5%** off the height, not the two thirds the
word count might suggest, because at 1440px the sentence sat *beside*
the value on the same line rather than under it. Height is `UX-347`'s
item, and it now has the page to choose its bound against, which is why
it was filed second.
