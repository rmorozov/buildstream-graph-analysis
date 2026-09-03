# UX-599: a guard pins a contract version by typing it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-584 (the figures that derive), UX-233 (the contracts guard) | **Serves:** the next contract bump, which will pass a guard that should have caught it | **Topic:** guards

## Motivation

`UX-584` made the process documents derive their versions from
`bga/schemas.py`. One literal survived, in a guard:

```text
tests/unit/test_docs_links_and_commands.py:808   assert "analyze/v2" in guide
bga/schemas.py                                    analyze/v5, compare/v2, blast/v2
```

The clause is green because §3.7 keeps `analyze/v2` as *history* — the
sentence is about what the version was. But the guard asserts the
literal rather than reading the registry, so it holds a string and not
a fact: bump `analyze` again and this clause says nothing, while the
sentence it guards may or may not still be true.

## Required Fix

The clause reads `bga/schemas.py` for the version it asserts, the way
`UX-584`'s derived clauses do, and states in one line whether it is
checking the current version or a historical one.

## Out of Scope

- The §3.7 history sentence itself — declined: `UX-584` dated it and it is correct.

## Acceptance Test

Mutation: bump a contract in `bga/schemas.py` — the clause reds or
says why the literal is historical; today it does neither.
