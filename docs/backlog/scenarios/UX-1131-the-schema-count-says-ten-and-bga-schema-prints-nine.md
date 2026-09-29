# UX-1131: `docs/README.md` counts ten printable contracts and `bga --schema` prints nine

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-1078 | **Found by:** round 149's bookkeeping ledger, promoted at round 152's sweep | **Serves:** R8 | **Topic:** contracts | **Area:** bga | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_printable_is_what_bga_schema_prints.py`

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

## Decision

- **Route:** `contracts.printable()` derives from `cli._SCHEMA_BY_COMMAND` and `_SCHEMA_BY_FLAG` (lazy import inside the function, no cycle: cli already imports contracts). `tail/v1` becomes unprintable, so `unprintable()` grows by one and every count read from it moves.
- **Rejected:** excluding `tail/v1` by name (a second list that ages).
- **Files:** `bga/contracts.py`; `docs/README.md` (ten -> nine), `docs/design/architecture.md` and `docs/spec/specification.md` Part 32 (six -> seven), `docs/guides/cli.md` (586 -> 585 keys); `tests/unit/test_the_contract_inventory_is_derived.py` (list gains `tail/v1`); the guard.
- **Guard:** that test: every real subcommand and flag asked `--schema`; printed ids equal `printable()`, every other schema name refused.
- **Mutation:** `printable()` returns the set plus `tail/v1`.
- **Class:** contracts

## Out of Scope

Making `tail/v1` printable.

## Acceptance Test

`printable()` equals the set `bga --schema NAME` accepts, every member
printing and every non-member refused; the README count matches. Mutation:
add `tail/v1` back to `printable()`; the guard reddens.

## Outcome

Gap measured: `contracts.printable()` had 10 members, `bga --schema` printed 9 (`tail/v1` refused); `docs/README.md` said ten.

Close measured: `python3 -m pytest -q -n 2` on the guard plus `test_a_counted_figure_is_derived`, `test_the_contract_inventory_is_derived`, `test_the_documents_keep_up_with_the_contracts`, `test_every_emitted_contract_is_answerable`: green.

| mutation | red | count |
|---|---|---|
| `printable()` returns the set plus `tail/v1` | both guard tests | 2 failed |

