# UX-873: the target read knows the subcommand's own option arity

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-842, UX-870 | **Found by:** round 121, UX-870's verifier | **Serves:** R2 (a `bst build --deps all t.bst` capture reads its kinds and its max-jobs) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`_cmd_target` (`UX-842`) takes the first token after the subcommand
that does not start with `-` as the element: on
`bst build --deps all t.bst` that is `all`, so the kinds read runs
`bst show ... all` and fails (`UX-870` now records it -
`kinds_read.json`, reason `exit` - but cannot fix it), and
`read_project_max_jobs` reads a max-jobs for an element that does not
exist. `UX-870` gave the *global* options their arity, read off the
installed `cli` group; `build`'s own valued options (`--deps`,
`--remote`, `--artifact-remote`, `--source-remote`, `--retry-failed`
is bare) were out of its scope. Measured by the verifier:
`_cmd_target(['bst','build','--deps','all','t.bst'])` is `'all'`.

## Required Fix

`tools/bst_native_build_tracer.py`: `_cmd_target` skips a subcommand
option's value by the subcommand's own arity table, read off the
installed `buildstream._frontend.cli` command (`build`, `show`,
`source fetch`, ...) the same way `UX-870` reads the group; the guard
derives its cases from that command's `params`, not from the table.

## Decomposition

Input classes: no option after the subcommand, a bare flag, a valued
option (`--deps all`), a valued option repeated. Surfaces:
`tools/bst_native_build_tracer.py` (`_cmd_target`, one table) ·
`tests/unit/test_the_kinds_read_carries_the_options.py`. Parallel with
anything not touching the tracer's option tables.

## Out of Scope

A target given through an option (`--deps` names a scope, not an
element); a subcommand the installed `bst` does not define.

## Acceptance Test

`tests/unit/test_the_kinds_read_carries_the_options.py`: for every
valued option of the installed `build` command,
`_cmd_target(['bst', 'build', opt, *values, 't.bst'])` is `'t.bst'`;
mutation: drop `--deps` from the arity set - red.
