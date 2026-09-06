# UX-723: the scenario recipe prints commands that do not run

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-685 (which built the tool) | **Serves:** the walker following the script the seed prints | **Topic:** guards | **Shape:** judgement | **Area:** tools

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

## Outcome

**The gap, measured.** The Motivation held, and there was a third
figure wrong in the same table:

```text
$ bga gen-synthetic --seed 1 --elements 1 /tmp/gsprobe
bga gen-synthetic: error: unrecognized arguments: --elements /tmp/gsprobe
$ find examples/06-macro-micro-optimization -name "*.bst" | sed 's|.*/||' | sort -u | wc -l
11                        # the recipe said "(9 elements)"
$ python3 -c "print(_RECIPE['Plane 2']['absent'] == _RECIPE['Plane 2']['hook only'])"
False — but both begin `bga snapshot -- bst build all.bst`
```

**The close, measured.** Every fragment now names a committed project
and a build target, and the three Plane 2 rows are three commands:

```text
population 0     examples/08-process-storm, built twice — the *rebuilt*
                 population of the second build
population 1     examples/08-process-storm, `bst build toolchain.bst`
                 (a leaf: no `depends` key in the file)
population many  examples/06-macro-micro-optimization, `bst build
                 all.bst` (11 elements)
Plane 2 absent   `bga wrap` then `bga extract` — see the deviation
$ python3 -m pytest tests/unit/test_a_scenario_is_named_by_its_seed.py -q
13 passed in 4.64s
```

**The mutation table.** Four, each reddening a named clause.

| mutation | clause that reds |
|---|---|
| restore `--elements`, the flag seed 1 found | `..._names_a_project_and_a_target` **and** `..._flag_is_one_its_subcommand_takes` |
| a subcommand `bga` does not have | `..._names_a_real_subcommand` |
| the two Plane 2 recipes collapse to one | `..._three_plane_two_recipes_are_three_commands` |
| a population row goes back to a planted run | `..._names_a_project_and_a_target` |

**Three deviations.**

*`population 0` is not a build.* A cold build of anything rebuilds
something, so the class is unreachable as a build target and the seed
that draws it crossed with `capture mode: cold` asks for a
contradiction. The row now names the *rebuilt* population of a second
build, which is the only zero this tool can publish. The class table
itself still lets the two cross; that is `decompose`'s, not this
item's.

*`Plane 2: absent` is not a `bga snapshot` command at all.* The Out of
Scope asked for this to be measured while fixing row 49, and it does
not hold: `--no-trace-opens --trace-spine=off` still compiles and
injects the hook and still writes a `plane2.json` — present, and empty
(`process_count 0`), with `plane2_absence` `null`. The row names
`wrap`+`extract`, and `UX-726` carries the flag defect.

*Seed 1's answer-key rows became rules in the same commit.* They
asserted the gap and reddened the moment this landed, which is the
ratchet those rows were written for: they now assert that a population
recipe names a project and that the three Plane 2 rows are three
commands.

