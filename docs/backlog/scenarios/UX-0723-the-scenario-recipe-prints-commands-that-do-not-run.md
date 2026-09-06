# UX-723: the scenario recipe prints commands that do not run

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-685 (which built the tool) | **Serves:** the walker following the script the seed prints | **Topic:** guards | **Shape:** judgement | **Area:** tools

## Motivation

`UX-685`'s first walk, at seed 1, found it in its first minute. The
recipe `tools/dev_scenario.py` prints is not runnable:

```text
$ python3 tools/dev_scenario.py --seed 1 | grep gen-synthetic
  one element (`bga gen-synthetic --seed N --elements 1`)
$ bga gen-synthetic --seed 1 --elements 1 /tmp/gsprobe
bga gen-synthetic: error: unrecognized arguments: --elements /tmp/gsprobe
$ bga gen-synthetic --help | grep -E "^  --(layers|width)"
  --layers LAYERS
  --width WIDTH
```

And `--layers 1 --width 1` is not the correction, because
`gen-synthetic` **plants a run** — `graph.json`, `run-context.json`,
`trace.json` — while the same recipe's next line says "a cold `bst
build all.bst`". A planted run and a built one are different things
and the recipe asks for both.

The Plane 2 rows are the same defect:

```text
tools/dev_scenario.py:49  "absent":    `bga snapshot -- bst build all.bst` — no hook, no spine
tools/dev_scenario.py:50  "hook only": `bga snapshot -- bst build all.bst` — the LD_PRELOAD hook, no spine
```

**One command, two annotations, and neither is what it does**:
`bga snapshot` defaults to `--trace-opens --trace-spine=auto`, so the
walker following the "absent" row captured Plane 2 anyway and had to
detour through `bga wrap` + `bga extract` — the older path `cli.md`
frames as what `snapshot` replaced — to reach the state the seed drew.
`--no-trace-opens` and `--trace-spine off` both exist and neither row
names them.

## Required Fix

Each of the six input classes' recipe is a command that runs, verified
by running it. Where a class needs two commands (plant *or* build),
the recipe says which, and the two are not printed as one. Decide
whether a `population` recipe plants a run or builds a project — the
draw is over input classes, and those are different inputs — and say
which in the Outcome.

A guard: every fenced command the tool prints parses against its own
`--help`, for every seed in a fixed sample.

## Out of Scope

- Whether `--no-trace-opens --trace-spine=off` yields a *fully* absent
  Plane 2 — measure it while fixing row 49, and file separately if it
  does not.

## Acceptance Test

For seeds 1..10, every command the recipe prints runs to exit 0 (or to
its own documented refusal) on a scratch project. Mutation: restore
`--elements` — the guard reds naming the seed and the flag.
