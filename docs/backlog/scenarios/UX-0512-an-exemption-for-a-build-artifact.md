# UX-512: a guard is red on any tree whose `__pycache__` was cleared

**Priority:** Low | **Status:** 🔴 Not Started | **Found by:** round 75, an `implementer` track following `UX-508`'s own advice | **Serves:** the round that clears bytecode before a same-length mutation and reads the result as a flake | **Topic:** guards

## Motivation

`tests/unit/test_the_context_map_is_the_tree.py` exempts
`tests/__pycache__` at line 42 and asserts at line 141 that every
exemption names a path that exists. Those two are only compatible while
the bytecode happens to be there:

```console
$ rm -rf tests/__pycache__
$ PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
    .../test_the_exemption_list_names_only_real_paths -q -p no:cacheprovider
E   AssertionError: exemption(s) for no such path: ['tests/__pycache__']
1 failed in 0.06s
```

Clearing `__pycache__` is exactly what `UX-508`'s trap tells a round to
do before a same-length mutation, and what the `implementer` brief
repeats. So the guard is red precisely when the falsification procedure
is being followed — and it presented as a flake in one `make test-small`
before it was reproduced deterministically.

An exemption for a build artifact is not the same kind of thing as an
exemption for a source path, and the existence check cannot tell them
apart.

## Required Fix

- The two kinds of exemption are distinguished, or the artifact is
  exempted by pattern rather than by a path that must exist.
- The clause that made this look like a flake — a guard whose verdict
  depends on whether bytecode was written — is stated in the file, so a
  later round does not rediscover it as noise.

## Out of Scope

- The rest of the context map. Every other exemption names a
  source path that a clone really has, so the existence check is
  the right one for them and only the artifact row is wrong.

## Acceptance Test

The file green with `tests/__pycache__` absent and green with it
present, both pasted.

## Outcome

_Not started._
