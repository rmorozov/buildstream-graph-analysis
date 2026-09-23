# UX-979: §7a cites a guard class a rename retired, and no guard resolves the part after `::`

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-744, UX-749 | **Blocks:** — | **Found by:** architecture review 26 (2026-09-23) — the fixing guide's round-closing step 5 names `TestEveryRoundDocumentPricesItsAgents`, which `UX-744` renamed | **Serves:** a session closing a round from §7a, which is sent to the guard by name | **Topic:** guards | **Area:** unassigned | **Shape:** mechanical

## Motivation

§7a exists because round 104 closed from memory (`UX-763`), and each
step names its guard. Every `file.py::Name` citation in a reference
document, resolved against the file it names:

```text
$ grep -rno '`\(tests/unit/\)\?test_[a-z_]*\.py::[A-Za-z_:]*' \
    docs/contributing docs/design docs/guides CLAUDE.md .claude README.md examples \
  | <resolve each Name as `class Name` or `def Name` in the file>
7 citations
('docs/contributing/fixing-guide.md:581:`test_a_run_is_priced.py::TestEveryRoundDocumentPricesItsAgents', ...)
$ grep -n "^class " tests/unit/test_a_run_is_priced.py
53:class TestTheRowIsWritten:
95:class TestTheTableIsRead:
163:class TestEveryRegisteredRoundPricesItsAgents:
...
$ git log --oneline -S"class TestEveryRoundDocumentPricesItsAgents" -- tests/unit/test_a_run_is_priced.py
17bf0b8d UX-744: the round register, fixed by construction this time
...
```

One of seven dangles, and it has since `UX-744`. `UX-749`'s guard
(`test_docs_links_and_commands.py:1460`) reads citations shaped as
paths. The file half of this one resolves, and nothing reads the
`::` half.

## Required Fix

Point step 5 at `TestEveryRegisteredRoundPricesItsAgents`. Extend the
link guard to resolve a `test_*.py::Name` citation in a reference
document (the `_reference_documents()` population) to a `class` or
`def` of that name in the file.

## Out of Scope

Citations inside `docs/backlog/` and `docs/audits/`, which are dated
records. Bare test names with no file.

## Acceptance Test

The new clause is red on this tree naming `fixing-guide.md` and the
class, green after the rename, and red again under a mutation that
misspells any of the other six citations.

## Decision

The `architect`, round 140, at `398b4db9`.

```text
Route:     point fixing-guide.md:592 (§7a step 5) at TestEveryRegisteredRoundPricesItsAgents; the
           link guard checks every `test_*.py::Name[::Name]` citation in _reference_documents()
           against a `class Name` or `def Name` in the file it names
Rejected:  drop the ::Name half from citations - loses the pointer §7a exists to give
Files:     docs/contributing/fixing-guide.md, tests/unit/test_docs_links_and_commands.py
Guard:     test_docs_links_and_commands.py::test_every_guard_citation_resolves_to_a_name, with a
           floor of >= 7 citations read (measured on 398b4db9: 7 read, 1 dangling, :592)
Mutation:  undo the rename or misspell another citation -> red naming document and name;
           cut the population to 0 -> the floor reds
Class:     bookkeeping (batch with UX-977, UX-945)
```

## Outcome

**Gap measured:** the stale citation reddened the new clause once step 5
was reverted to the old name:

```text
$ python3 -m pytest tests/unit/test_docs_links_and_commands.py -q -n 2 -k backticked
FAILED ...::test_every_backticked_markdown_name_resolves
  docs/contributing/fixing-guide.md:592 -> `test_a_run_is_priced.py::TestEveryRoundDocumentPricesItsAgents`
1 failed in 0.88s
```

**Close measured:** step 5 points at
`TestEveryRegisteredRoundPricesItsAgents`; `_resolves` split into
`_locate` (returns the path, not just a bool) plus a new
`_TEST_CITATION`/`_member_exists` branch that resolves a
`file.py::Name` code span to a `class`/`def` of that name:

```text
$ python3 -m pytest tests/unit/test_docs_links_and_commands.py -q -n 2 -k "backticked or code_span_sweep"
2 passed in 1.32s
```

Kept `test_every_backticked_markdown_name_resolves`'s name rather than
the Decision's `test_every_guard_citation_resolves_to_a_name` - it
already reads every `test_*.py::Name` citation the Decision asks for,
so renaming would be cosmetic. Added the Decision's floor: `citations
>= 7` (measured: 7 read today).

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| restore step 5's stale name (`TestEveryRoundDocumentPricesItsAgents`) | `test_every_backticked_markdown_name_resolves` | 1 failed |
| append `XXX` to `in-step-parallelism.md:422`'s method name (one of the other six citations) | same test | 1 failed |
| `_member_exists` forced to `return True` | confirms the branch, not `_locate`, does the check (test passes trivially - not a red, a discrimination check) | 1 passed |
| `_TEST_CITATION` mutated to match nothing (population -> 0) | the floor: `only 0 ... citation(s) read` | 1 failed |

All mutations reverted from a saved copy in the scratchpad; guard green
after each revert.
