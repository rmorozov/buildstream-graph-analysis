# UX-674: eighteen font sizes, an h3 larger than its h2, and 130-character lines

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-305 (the conformance checklist), UX-316 | **Serves:** every reader of prose on the page | **Topic:** viewer | **Shape:** judgement

## Motivation

```text
distinct computed font sizes     18   (body/td 15 · section p 16.32 · section h2 16.8 · h3 17.55 · chapter h2 20.8 · h1 22.4 · …)
h3 vs its h2                     17.55 px > 16.8 px
prose line length                ≈ 122 chars (verdict, 993 px) · 133 (finding title) · 127 (next-step reason)
contrast                         fg 17.4:1 · muted 5.74 · accent 7.21 · warn 5.0 (4.47 on --muted-bg)
```

Three sentences a reader has to re-read: the verdict ("chain-bound"
three times, two percentages before the verb, 122-char lines); the
core.bst card's 257-character sentence with five numbers and a
slash-alternative; a provenance sentence with nested dashes, a raw
`>=` and a payload key, and one that ends a 399-character sentence
with "(UX-116)". The styleguide has color and emphasis budgets and
no type budget.

## Required Fix

Styleguide **§4f, "The type scale"**: a four-step scale (body 15 /
small 13 / h2 17 / h1 21; h3 = body at weight 600 and always smaller
than its h2); `p, li > p, dd {max-width: 72ch}`; task ids and payload
keys never inside prose (§4b extended to sentences). The three
sentences above rewritten as the worked examples.

## Out of Scope

- Contrast — every measured pair passes; the one 4.47 (warn on
  muted-bg) is at the boundary and noted, not filed.

## Acceptance Test

Guard: distinct computed sizes ≤ 4 on the golden page; every h3
smaller than its h2; no `p` wider than 72ch. Mutation: add a fifth
size — red.
