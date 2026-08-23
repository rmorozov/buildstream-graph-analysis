# UX-227: why is this ranked first

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-207 (the ranking), UX-215 (the join), UX-216 (the element object) | **Serves:** R1, R8 | **Topic:** viewer

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

## Outcome (round 28)

A `<details>` fold under each top action: the rule that ranked it, what
this run measured about it, the findings that name it, and its history
across the store. Every value carries the path it was read from in
`data-field`, in the grammar `bga/provenance.py` walks — so a reader
follows the reference back into the payload rather than trusting the
number, and so does the guard.

**It reads the contract rather than composing.** The Required Fix said
the composition was the interim and `UX-229` was the destination;
`UX-229` landed two commits earlier, so this went straight to the
destination: the "why" sentence is `provenance.rule.sentence`, reached
by following the top action's `see` pointer into the finding's record.
The mutation that proves it is the page wording its own reason — "It is
the biggest one." — and it reddens.

**The facts gather themselves.** `SOURCES` (`UX-216`) already declared
where each per-element fact comes from; rows now also carry
`` `${array}[${idKey}=${uid}].${field}` ``, built from that declaration.
Adding a fact is still one line in `SOURCES`, and it arrives traceable.

### A bug this found in UX-229, one commit old

`provenance._segments` split a path on `.`, so `[element_uid=core.bst]`
became `["...[element_uid=core", "bst]", ...]` — nonsense. It never bit
because no path in `_CLAIMS` uses a selector with a dotted value
(`violations[type=build_failed]` has none), and this item emits nothing
*but* dotted element uids. Both resolvers now scan instead of split, and
a fixture with `layer07/mod084.bst` in the selector holds it.

The two implementations of one grammar are checked against each other
rather than trusted: the page walks each path it emits and reports what
it found, and the guard compares that against `provenance.resolve`
walking the same path. A divergence is a failing test, not a wrong
number in a fold.

```text
9 guards, all green on the golden run: each action gets a block, every
shown value resolves to the field it cites, both resolvers agree on
every path, the rule comes from the record, an element no source knows
gets no block, a dotted uid resolves, the history line needs a store,
and the export carries the renderer.
```

**Mutations verified red and reverted (6):** a path naming a field the
payload does not carry; `data-raw` carrying the rendered figure instead
of the published one; the page wording the reason itself; the resolver
splitting on `.`; a block with nothing to say rendering anyway; the
history drawn without a store.

**One guard had to be scoped, not the code.** `UX-207`'s
"every number in the panel is a published field" collected every
`data-field` under the panel and looked each up as a `headline.` key.
The fold's rows are paths, not headline keys, so that guard now walks
past the fold — and the fold's own rows are checked against their own
paths here, which is the stronger check of the two.

**Deviation from the Required Fix:** none. The history delta is the
existing `UX-226` block embedded rather than a delta recomputed here —
that block already refuses to state a percentage, "two points from two
different builds are not a rate", and re-deriving one inside a fold
about traceability would have been the wrong lesson twice.

Full suite: `3036 passed, 3 skipped`.
