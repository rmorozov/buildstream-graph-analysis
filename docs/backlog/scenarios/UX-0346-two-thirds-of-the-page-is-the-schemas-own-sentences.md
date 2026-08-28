# UX-346: two thirds of the page is the schema's own sentences

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-220 (the numbers that need a sentence have one), UX-317 (apparatus in its place) | **Serves:** every reader of the report | **Topic:** viewer

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
