# UX-687: the impact set is derived by one tool, not five greps

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-524 (the CI-measured touching map), UX-498 (decompose), UX-499 (the orient recipes) | **Serves:** the session at the design stage, before the first edit | **Topic:** guards | **Shape:** judgement

## Motivation

The `decompose` skill derives *surfaces* — the files a change touches
and the guards that name them (`dev_touching`, the touch map). What
a design-stage reader also needs is the *impact*: which contracts a
module emits, which findings it produces, which guides name the
module or its command, which styleguide sections cite the viewer
module, which open filings sit on the same area. Today that is five
recipes in the `orient` skill, run by hand, or not.

```text
tools/dev_touching.py     grep selector           module → test files
tools/dev_touch_map.py    coverage map (CI-filled) module → test files
tools/dev_js_deps.py      viewer import graph
module → contracts / findings / guides / styleguide § / open filings   no index (grep tools/ → 0)
```

## Required Fix

`tools/dev_impact.py <diff | UX-NNN | module>` prints the impact set:
modules; contracts (`bga/schemas.py` keys by emitting module, via
`bga/contracts.py`); finding ids (`bga/findings.py` by module);
guides and README lines naming the module or its `bga` command;
styleguide sections the viewer module cites; guards (grep ∪ touch
map ∪ census set); open filings whose area (`UX-688`) matches. The
`decompose` skill's §1 becomes "run the tool and paste"; a filing's
decomposition block carries the set.

## Out of Scope

- Judging the impact — the tool lists; the session decides what a
  change may break.

## Acceptance Test

For a diff in `bga/correlate.py` the set names `correlate/v2`, the
restructuring finding, `real-project.md`'s Step 6, the join guards
and any open correlate filing; mutation: drop the contracts source —
red on the contract row.

## Outcome

🟢 Done. `tools/dev_impact.py <- | UX-NNN | module>` prints six rows,
each from one source, and `decompose` §1 now opens with it:
`git diff --name-only | python3 tools/dev_impact.py -`.

```console
$ python3 tools/dev_impact.py bga/correlate.py
10 contract id(s) no module name claims: analyze/v2 … store/v1

bga/correlate.py
  contracts     2  correlate/v1, correlate/v2
  guides       28  docs/guides/cli.md:20, … docs/guides/real-project.md:…
  guards       29  tests/unit/test_correlate.py, … (+21)
  filings       8  UX-676 …, UX-684 …
```

All four acceptance clauses hold: `correlate/v2`, `real-project.md`,
the join guard, an open filing.

### The contract row was three wrong sources before it was one right one

The Required Fix said *"contracts by emitting module, via
`bga/contracts.py`"*. That source does not answer the question:

| tried | what it actually says |
|---|---|
| `contracts.inventory()` | where the `SCHEMA` constant is **declared** — `bga.schemas` for 24 of 25 |
| the module's own text | nothing: `correlate.py` never says `correlate/v2` |
| the id's stem vs the module's stem or command | 14 of 25 — the join that ships |

The first two are `CLAUDE.md`'s *instrument that reads a proxy*, and I
built both before measuring either. The emitting relation is **not
recorded anywhere derivable** in this tree, so rather than type an
alias table — a second copy of a fact, which is what round 96 has
spent itself on — the tool places what the name places and
`unplaced()` names the other ten. A row that is silently partial is
worse than one that says so (`UX-376`).

### The guard caught a second copy in the tool itself

`unplaced()` first restated `contracts_of`'s join instead of using it,
and the two disagreed on `analyze/*`: the command is `analyze`, the
module is `analyzer.py`, so one counted them placed and the other did
not. `test_every_contract_is_placed_or_named_unplaced` found it before
the commit. `unplaced()` now iterates `contracts_of`.

### Mutations

Six clauses, six mutations, each reddening its own and only its own.

| mutation | guard |
|---|---|
| the contracts source dropped (the row's own) | the contract clause |
| `PROSE = ()` | the guide clause |
| the guards row stops reading the selector | the join-guard clause |
| the filings row stops reading the index | the filing clause |
| `unplaced()` claims every id | the *not everything* clause |
| the skill stops naming the tool | the decompose clause |

### Deviation

The filings row joins on **Topic**, not the Area the Required Fix
names: `UX-688` has not landed, and every task already carries a
Topic. The row is written so that `UX-688` changes one function.

**The tool shells out to nothing, and that was forced rather than
chosen.** `--diff` first ran `git diff` itself; ruff's `S607` (partial
path) then `S603` (subprocess at all) each raised a *new* baseline
finding, and `UX-694`'s rule is that the list only shrinks, with
`UX-705` ruling out a suppression. Resolving the binary cleared `S607`
and not `S603`, so the diff moved to stdin: the caller owns which
revisions it compares and this stays a reader. Baseline unchanged at
299.

`--rows` caps what prints; `report()` returns the full set and the
guard reads that. The styleguide row is viewer-only and no viewer
module was in the acceptance case, so it is written and unexercised.
