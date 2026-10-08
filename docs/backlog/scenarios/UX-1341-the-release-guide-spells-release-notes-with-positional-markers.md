# UX-1341: the release guide spells `bga release-notes` with positional markers the CLI refuses

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** walk seed 5 (2026-10-07), finding 1 | **Serves:** R8 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** test_the_release_body_is_generated.py

## Motivation

`docs/contributing/release-guide.md` step 6: "`bga release-notes <from> <to>`".
On `3e3657a7`, `bga release-notes 1083 1277`:

```text
usage: bga release-notes [-h] --from START [--to END]
error: the following arguments are required: --from
```

`docs/guides/cli.md` has it right.

## Required Fix

Spell it as the CLI takes it, `--from <marker> [--to <marker>]`.

## Out of Scope

Making the markers positional.

## Acceptance Test

The step's command runs as written.

## Outcome (round 172, 2026-10-07) — 🟢 Done

**Premise:** held — `test_docs_links_and_commands.py` passed 59/59 on the old spelling, so no guard read it.

### The gap, measured

```text
$ bga release-notes 1083 1277
usage: bga release-notes [-h] --from START [--to END]
error: the following arguments are required: --from
```

### After

```text
$ pytest -q tests/unit/test_the_release_body_is_generated.py -k spelling
1 passed
```

Step 6 reads `bga release-notes --from <marker> [--to <marker>]`; the guard
runs the guide's own spelling, brackets opened and markers set to 1, through the module `bga release-notes` dispatches to.

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| A1 | the guide's step 6 back to `<from> <to>` | `test_the_release_guides_spelling_is_one_the_cli_takes`, `assert 2 == 0`, 1 failed |
