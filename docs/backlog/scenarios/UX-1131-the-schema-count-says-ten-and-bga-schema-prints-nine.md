# UX-1131: `docs/README.md` counts ten printable contracts and `bga --schema` prints nine

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-1078 | **Found by:** round 149's bookkeeping ledger, promoted at round 152's sweep | **Serves:** R8 | **Topic:** contracts | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`docs/README.md:97` says "The other ten each have a command that
prints"; `bga --schema tail/v1` refuses, so nine do.
`test_a_counted_figure_is_derived.py` holds the sentence to
`contracts.printable()`, which includes `tail/v1` although its
docstring says "the subset bga --schema can print".

```text
python3 -c "from bga.cli import _SCHEMA_BY_COMMAND as C,_SCHEMA_BY_FLAG as F; p=set(C.values()); [p.update(n for _,n in v) for v in F.values()]; print(len(p))"
```

## Required Fix

`contracts.printable()` returns exactly what `bga --schema` prints
(derived from the CLI's schema maps, or excluding file-written-only
contracts), and the README sentence reads the derived count.

## Out of Scope

Making `tail/v1` printable.

## Acceptance Test

`printable()` equals the set `bga --schema NAME` accepts, every member
printing and every non-member refused; the README count matches. Mutation:
add `tail/v1` back to `printable()`; the guard reddens.

## Outcome
