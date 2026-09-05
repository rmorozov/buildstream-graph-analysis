# UX-718: the census omits the guard its own docstring names

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-522 (the census set), UX-645 (the census floor) | **Serves:** anyone whose inner loop is `make test-touching` | **Topic:** guards | **Shape:** mechanical | **Area:** tools

## Motivation

`census_set()`'s docstring names three archetypes of the class, and
the list is missing the middle one:

```text
tools/dev_touching.py:86-88
    A census guard's subject is the **tree** - the register cap over
    every task file, the skip census over every guard, the context map
    over every module - so it names none of them and no diff can point
    at it.

tests/tiers.py:117-129   CENSUS, 11 entries
    test_the_register_is_terse.py          ✓ the register cap
    test_every_skip_reason_is_declared.py  ✓ the skip census
    test_the_context_map_is_the_tree.py    ✗ absent
```

Measured, not argued: adding `bga/utilisation/envelope.py` in `44d211f`
passed `make test-touching` at 104 files and **failed CI on all four
`test` jobs** —

```text
FAILURE tests.unit.test_the_context_map_is_the_tree.TestTheMapNamesTheTree
        ::test_every_module_is_on_the_map
        module(s) the context map does not mention:
        ['bga/utilisation/envelope.py']
```

A new module is exactly the diff that cannot name this guard: the guard
mentions no module, and the module is not yet in the map it checks. So
the one change that reddens it is the one change the selector cannot
select — `UX-522`'s own argument, on a file `UX-522` left out.

## Required Fix

`test_the_context_map_is_the_tree.py` joins `tests/tiers.py`'s `CENSUS`.
`test_the_selector_carries_the_census.py` derives the set rather than
auditing a typed list, so a fourth tree-walking guard added later is
not a fourth round of this.

## Out of Scope

- The other 480 guards. This item adds the one its own docstring
  names and closes the derivation gap that let it be missed; a sweep
  for further census candidates is a separate measurement.

## Acceptance Test

`python3 tools/dev_touching.py --why tests/unit/test_the_context_map_is_the_tree.py`
reports `census` on a diff naming no module; `git rm` a `bga/` module
and `make test-touching` reds without the module being named anywhere
in the diff. Mutation: drop the entry again — the derivation guard reds
rather than the list silently shrinking.
