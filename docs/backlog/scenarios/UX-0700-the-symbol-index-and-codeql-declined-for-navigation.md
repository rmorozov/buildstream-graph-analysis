# UX-700: the symbol index — and CodeQL declined for navigation

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-499 (the orient recipes), UX-687 (the impact tool, which reads it) | **Serves:** the session at the start of a task, which today spends five greps and their raw lines to learn who calls what | **Topic:** guards | **Area:** tools | **Shape:** bounded

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

## Outcome

**The gap, measured** — the orient table's five lookups, run for
`compute_confidence`, line counts today:

```text
grep -rn compute_confidence bga/findings.py bga/provenance.py   0
grep -n  compute_confidence bga/schemas.py                      0
grep -n  compute_confidence bga/viewer/chapters.js bga/viewer/*.js  0
grep -ln compute_confidence tests/unit/*.py                     8 files
git grep -l compute_confidence docs/backlog/scenarios/          5 files
```

Five separate invocations, none of them the one that mattered — the
real answer (`bga/analyzer.py:1862`, inside a docstring twice at
1854/1858, six raw grep hits total) needed a sixth, manual read.

**The close, measured**:

```text
$ python3 tools/dev_symbols.py callers compute_confidence
location
bga/analyzer.py:1862

$ python3 tools/dev_symbols.py dead --js
location                     name
bga/viewer/nav.js:16         RAILS
bga/viewer/tablefocus.js:38  forgetFocusTargets

$ time python3 tools/dev_symbols.py def analyze
... 0.66s real
```

One command, one call site, the two docstring mentions correctly
absent. `dead --js` found two unreferenced exports on this tree, not
five — the honest count, not a fitted one.

**Mutations** (`tests/unit/test_the_symbol_index_reads_the_tree_not_the_text.py`):

| mutation | reddened | printed |
|---|---|---|
| `callers` by regex over raw text | `test_a_string_and_a_docstring_are_not_callers` | `[('pkg/a.py:4',), ('pkg/a.py:12',), ('pkg/a.py:16',), ('pkg/a.py:21',)]` vs expected one row |
| `dead`'s reference scan drops the `ImportFrom` branch | `test_a_from_import_alone_counts_as_a_reference` | `imported_only_fn` (import-only reference) now `in dead_names` |
| `imported_names` returns `[]` for the `from` form | `test_importers_finds_both_the_import_and_the_from_form` | `{'pkg/b.py'}` vs expected `{'pkg/b.py', 'pkg/c.py', 'pkg/d.py'}` |
| `referenced_names` drops the `Name`/`Load` and `Attribute` branches (`ImportFrom` only) | `test_dead_lists_the_unreferenced_name_and_not_the_referenced_one` | `AssertionError: assert 'attr_called_fn' not in {..., 'attr_called_fn', ...}` — `attr_called_fn` is reached only by `pkg.a.attr_called_fn()`, no `from` import anywhere |

All four reverted from the pre-mutation copy; full file green after
each (`6 passed`). The verifier found the third row's guard did not
isolate the call path — `target_fn` survived a disabled `Name`/`Load`
branch through `pkg/c.py`'s `from pkg.a import target_fn`, a separate
`ImportFrom` credit — so `attr_called_fn` was added with no `from`
import reaching it anywhere in the fixture, and `__all__` is now
skipped in `top_level_names` (dunders are read by tooling, not by
name).

**Deviation.** The verifier measured four precision limits: an attribute call on a same-named method and a call to a shadowing inner definition are both listed as callers; a re-export is invisible to `dead`; `dead --js` found 2 exports, not the 5 round 93's grep reported. A navigation aid resolves names, not bindings — data-flow stays CodeQL's (`UX-698`); `UX-699` decides the viewer's five against the two.
CI, not the local gate, caught two 3.9 breaks the track wrote (`isinstance(x, A | B)`, `zip(strict=)`): no 3.9 here, and ruff has no rule for either under a 3.9 target. The two-second guard was a timing across machines (`UX-418`); it reads 2.26 s on a loaded runner and now holds only that the tool answers, the timing staying in this Outcome.
