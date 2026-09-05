# UX-388: an empty population disappears without a word

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-107 ("nobody could look" is not "looked and found nothing"), UX-286 (the report has chapters), UX-320 (the page conforms to its sections) | **Serves:** anyone reading the report of an incremental build | **Topic:** viewer | **Area:** bga/viewer

## Motivation

Round 63 ran the user's `snapshot` → `view` cycle twice over
`examples/06-macro-micro-optimization` — a cold build, then an
incremental one — and diffed the two exported pages. This is what the
second one lost:

```text
                        run 1 (full)   run 2 (incremental)
page height                  9,316 px            3,347 px
sections                           71                  36
payload keys                       51                  30
```

Thirty-five sections and 5,969 px of report vanished, and the page
says nothing about any of them. Six named populations:

```text
optimization_horizon      5 rows -> []       section gone
latent_heavies            1 row  -> []       section gone
joint_saving              object -> null     section gone
violations                []     -> []       never present
consolidation_candidates  []     -> absent   never present
```

The mechanism is one line in `bga/viewer/app.js`:

```javascript
if (!value.length) return null;
```

An empty array renders no heading, no sentence, and no rail entry, so
the reader has no way to distinguish three different facts that the
tool itself distinguishes:

- the analysis ran and found nothing (`optimization_horizon: []`),
- the analysis could not run on this capture (`joint_saving: null`),
- this version of `bga` does not compute it at all (absent key).

That is exactly `UX-107`'s rule — *"nobody could look" must not read
as "looked and found nothing"* — which the tree applies to Plane 2
coverage blocks and has never applied to a population. The incremental
run is the common case, so the reader who most needs to know that the
horizon is empty *because there was nothing to build* is the reader
who is told least.

The rail makes it worse rather than better: it lists what rendered, so
a section that rendered nothing is missing from the map of the report
as well as from the report.

## Required Fix

An empty population is a result, and the page states it.

- **`renderSection` distinguishes empty from absent.** An empty
  collection renders its heading, its schema sentence, and one line
  saying it is empty — in the vocabulary `UX-214` already set, so
  "no elements are above the horizon" rather than "0 rows". An absent
  key renders nothing, because nothing was computed.
- **The distinction is the payload's, not the viewer's guess.** If
  `analyze/v4` cannot today tell "computed, empty" from "not
  computed", that is the half of the fix that belongs in the contract:
  a population the analysis ran is present and empty, not omitted.
- **The rail carries the empty sections too**, marked as empty, so the
  map of the report matches the report on every run.

## Falsification

Two exports of the same project, one cold and one incremental, and a
guard that asserts every population present in either payload has a
heading in both pages, and that a population which is empty says so in
words. Today the incremental page fails on five headings.

The other direction, so the fix is not "render everything": a key the
payload does not carry must still render nothing, and the page's
section count must not grow on the cold run at all. `UX-360`'s volume
budget is the ceiling — an empty section is one line, not a table
shell.

## Out of Scope

- Whether the six populations should be computed on an incremental
  run. That is an analysis question; this item is about the page not
  hiding the answer either way.
- The terminal report. `bga analyze` already prints a sentence for
  most empty blocks; a comparison of the two vocabularies is `UX-329`
  territory.

## Outcome (round 65, 2026-08-29) — 🟢 Done

### After, on the two committed fixtures

```text
                         before   after   sections now marked empty
golden                       44      47   consolidation_candidates,
                                          serialization_point_risks, violations
macro_micro                  64      66   consolidation_candidates, violations
rail entries (golden)        44      47
```

Every one of those was invisible before — not folded, not stubbed:
absent from the document, and therefore absent from the rail, so the
map of the report described whatever happened to be non-empty on this
run.

### The rule: the contract decides, not the value

```text
[] or {} on a declared collection   -> a section, marked empty
null on a declared collection       -> a section, marked empty
null on a declared scalar           -> nothing, as before
an empty value with no schema node  -> nothing, as before
a key the payload does not carry    -> nothing, as before
```

The `null` row is load-bearing and was nearly missed. `joint_saving` is
`None` — not `{}` — when its input set is empty
(`bga/analyzer.py:1799`), so a rule that looked only at `[]` would have
left one of the six sections the round found still vanishing. And a rule
that rendered every `null` would have put a heading over every unset
scalar in the payload; `section: null` is a declared **string** and has
never been a section.

### What this section deliberately does not do

The Required Fix asks for the heading, **the schema sentence**, and one
line. The sentence is not here. `UX-346` made the rule that a
description renders beside its value only where the contract declares it
inline, and `UX-317` that every described value carries a `?` marker; a
`<p class="description">` under a heading satisfies neither. The first
version did it anyway and reddened four clauses across
`test_a_sentence_lives_on_its_door.py` and
`test_apparatus_in_its_place.py`. The rule is older and better argued
than the convenience, so the sentence stays where the rule puts it, and
a clause of this item's own guard now holds it out.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | `return null` for every empty value — the defect | six of nine clauses (6 failed, 3 passed) |
| A2 | the contract check dropped: every empty value is a section | the two absent-stays-absent clauses (2 failed, 7 passed) |
| A3 | the heading renders and the "found none" line does not | the says-so-in-words clause (1 failed, 8 passed) |
| A4 | `data-empty` is not set | the rail clause and two others (3 failed, 6 passed) |
| A5 | a `null` collection vanishes again | the joint-saving clause (1 failed, 8 passed) |

**Two of these did not discriminate on their first run**, and the fix
was to the probe rather than to the count. A2 and A5 originally killed
the harness — `JSON.stringify` on a DOM node is a circular structure —
so the mutation "went red" by crashing rather than by failing a clause
that says what is wrong. The two fields the mutations turn into nodes
are now serialised as booleans, and A2 reddens two named clauses. A5's
first form also crashed the *renderer* (a `null` falling through to code
that dereferences it), which is a real fact about the mutation and not
about the guard; the recorded A5 is the honest one — the null branch
restored to `return null`, which is exactly the code this item replaced.

### Deviation from the Required Fix

- **No schema sentence in the empty section**, for the reason above. The
  heading, the rail entry and the line all landed.
- **The payload needed no change.** The Required Fix says "if
  `analyze/v4` cannot tell 'computed, empty' from 'not computed', that
  is the half that belongs in the contract". Measured: it already can —
  `optimization_horizon: []` is present-and-empty and
  `consolidation_candidates` is absent on a run that does not compute
  it. The viewer was dropping a distinction the contract already made.

### The export, split

```text
                page half     data half (golden / macro_micro)
before           271,453        95,549 / 148,380
after            272,719        95,549 / 148,380
                  +1,266              unchanged
```

All source. Nothing was added to any payload; what changed is that
three of golden's keys and two of macro_micro's now reach a reader.
`PAGE_BUDGET_B` 273,000 → 274,000 and both export bounds restated with
that split.

### Verification

```text
pytest tests/unit/test_an_empty_population_says_so.py           9 passed
pytest tests/unit/test_the_report_you_can_attach.py            24 passed
make test                       4,995 passed, 26 skipped, 245.2s
make lint                                                       clean
```
