# UX-977: the coverage section states the surface twice, and the guard reads one of them

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-909 | **Blocks:** — | **Found by:** architecture review 26 (2026-09-23) — `UX-899` moved `cli.md:1085` from 562 to 563 because a guard made it, and `:1099` fourteen lines below still says 562 | **Serves:** whoever reads `cli.md`'s coverage section to learn how far the documentation guard reaches | **Topic:** guards | **Area:** unassigned | **Shape:** mechanical

## Motivation

`UX-909`'s Outcome: "both figures in it (`562 keys`, `0 undocumented
keys`) are read off the walk and the register rather than typed, so the
next widening moves the guide or reddens." The section carries the
surface count twice:

```text
$ grep -n "562 above\|563 keys" docs/guides/cli.md
1085:its own nine buckets are not. The surface is **563 keys** today, and
1099:  walked, against the 562 above. `--schema` stays the complete list,
$ python3 -c "import sys; sys.path.insert(0,'tests/unit'); \
    import test_the_documents_keep_up_with_the_contracts as t; \
    print(len(t._consumer_surface()))"
563
```

`test_the_guide_states_the_reach_it_actually_has` asserts
`f"**{len(surface)} keys**" in body` - the bold copy. `UX-899` added a
key, the clause reddened, and the bold copy moved:

```text
$ git show 7e788bcb -- docs/guides/cli.md | grep "^[-+].*56[23]"
-its own nine buckets are not. The surface is **562 keys** today, and
+its own nine buckets are not. The surface is **563 keys** today, and
```

The unbolded copy is outside the clause's population, and it is green
today:

```text
$ python -m pytest tests/unit/test_the_documents_keep_up_with_the_contracts.py -q \
    -k reach_it_actually_has
1 passed, 28 deselected
```

Review 19's shape, a sentence inside a guarded document and outside its
guard's population, and the second time `UX-909`'s section has shown
it. The `514 distinct keys` in the same sentence is a third figure no
clause reads; this row did not re-derive it.

## Required Fix

One statement of the surface in the section of `docs/guides/cli.md`.
Either `:1099` refers back ("against the surface above") or the clause
in `tests/unit/test_the_documents_keep_up_with_the_contracts.py` asserts
every figure the section states, `514` included, from the walk that
produces it.

## Out of Scope

The population itself. Any other section of `cli.md`.

## Acceptance Test

`grep -c "562" docs/guides/cli.md` prints 0. A mutation that changes the
figure `:1099` states (or, if it now refers back, re-adds a literal
there) reddens a clause of
`test_the_documents_keep_up_with_the_contracts.py`, and the clause is
green on the fixed tree.

## Outcome
