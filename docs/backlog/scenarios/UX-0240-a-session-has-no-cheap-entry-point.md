# UX-240: a session has no cheap entry point

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-238 (the tiers a skill would name), UX-239 (the map and the streams it would carry) | **Serves:** the maintainers, and every agent session | **Topic:** docs

## Motivation

The user's proposal: skill files, so an agent's interaction with the
codebase is more efficient.

The cost this is about is measurable. Every session in this repository
begins by re-reading the same things — the fixing guide, the style
guide, the backlog index, the Makefile, the test layout — before it can
do anything, and then re-derives the same procedures: how to falsify a
guard, how to regenerate the golden snapshot, which budget guards exist
and what their numbers mean. Round 28 rediscovered the golden-snapshot
recipe from a docstring, and rediscovered the falsification discipline
by getting it wrong four times.

A repository skill is the right shape for a *procedure that is followed
identically every time and is currently prose in a guide*. It is the
wrong shape for judgment, and this repository is mostly judgment — so
the scope is deliberately narrow.

## Required Fix

Skills only where the procedure is mechanical and repeated:

1. **verify** — the Definition of Done as a runnable checklist: the
   acceptance command, the right test tier, the full suite, lint, the
   status-row-and-file pair, the Outcome section.
2. **falsify** — the mutation discipline: apply, confirm the edit
   landed, run the one guard, confirm red, revert, confirm green. With
   the two failure modes this repository keeps hitting written into it:
   a mutation that does not discriminate, and a revert that resets past
   your own work.
3. **measure** — the recipes that get re-derived: the golden snapshot,
   the 1,202-element synthetic, the export size, the durations run.

Each skill points at the guide that owns the rule rather than restating
it, so there is one source and the skill is the entry point.

## Out of Scope

- A skill for "how to fix a task". That is judgment, and a skill that
  pretended otherwise would be a worse fixing guide.
- Anything that duplicates a guide's *content* rather than pointing at
  it. Two copies of one rule is the defect this repository has fixed
  more times than any other.

## Acceptance Test

Each skill's commands run as written against this tree, with output
pasted; a guard asserts every command a skill tells you to type exists
(the same check `test_docs_links_and_commands.py` already makes for the
guides); the skills contain no rule that is not also in a guide, and a
guard names where each points.

## Outcome

**Status:** 🟢 Fixed & Verified

Three skills under `.claude/skills/`, scoped exactly as the Required
Fix scoped them: `verify` (the Definition of Done as a sequence),
`falsify` (the mutation discipline), `measure` (the four recipes that
get re-derived from a docstring each round). Nothing about judgment,
and nothing that restates a guide's content — each names the guide that
owns its rule, and `verify` says out loud which document wins:
*"the guide is right and this file is a bug."*

### Every command, run as written

The golden recipe, straight out of the skill:

```text
$ PYTHONPATH=. python3 -m bga.cli analyze "$PWD/tests/fixtures/golden/mixed_task_kinds" \
    --format json --diagnostics | sed ... | python3 -c ... > .../expected_output.json
$ git diff --stat tests/fixtures/golden/mixed_task_kinds/expected_output.json
(no output — byte-identical)
$ python3 -m pytest tests/test_golden.py -q
2 passed in 0.63s
```

The scale run, twice, to check the claim the skill makes about it:

```text
$ bga gen-synthetic /tmp/scale --seed 1     -> 1202 elements
$ bga gen-synthetic /tmp/scale2 --seed 1
sha256 over both trees, sorted:  e6544b851e4fd275  ==  e6544b851e4fd275
$ bga analyze /tmp/scale --diagnostics      -> Total Duration: 357.1s, horizon 355.13s
```

The export split, which is the measurement the skill exists to stop
people from re-deriving wrong:

```text
$ bga view /tmp/scale3 --export /tmp/report3.html
total 833,552 B   page 141,603 B   data 691,949 B   ratio 4.9x
```

The page/data split matters and the total does not: the guard's rule is
that data dwarfs page at scale, and only the split can say so.

### The guard, and what it caught in its own first run

`tests/unit/test_the_skills_point_at_the_guides.py` (21 cases) checks
frontmatter, that each skill names its owning guide, that every
relative link resolves, and that every `make` target, `bga` subcommand
and repository path it names exists — the same checks
`test_docs_links_and_commands.py` makes for the guides, because a skill
is read and mis-typed the same way.

Its first run reported a make target called **`a`**, out of the
sentence *"make a document wrong"*. The command checks now read only
fenced blocks and inline code spans, not prose. That is the same
subject-versus-argument separation as `UX-239`'s map guard, in a new
costume: a guard that reads English as shell finds commands nobody
wrote.

### Two small things on the way

`.pymarkdown.json` gained the `front-matter` extension — without it a
skill's leading `---` reads as a setext heading and all three fail
MD022 — and `make lint-docs` now scans `.claude/` as well as `docs/`,
because a linted document and an unlinted one beside it is how the
unlinted one rots. `tests/tiers.py`'s docstring said "160 of 220
files"; it is 164 of 224, refreshed from the count.

**Mutations verified red and reverted (9):** a skill deleted; a
description too thin to route on; a skill no longer naming its guide; a
dangling relative link; a `make` target that does not exist; a `bga`
subcommand that does not exist; a repository path that does not exist;
`verify` no longer saying which document wins; `falsify` dropping one
of its three failure modes.

**Deviation from the Required Fix:** none. The acceptance test also
asked that "the skills contain no rule that is not also in a guide" —
that half is a checklist item rather than a guard, because deciding
whether a sentence is *a rule* or *an instruction for following one* is
judgment, and a guard that guessed would either pass on everything or
fail on the recipes. What is guarded is the pointer: every skill names
its owning guide, and losing that reddens.

Small tier: `2005 passed, 1130 deselected in 21.74s`.
Full suite: `3153 passed, 3 skipped in 313.71s`. `make lint`: clean.
