# UX-1341: the release guide spells `bga release-notes` with positional markers the CLI refuses

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** walk seed 5 (2026-10-07), finding 1 | **Serves:** R8 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** test_docs_links_and_commands.py

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
