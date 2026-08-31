# UX-408: `serialized_pairs` is described as its own opposite

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-341 (the declared-description discipline this slipped past) | **Serves:** anyone reading the batching section on the page | **Topic:** contracts

## Motivation

The computation (`bga/structural/batching.py:96-101`) collects pairs
that are **not** independent — same dependency chain, kept so a
reader can see *why* two elements weren't batched:

```python
serialized_pairs: List[Tuple[str, str]] = [
    (a, b) ... if not _are_independent(a, b, reachable_downstream)
]
```

The terminal prints them honestly: "Serialized (same dependency
chain, not independently batchable)". The schema description the
page renders (`bga/schemas.py:1827-1829`) says the opposite:

```text
"Pairs that ran one after the other with nothing forcing the order."
```

A page reader is told these ten pairs are unforced serialization —
free wins — when the computation selected them *because* the order
is forced. The viewer and the terminal disagree about the same rows,
at the caption level, which breaks the page's own
never-disagree property and would send a reader to "fix" pairs the
tool knows cannot be batched.

## Required Fix

Correct the schema description to what the computation does (a
description fix — no version bump under `UX-190`), aligned with the
terminal's wording. Then the guard: the round-52/`UX-345` class
("a declared quantity has to match the value it declares") gets a
sibling for *sentences* — where a schema description and a terminal
caption describe the same key, a table pins each pair, so the next
caption cannot invert alone. If a full sentence-census is too blunt,
the minimal version pins this one key with a source-of-truth
comment beside both strings.

## Out of Scope

- Renaming `serialized_pairs` itself — the key is accurate; only
  its published sentence lies.
- The batching algorithm — the walk verified its output against the
  graph; the numbers are right.

## Acceptance Test

- The page's batching section caption states the pairs are on the
  same chain and not independently batchable; terminal and page
  sentences agree.
- Falsification: restore the "nothing forcing the order" sentence —
  the caption guard goes RED.

## Outcome (round 65, 2026-08-29) — 🟢 Done

### The two sentences, before and after

```text
before  page      "Pairs that ran one after the other with nothing
                   forcing the order."
        terminal  "Serialized (same dependency chain, not independently
                   batchable)"

after   both      "Pairs on the same dependency chain, so not
                   independently batchable."
```

Printed by `bga analyze tests/fixtures/macro_micro/run`:

```text
  Serialized (pairs on the same dependency chain, so not independently
  batchable): core.bst -> lib-b.bst; core.bst -> lib-d.bst; ...
```

### One string, not two held equal

The Required Fix offers a table pinning each (schema description,
terminal caption) pair. **Declined, for a stronger shape**: two copies
a guard holds equal can still both be edited in one commit, and this
pair drifted for as long as it existed. The sentence is now
`schemas.SERIALIZED_PAIRS_MEANING`, imported by the schema and by
`bga/report/text.py`, so there is no second copy to drift. It is
deliberately short enough to work as a terminal caption *and* a page
description, which is what keeps it one string rather than two that
happen to agree today.

What is left to guard is the part no equality between two copies could
ever have caught: **that the sentence still describes what the code
selects for.** The third clause reads `batching.py`'s filter itself and
fails if it stops being `if not _are_independent(...)`.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| A1 | the constant restored to the old, inverted sentence | the says-the-order-is-forced clause (1 failed, 3 passed) |
| A2 | the terminal keeps a caption of its own again | the one-string clause and the rendered-line clause (2 failed, 2 passed) |
| A3 | `batching.py`'s filter inverted to select the *independent* pairs | the premise clause and the rendered-line clause (2 failed, 2 passed) |

A3 is the one the pinned-pair shape could not have: with two strings
held equal to each other, inverting the computation leaves both green.

### Deviation from the Required Fix

**One, and it is the shape.** A pinned table of (description, caption)
pairs is replaced by one imported constant plus a clause over the
computation. The Required Fix's own fallback - "the minimal version pins
this one key with a source-of-truth comment beside both strings" - is
what this is, with the comment replaced by the string itself.

### Verification

```text
pytest tests/unit/test_one_sentence_for_one_key.py             4 passed
make lint                                                      clean
```
