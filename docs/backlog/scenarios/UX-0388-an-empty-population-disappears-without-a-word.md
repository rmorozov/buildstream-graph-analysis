# UX-388: an empty population disappears without a word

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-107 ("nobody could look" is not "looked and found nothing"), UX-286 (the report has chapters), UX-320 (the page conforms to its sections) | **Serves:** anyone reading the report of an incremental build | **Topic:** viewer

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
