# UX-227: why is this ranked first

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-207 (the ranking), UX-215 (the join), UX-216 (the element object) | **Serves:** R1, R8 | **Topic:** viewer

## Motivation

The fourth external review's cheapest good idea. The page can say
`openssl.bst` is worth fixing, that it saves ~522 s, that it sits at
18.6% of the critical path, that it has 14 downstream consumers and
that it regressed +81 s since the last capture — in five different
sections. What it cannot do is say them *together, as the reason*:
click the top action and get "why is this ranked first" as one
compact answer. The reader assembles the case by scrolling; the tool
already holds every fact in a published field.

This is semantic composition, not analysis: `headline.top_actions`
names the element, `element_join` carries its planes,
`critical_path_detail` its share, the store history its delta. No
number needs deriving — only gathering under the question.

## Required Fix

An explanation block per top action (rendered on click or focus):
the ranked element's saving, path share, downstream count and
history delta, each value read from the published field it cites
(`data-field` refs, the UX-202 pattern), closing with the actions
that already exist (Investigate, blast, history). When `UX-229`'s
provenance object lands, this block re-plumbs to read it instead of
composing — the composition is the interim, the contract is the
destination.

## Out of Scope

- Any ranking logic in the viewer (the order is `top_actions`' own).
- New analysis or new fields (a fact the block wants but no payload
  carries goes through the pipeline first, per Direction 7).

## Acceptance Test

On the golden run: each top action's explanation values are
byte-traceable to the published fields they cite (walked via
`data-field`/`data-raw` back into the payloads, the UX-202 guard
extended); mutation: an explanation value with no resolvable field
reference reddens. The block renders nothing for an element absent
from the join rather than guessing. Export carries the explanations
inline (no server dependency).
