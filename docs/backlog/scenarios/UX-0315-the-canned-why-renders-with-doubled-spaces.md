# UX-315: every canned question's `why` renders with doubled spaces

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Serves:** R1 | **Topic:** viewer

## Motivation

`bga/viewer/questions.js` builds each `why` by concatenating string
literals across lines, and every continuation begins with a space
while the previous line already ends with one:

```js
why:
  "Plane 1's element spans, aggregated - scoped to the element " +
  " plane, so Plane 2 command names cannot crowd the answer.",
```

The reader sees `the element  plane`. Measured: **13 of 13**
questions are affected, so it is the file's convention rather than
one slip, and every one of them is prose the page renders.

Found while `UX-312` was raising the page budget, and deliberately
not fixed there: the six pre-existing questions are text that item
had no other reason to touch, and "trivial and adjacent" is how a
pull request widens.

## Required Fix

The continuations lose their leading space, and a guard asserts no
`why` contains a double space — cheap, and the kind of defect that
comes back the next time someone adds a question by copying the one
above it.

## Out of Scope

- Rewording any `why`. This is whitespace; the sentences are right.
- The same pattern anywhere else. If it exists elsewhere the guard
  should widen, but that is a search, not an assumption.

## Acceptance Test

No `why` in `QUESTIONS` matches `/  /`; the guard reddens when a
continuation's leading space is restored.

## Outcome (round 45, 2026-08-26) — 🟢 Done

### The gap, measured

Every `why`, read by running the module it lives in:

```text
 3 element-time            3 time-by-kind           5 waited-on-flow
 2 process-storm           4 failed-processes       5 concurrency-curve
 4 sandbox-tax             5 cpu-versus-wall        5 which-run-is-this
 3 stalls                  5 peak-rss
 2 element-commands        3 dependency-wait
---
questions: 13   with a doubled space: 13
```

49 runs of doubled space across 13 of 13 questions — the file's
convention, as the filing said, not one slip.

### The fix, and the invariant that says it changed nothing else

The continuations lose their leading space: 49 lines edited. The
wording is untouched, and that is asserted rather than eyeballed —
each `why` after the edit equals the old string with runs of spaces
collapsed to one:

```text
questions: 13
whys equal to the old text with runs of spaces collapsed: 13 / 13
whys still containing a doubled space: 0
```

That invariant is what rules out the failure mode this edit could
have had: stripping a leading space where the previous literal did
*not* end in one would silently join two words.

### The search the Out of Scope asked for

The filing declined to assume the pattern lived elsewhere and asked
for a search. It was run — a literal ending in a space concatenated
with one beginning in a space, over every `.js`, `.py` and `.html`
under `bga/` and `tools/`:

```text
the search, run on HEAD's questions.js:  49 sites
the search, run on the working tree (105 files): no sites
```

Run against the pre-fix file first, so a scan that found nothing is
distinguishable from a scan that cannot find anything. The pattern
was `questions.js`'s alone, so the guard does not widen to cover a
defect nobody found — it holds the *shape* across the shipped tree,
which is what catches the next question copied from the one above it.

### The guard

`tests/unit/test_the_canned_prose_reads_as_written.py`, four clauses:
no prose field of a question carries a doubled space; the `sql`
exclusion is real and stated (12 of 13 queries indent their own text
inside a template literal — layout, not a typo); no shipped module
glues two spaces together; and the shape scan actually read the tree
it claims to.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| S1 | restore one continuation's leading space (the acceptance test verbatim) | both the prose clause and the shape clause — 2 failed, 2 passed |
| S1b | a doubled space *inside* one literal, no glued shape | the prose clause alone, naming `{'process-storm': ['why']}` |
| S2 | plant the glued shape in a **different** shipped file (`app.js`) | the shape clause alone, naming `{'bga/viewer/app.js': [54]}` |
| S3 | narrow `SOURCE_ROOTS` to one file | the coverage clause: "the shape scan read only 0 files" |
| S4 | reformat all 13 queries so no SQL indents itself | the `sql`-exclusion clause |

S1 is the acceptance test as the filing words it, and it reddens *two*
clauses, because restoring the source shape restores both the shape and
the doubled space it produces. That is not a discriminating mutation for
either clause on its own, so S1b and S2 were added to isolate them: S1b
produces the rendered defect without the shape, S2 the shape without the
rendered defect, and each reddens exactly one clause. S2's first attempt
did not land at all — the anchor `export function el(` is not in
`app.js` — and a mutation that never happened proves nothing, so it was
rewritten against a real anchor rather than counted.

### Deviation from the Required Fix

None. The Required Fix asked for the leading spaces dropped and a guard
asserting no `why` contains a double space; both landed. The three
clauses beyond that one are the Out of Scope's own search, turned into
a standing check after it came back empty.
