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

- Moving the floor itself — declined: `UX-588` measured what the
  floor costs and 3.9 is still what the matrix runs; this item is
  about saying so, not about changing it.

## Acceptance Test

Mutation: raise `requires-python` and leave the prose — red naming
both figures.

## Outcome (round 84, 2026-09-03) — 🔴 guard landed, row not moved

**Premise: holds.** Re-measured at `8f51a26`, with the front-of-house
population spelled out (tracked `*.md` less `docs/backlog/`,
`docs/spec/`, `docs/audits/`):

```text
$ grep -n requires-python pyproject.toml
11:requires-python = ">=3.9"
$ grep -n python-version .github/workflows/ci.yml | head -1
25:        python-version: ["3.9", "3.10", "3.11", "3.12"]
$ git ls-files '*.md' | grep -vE '^docs/(backlog|spec|audits)/' | wc -l
33
$ grep -nE 'Python 3|python3\.[0-9]|requires-python|3\.9' $(that list)
0 hits
```

33, not the Motivation's 36 - the difference is which directories count
as front of house; the hit count is 0 either way.

**Close.** `README.md`'s Install section states it, and
`tests/unit/test_the_floor_is_stated_where_it_is_read.py` reads both
figures rather than either being typed: the floor from `pyproject.toml`,
the matrix from `.github/workflows/ci.yml`, plus the tie between them -
`requires-python` is only enforced because the *lowest* matrix job is
that version.

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_floor_is_stated_where_it_is_read.py \
      tests/unit/test_the_python_floor_is_a_guard.py -q
7 passed in 1.64s
$ make lint                All checks passed!
$ wc -l README.md          323   (unchanged; the sentence extends a wrapped line)
```

**Mutations.**

| mutation | anchor confirmed | red | count |
|---|---|---|---|
| `requires-python = ">=3.10"`, prose left | `11:requires-python = ">=3.10"` | matrix tie + `…states ['3.9']` | 2 failed, 2 passed |
| README says `Python 3.10` | line 21 | `…declares >=3.9, and README.md states ['3.10']` | 1 failed, 3 passed |
| `, and CI runs 3.9-3.12` removed | `grep -c` -> 0 | `…does not state that range` | 1 failed, 3 passed |
| matrix drops `"3.9"` | `python-version: ["3.10", …]` | tie + range | 2 failed, 2 passed |
| `_floor() == "3.9"` typed in the guard | line 100 | `…writes the floor 3.9 as a literal` | 1 failed, 3 passed |
| `Python` -> `Pythonn` in the reader | line 47 | `…states no Python version at all` | 2 failed, 2 passed |

Every guard discriminated; none was vacuous.

**Deviation from the Required Fix.** The fixing guide does not state
the floor. `docs/contributing/fixing-guide.md` is 41,439 B after
`UX-590`'s row; `UX-584` derives `round(B/1024)` into a sentence in
*both* the guide and `docs/contributing/rules.md`, and 41,472 B is
where that figure becomes 41. That leaves 33 B, against ~44 B for the
shortest sentence naming the floor and its source - and `rules.md` is
another track's file this round, so the coupled figure cannot move
with it. Filed as a follow-on row rather than shipped with 2 B of
margin.
