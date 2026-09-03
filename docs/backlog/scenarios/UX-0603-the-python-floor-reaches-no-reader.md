# UX-603: the Python floor reaches no reader

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-588 (the floor's guard) | **Serves:** the contributor deciding whether their interpreter will do | **Topic:** docs

## Motivation

Architecture review 14, item 4 — what shipped that no document names:

```text
$ grep requires-python pyproject.toml                          ">=3.9"
$ ci.yml matrix                                                3.9, 3.10, 3.11, 3.12
$ grep 'Python 3\|python3\.[0-9]\|requires-python' <36 front-of-house .md>
0 hits
```

`UX-588` guards the floor against the tree — no PEP 604 union may
reach a 3.9 runtime — so the constraint is enforced and invisible. A
contributor on 3.8 learns it from a `pip` error, and one writing
`str | None` learns it from a guard rather than from a sentence.

## Required Fix

The floor is stated where a contributor reads before writing code —
the README's install section and the fixing guide — derived from
`pyproject.toml` rather than typed, so it cannot drift from the
matrix that enforces it.

## Out of Scope

- Moving the floor itself.

## Acceptance Test

Mutation: raise `requires-python` and leave the prose — red naming
both figures.
