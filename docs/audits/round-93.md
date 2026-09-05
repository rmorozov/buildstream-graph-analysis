# Design round 93: the gate holds the numbers; the review holds the design

Run on 2026-09-05, after round 92 was filed. A design round (§6a).
The user asked how to keep the code in shape as the tree grows —
static analysis and coverage exist but no refactoring cadence, so
comments go stale and complexity grows; revise the analysis rules;
put performance, security and maintenance analysis on the GitHub gate
without slowing the inner loop; a CodeQL skill for navigation in
place of greps; metrics whose control is delegated to tools, with
review reserved for design; a cheap self-review skill — and asked to
be challenged. One researcher measured the gate and the tree; the
argument is Direction 19; the filings are `UX-693`..`UX-703`.

## What exists today

| | |
|---|---|
| the gate | `make lint` = `ruff check` with `select = ["F"]` + PyMarkdown; no type, security, audit, JS or code-scanning step in either workflow |
| the config's own comment | "~30-module codebase … widen the rule set in a later, separate task" — 104 modules; no later task |
| `# noqa` | 286 (bga 4, tools 19, tests 263); 23 unused (`RUF100`) |
| wider ruff, `bga tools` | `UP` 1,378 · `S` 87 · `SIM` 37 · `B` 12 · `ERA001` 7 · `T201` 355 · `C901` 84 · `PLR091x` 111 |
| complexity (`radon cc -n C`) | 228 of 1,426 blocks C-or-worse; average B (6.37); MI 0.00 in `correlate.py`, `findings.py`, `report/text.py`, `bst_native_build_tracer.py` |
| longest functions | `format_text` 548 lines / CC 135 · `create_parser` 417 · `compute_confidence` 401 / CC 91 · `build_document` 339 / CC 86 · `analyze` 315 |
| files over 1,000 lines | 15 — tracer 6,960 · `schemas.py` 5,517 · `analyzer.py` 2,612 · `cli.py` 2,301 · `findings.py` 2,107 |
| dead code (`vulture --min-confidence 80`) | 0 |
| stale comments | backticked identifiers in comments: 1,585 checked, 0 unresolved · lines naming a round in `bga/`+`tools/`: 31 · TODO/FIXME: 0 |
| typing | no config; `pyright` 270 errors in 104 files (10.4 s); `mypy` 168 in 26; 57.5 % of `bga/` functions fully annotated |
| security / supply chain | `bandit -ll`: 2 High, 14 Medium (`B314` at `dev_tier_drift.py:298`); deps all `>=`, no lockfile, no Dependabot; `pip-audit` could only read the ambient env (37 advisories, none in `networkx`/`pyyaml`) |
| viewer | 12,906 JS lines, never linted; eslint per file 70 problems (55 `no-unused-vars` mostly cross-module, 8 `no-undef`, 6 `eqeqeq`); 5 exports referenced nowhere; no import cycles |
| CodeQL | not installed; 62,440 Python + 12,906 JS lines — a minutes-long database build for questions grep answers in ms |
| tool versions | `ruff>=0.6` — the gate's own tool floats |

Commands and the full statistics are in the researcher's row below;
each number above is one of its pasted outputs.

## The six corrections

1. **The cadence is not missing; the measurement is.** §6a defines
   the refactor stream by a measured cost and nothing records one. A
   ratcheted ledger, and the top row is the refactor's queue.
2. **Stale comments are counts, promises and history — not names.**
   The identifier guard the brief implies would find nothing; the
   register's unguarded rows are the guard.
3. **Three shelves.** Auto-fixed, ratcheted, gate-only. The inner
   loop keeps `ruff` on the edited file; everything slower is hosted.
4. **CodeQL is for data-flow at the gate; navigation wants an AST
   index** — the `orient` greps are slow in tokens, not in seconds.
5. **`REVIEW.md` already delegates to the gate** — every rule the
   gate holds is a pass the review drops; the reader is routed by the
   impact set, not chosen.
6. **The self-review is the existing policy on the diff**, on the
   reporters' model, never a second checklist.

## Filed

`UX-693` (the rule set widened by layer, tools pinned — High),
`UX-694` (the quality ledger — High), `UX-695` (the refactor stream
takes the top row, renderers first — Medium), `UX-696` (the register's
unguarded rows — Medium), `UX-697` (a type-error ratchet, contracts
first — Medium), `UX-698` (the gate-only shelf on GitHub — High),
`UX-699` (the viewer linted as one module graph — Medium), `UX-700`
(the symbol index; CodeQL declined for navigation — High), `UX-701`
(the `self-review` skill — High), `UX-702` (a performance ratchet at
the gate — Medium), `UX-703` (a mutation run on the touched modules,
weekly — Low).

## Agents

| agent | model | task | tokens | tool calls | wall | friction |
|---|---|---|---|---|---|---|
| researcher | sonnet | the gate as configured; ruff by family; radon, an AST size pass, vulture; a stale-comment census; pyright and mypy; bandit and pip-audit; eslint on the viewer; CodeQL feasibility | 62k | 51 | 5.8 m | `ruff --statistics` exits 1 on any finding, so each family needed its own invocation to keep the count |

## Standing

A design round produces no code; the one test edit is the direction
walk's count, 1-18 → 1-19. Two of the brief's premises did not
survive measurement: the stale-comment shape (names: 0 of 1,585) and
CodeQL as a navigation tool (a minutes-long build for millisecond
questions). The rest held and is filed with its numbers. The user
confirmed the repository is public, so `UX-698` takes CodeQL. Not
established: whether the five unreferenced viewer exports are reached
dynamically (`UX-699` checks before deleting). The round's own gate
went red on the branch — the backlog it added to made `--check`
quadratic in the guard that runs it eleven times — and `UX-704`
closed it: the ledger of `UX-694` and the ratchet of `UX-702`, met
live.
