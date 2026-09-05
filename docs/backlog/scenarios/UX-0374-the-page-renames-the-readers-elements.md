# UX-374: the page renames the reader's elements and programs

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-201 (the schema says what things are), UX-326 (the tool's own sentences are contracts) | **Serves:** anyone searching the page for a name they know | **Topic:** viewer | **Area:** bga/viewer

## Motivation

`format.js`'s `title()` capitalises the first character of every key:

```javascript
return named.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
```

That is right for a *schema* key — `element_durations` should read
"Element durations". It is applied to map keys that are **data**, and
those are the reader's own identifiers. Measured on
`tests/fixtures/macro_micro`, on the committed tree:

```text
published                          rendered
codegen.bst|BUILD|BUILD|0          Codegen.bst|BUILD|BUILD|0
cmake                              Cmake
cc1plus                            Cc1plus
```

Every element-keyed map on the page is affected —
`wall_clock_share_us`, `element_durations`, `slack`,
`downstream_count` — and `wall_clock_share_us` alone is 82% of the
page at 1,202 elements (`UX-367`). A reader who searches the page for
`cmake` or for `core.bst` does not find the row; a reader who copies
one pastes a name their project does not have.

This is `UX-326`'s rule — the tool's sentences are contracts — applied
to the one class of string the tool must never author: a name it was
given.

Found while closing `UX-370`, which added `by_binary` and met the same
renderer. It is older than that item and wider, so it is filed rather
than fixed inside it.

## Required Fix

A key that is data is rendered as published. The schema already knows
which those are: a map declared with `additionalProperties` is keyed by
data, and a `properties` block is keyed by contract. That distinction is
the predicate, so no new hint is needed.

- `title()` takes whether the key is a declared property or a data key,
  and humanises only the first.
- The element-keyed maps and `by_binary` render their keys verbatim.

## Falsification

Export `macro_micro`, boot it, and assert that every key of
`wall_clock_share_us` and `by_binary` appears on the page exactly as
the payload spells it. Today none of them do.

The other direction, so the fix is not "stop humanising": a *schema*
key still reads as English — `element_durations` renders "Element
durations" and not `element_durations`.

## Out of Scope

Table cells, which already render published values verbatim
(`UX-277`). This is the map renderer's key column and the pair list.

## Outcome

Round 59. `title()` takes a third argument and `format.js` gained the
predicate that decides it.

**Measured either side**, on `macro_micro`, exported and booted, every
chapter and fold open, comparing each label against the `data-key` the
same node has always carried:

```text
                     data keys   renamed   contract keys   humanised
before                      22        22             241         241
after                       22         0             241         241
```

The Falsification's two directions, and both are guarded: the reader's
own names survive, and the contract's keys still read as English. The
cheap wrong fix — stop humanising — fails four clauses.

**No new hint, as the filing said.** `childNode` has resolved a
declared member through `properties` and a data-keyed map's value
through `additionalProperties` since `UX-343`, so `dataKeyed(node, key)`
reads the same node and returns which branch applies. `title` returns
before *all three* of its transformations rather than skipping the
capital: `a_b.bst` is not "A b.bst", and a program called `x_us` would
otherwise lose its tail to the unit trim.

**Absent a schema it is false**, and that is a decision rather than an
oversight: an undeclared node says nothing about its keys, and guessing
"data" would strip the English off contract keys instead. Mutation M8'
is that branch.

The item named the map renderer's key column and the pair list. The
pair list is `describedTerm`; the second site is `inlineObject`, which
labels a small map's keys through the same call — see the falsification
note below for why it needed a clause of its own.

**`structured.js` came to 1,504 lines** against `UX-337`'s 1,500
ceiling on the way. The commentary there is now one line and the
reasoning lives in `format.js` beside the rule, which is where a reader
looking for it would go. Worth recording: that module has two lines of
headroom, and the next viewer item will meet the same wall.

Page 267,286 → 267,830 B. Every export bound already permitted it, so
nothing was restated.

### Falsification run

Eight mutations against the committed tree. Seven caught, one rejected:

| # | Mutation | Caught by |
| --- | --- | --- |
| M1 | `title` humanises a published key again — the defect | 3 clauses, both fixtures |
| M2 | the fix becomes "stop humanising" | 5 clauses |
| M3 | a declared property counts as data | `test_a_declared_property_wins_over_additional_ones` |
| M4 | the predicate never fires | 4 clauses |
| M5 | the pair list stops asking the schema | both browser clauses |
| M6 | the inline object stops asking the schema | `TestTheInlineObjectAsksToo` |
| M7 | the pair key stops publishing `data-key` | `test_a_small_data_keyed_map_keeps_its_names` |
| M8′ | an absent schema is guessed to be data | `test_no_schema_says_nothing` |

**M6 passed first, and that is the finding.** No committed fixture
publishes a data-keyed map of four or fewer scalars, which is what
`shapes.js` draws inline, so the second call site was asserted against
nothing while every browser clause stayed green. `TestTheInlineObject
AsksToo` drives `renderStructured` through `tests/viewer.mjs` with that
shape rather than waiting for a capture to produce one. This is the
same gap `UX-368` spent four rounds inside and `UX-372`'s own M6 hit —
three rounds running, so it is worth saying plainly: **a call site no
fixture reaches needs a clause that builds the shape.**

**M8 was rejected rather than counted.** It removed `dataKeyed`'s
`if (node.items) return false;` and nothing failed — correctly, because
an array node carries no `additionalProperties`, so the line is
behaviour-preserving for every shape the schema produces. It is kept
for the same reason `childNode` has three branches: without it the
function's correctness rests on an unstated premise about JSON Schema.
M8′ replaced it with a mutation that discriminates.

**M7 failed as a `KeyError` before the clause named its precondition**,
which is UX-373's M5 one item later. The clause checks `data-key` is
there before comparing against it.

The new guard is tiered on landing — 4.2s, medium — which is what
`tiers.py`'s note asks for after two rounds of forgetting.
