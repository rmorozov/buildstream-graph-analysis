# UX-979: §7a cites a guard class a rename retired, and no guard resolves the part after `::`

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-744, UX-749 | **Blocks:** — | **Found by:** architecture review 26 (2026-09-23) — the fixing guide's round-closing step 5 names `TestEveryRoundDocumentPricesItsAgents`, which `UX-744` renamed | **Serves:** a session closing a round from §7a, which is sent to the guard by name | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

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

## Outcome
