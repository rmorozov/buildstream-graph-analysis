# UX-574: "invalid arguments" exit 2, which the table gives to ingestion

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-186 (the refusal grammar and its codes) | **Serves:** the CI owner branching on an exit code | **Topic:** cli

## Motivation

```text
docs/guides/cli.md:2046   "1: General error (e.g., invalid arguments…)"
$ bga analyze --bogus tests/fixtures/macro_micro/run; echo $?
usage: … error: unrecognized arguments: --bogus
2
cli.md:2042-2066          2 = ingestion failure
```

argparse exits 2, and the table reserves 2 for a run that could not
be read — so a CI script that branches on 2 treats a typo as a
corrupt capture. The rest of the table (3-7, baseline 6, snapshot 2
and 130) was checked against `bga/cli.py:659-684` and is true.

## Required Fix

Either the parser's usage error is mapped to 1 (a parser subclass,
one line) or the table says 2 for both and names the difference by
stderr shape — a product decision; the table then derives from the
code (`bga/exceptions.py` codes listed by a guard against the table's
rows).

## Out of Scope

- The other codes — verified against `bga/cli.py:659-684` this round; nothing to change.

## Acceptance Test

`bga analyze --bogus RUN; echo $?` prints the code the table says;
mutation: change one code in the table — the derivation guard reds.
