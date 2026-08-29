# UX-408: `serialized_pairs` is described as its own opposite

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-341 (the declared-description discipline this slipped past) | **Serves:** anyone reading the batching section on the page | **Topic:** contracts

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
