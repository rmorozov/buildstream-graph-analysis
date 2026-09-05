# UX-524: the touching map is measured in CI, not grepped

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-522 (the census half), UX-503 (the adopt route the map reuses) | **Serves:** the session that wants `test-touching` to be a gate | **Topic:** guards | **Area:** tools

## Motivation

`dev_touching.py` selects by grep — a test file that names the
module — and its own docstring says why that is a selector and not a
gate: a test can exercise a module without naming it. `UX-500`'s
round counted what that costs (two misses in five, both census-class,
`UX-522`); the remaining class is the Python test that reaches a
module through an import chain and never spells its name.

CI already runs the whole suite. With `--cov-context=test` the same
run knows, per test, every module line it executed — the exact map
the selector guesses at.

## Required Fix

- The CI `test` job records a **touching map** (`tests/touch_map.json`:
  module → test files that executed it) from one Python version's
  run, and adopts it the way `UX-503` adopts the tier reference —
  on CI's own run, committed by the adopt job.
- `dev_touching.py` unions three sets: the grep (still catches docs
  and fixture readers), the map (catches the import chain), the
  census (`UX-522`). `--why` names which set selected each file.
- Measured before it is believed: the coverage run's extra wall
  clock on CI, the map's size, and the miss rate re-counted on the
  next Regime-A round.

## Out of Scope

- Coverage as a *target* — no percentage is asserted; the map is a
  selection instrument.
- Local `--record` of the map — refused for the reason `UX-447`
  gives about references from other clocks: the map comes from CI.

## Acceptance Test

A diff touching a module that no test names by string selects the
tests that import it; `--why` says "map". Mutation: delete the map
row — the selection falls back to grep and `--why` says so.

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

The selector's third class, after `UX-522` closed the census one: a
Python test that reaches a module through an import chain and never
spells its name. Built from a real coverage run of twelve files:

```text
$ pytest <12 files> -n auto --cov=bga --cov=tools --cov-context=test
$ python3 tools/dev_touch_map.py --write /tmp/tm.json
60 module(s), 167 edge(s)

$ dev_touching.select(["bga/analyzer.py"])
census 11 · map 3 · grep 33          selected by the map alone: 3
  test_a_chain_bound_build_still_has_a_blast_radius.py
  test_a_command_renders_as_a_command.py
  test_a_control_acts_on_what_it_names.py
```

Three guards a diff to `bga/analyzer.py` would not have run, from a map
built off 12 of 400 files. The committed map is `{}`: CI fills it.

### What it costs, measured before it was believed

```text
12 files, -n auto            33.2s
the same, --cov-context=test 40.0s        +20%
```

So it runs on **3.12** and never on 3.11 — which is the interpreter
whose seconds `UX-503`'s tier reference is made of, and a timing record
taken under coverage would move every row in it. That is a constraint
the filing did not name, and it is the one that decided where the job
goes.

### Mutations verified red and reverted (12)

| # | mutation | red |
|---|---|---|
| M1 | the map is keyed by test, not file | 2 |
| M2 | a null context is an edge | **0** |
| M3 | `tests/` modules are rows too | 1 |
| M4 | adopt replaces instead of adding | 1 |
| M5 | adopt drops the rows it did not measure | 2 |
| M6 | the selector ignores the map | 1 |
| M7 | `--why` calls a map edge a grep | 1 |
| M8 | a vanished guard is run anyway | 1 |
| M9 | an unparseable map raises | 1 |
| M10 | coverage moves to the timing interpreter | 1 |
| M11 | the adopt job runs on every pull request | 1 |
| M12 | the tool can write the map locally | 1 |

**M2 cannot discriminate, and the code is right anyway**: an empty
context splits to an empty guard, which fails the `tests/` check one
line down, so the row is dropped twice. The check is kept because a
database written without `--cov-context` is *every* row like that, and
its comment now says it is belt and braces.

M9 and M10 were green on their first writing. M9's clause monkeypatched
`touch_map` and never drove its own `except`; M10's read the `if:`
*before* the coverage flags, which is the previous step's — so the
clause passed with the coverage moved onto 3.11, which is the one thing
it exists to stop.

### Deviation from the Required Fix

None to the fix; one to what it can show. `tests/touch_map.json` ships
**empty**, because the filing refuses a local `--record` for `UX-447`'s
reason and this machine's run is not CI's. The mechanism is proved on a
fixture map and on the twelve-file measurement above; the first real
map arrives on the next push to the default branch, and the miss rate
the item asks to re-count is a next-round measurement by construction.

```text
=== 14 failed, 5957 passed, 27 skipped in 752.58s ===  (load average 12)
Twelve were the row this commit moves and the context map §3.10 asked
for; `test_the_first_thing_to_fix_is_core` is `UX-538`.
ruff check bga/ tools/ tests/ .claude/hooks/  ->  All checks passed!
```
