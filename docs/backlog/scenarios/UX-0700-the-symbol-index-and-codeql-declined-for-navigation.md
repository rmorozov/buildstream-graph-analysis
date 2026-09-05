# UX-700: the symbol index — and CodeQL declined for navigation

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-499 (the orient recipes), UX-687 (the impact tool, which reads it) | **Serves:** the session at the start of a task, which today spends five greps and their raw lines to learn who calls what | **Topic:** guards | **Shape:** bounded

## Motivation

The `orient` skill answers "where is it defined, who calls it, who
imports this module" with greps that return raw lines the session
then reads — round-90's ledger puts a whole-document orientation at
100–180k tokens. The brief proposes CodeQL for this. Measured: no
`codeql` on PATH; a database build over 62,440 Python and 12,906 JS
lines is minutes and a 500 MB CLI; the questions above are
symbol-shaped and `grep -w` answers each in milliseconds. What grep
cannot answer — does a log field reach `subprocess` in the 6,960-line
tracer, does it reach the page — is data-flow, a gate question
(`UX-698`), not a navigation one.

## Required Fix

`tools/dev_symbols.py`, `ast` only: `def <name>` (definitions, with
file:line and enclosing class), `callers <name>` (direct call sites),
`importers <module>`, `fanin`/`fanout <module>`, `dead` (exports no
module references — Python via `ast`, the viewer via `dev_js_deps`'s
declarations). Output a table, `--json` for `UX-687`. The `orient`
skill's five recipes become one command each, and the skill's cost
row in the run ledger is re-measured on the next round.

## Out of Scope

- Transitive callers and data-flow — CodeQL's job, at the gate.
- A persistent index or a daemon — the AST walk over `bga/` and
  `tools/` is under two seconds; caching would be a second source of
  truth.

## Acceptance Test

`dev_symbols.py callers compute_confidence` lists
`bga/analyzer.py`'s call sites and nothing in a string literal
(`UX-403`'s shape); `dead --js` lists the five exports named above;
mutation: rename a caller — the row moves; a call inside a docstring —
not listed.
