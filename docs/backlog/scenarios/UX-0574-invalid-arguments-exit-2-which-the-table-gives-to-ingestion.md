# UX-574: "invalid arguments" exit 2, which the table gives to ingestion

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-186 (the refusal grammar and its codes) | **Serves:** the CI owner branching on an exit code | **Topic:** cli | **Area:** bga

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

## Outcome (round 83, 2026-09-03) — 🟢 Done

**The decision: map the usage error to 1.** `2` is the only code a CI
job can act on without parsing stderr, and the table already promised
`1` for invalid arguments — mapping is one subclass, while "2 for both,
told apart by stderr shape" asks every consumer to grep English.

The gap, before the change (`bga` on `PATH`, worktree on `PYTHONPATH`):

```text
$ bga analyze --bogus tests/fixtures/macro_micro/run; echo $?
usage: bga [-h] [--version] COMMAND ...
bga: error: unrecognized arguments: --bogus
2
```

After — the Acceptance Test, verbatim:

```text
$ bga analyze --bogus tests/fixtures/macro_micro/run; echo $?
usage: bga [-h] [--version] COMMAND ...
bga: error: unrecognized arguments: --bogus
1
```

Every argparse refusal path, and the two that must stay `0`:

```text
bga nosuchcommand              invalid choice          1
bga analyze                    required: directory     1
bga analyze --format           expected one argument   1
bga --version | --help | bga                           0
```

`_CompactSubParser` now inherits `_UsageErrorParser`, which is why the
subparsers' three errors moved too and not only the top parser's.

The derivation: `bga/exceptions.py` grew `EXIT_CODES` (9 entries,
0-7 and 130) and `bga/cli.py`'s four `EXIT_CODE_*` constants are now
assignments from it rather than literals. `docs/guides/cli.md`'s Exit
Codes list is read row-by-row and compared to `set(EXIT_CODES.values())`.

**Mutations verified red and reverted (3):**

| mutation | reddened | run |
|---|---|---|
| `cli.md` row `` - `3`: `` → `` - `9`: `` | `test_the_listed_codes_are_the_registrys` — `Extra items in the left set: 9` | 1 failed, 2 passed |
| `EXIT_CODE_MISMATCHED_RUNS = EXIT_MISMATCHED_RUNS` → `= 9` | `test_the_cli_constants_are_the_registrys` — `assert 9 == 6` | 1 failed, 2 passed |
| `self.exit(EXIT_GENERAL, …)` → `self.exit(2, …)` | `test_a_bad_flag_exits_the_code_the_row_for_invalid_arguments_carries` — `assert 2 == 1` | 1 failed, 2 passed |

Each landed under an `assert … in t` and each reddened exactly one
guard. Reverted, `3 passed in 0.43s`.

```text
$ make test-touching
115 file(s) selected · 2153 passed, 71 skipped in 68.92s (0:01:08)
$ make lint
All checks passed!
```

**Deviation.** A fourth guard was written and dropped before commit:
`EXIT_GENERAL != EXIT_INGESTION` reads two constants and restates the
motivation, and the only mutation that reddens it also reddens the set
comparison — it did not discriminate.

`EXIT_INTERRUPTED = 130` is in the registry so the table's row derives,
but nothing imports it yet: `tools/bga_view.py:1935` and
`tools/bga_snapshot.py:520` still write the literal. Rewiring the tools
was not in this item's surfaces.
