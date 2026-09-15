# UX-873: the target read knows the subcommand's own option arity

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-842, UX-870 | **Found by:** round 121, UX-870's verifier | **Serves:** R2 (a `bst build --deps all t.bst` capture reads its kinds and its max-jobs) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

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

## Outcome

**Gap measured.** Pre-fix, `_cmd_target(['bst', 'build', '--deps',
'all', 't.bst'])` returned `'all'` - the first non-dash token after
`build`, `--deps`'s own value, not the element - so
`read_element_kinds_for_jobserver`'s composed `bst show` argv ended in
`'all'` too.

**Close measured.** Same call now returns `'t.bst'`
(`_BST_SUBCOMMAND_OPTIONS_ONE_VALUE['build']`, read off
`buildstream._frontend.cli.cli.commands['build'].params`, BuildStream
2.8.0 this box - `--deps`/`-d`, `--artifact-remote`, `--source-remote`;
`--retry-failed` and the two `--ignore-project-*-remotes` flags are
bare, unchanged). `show`'s own table is read the same way
(`--except`, `--deps`/`-d`, `--order`, `--format`/`-f`); `track` and
`checkout` are not top-level commands in this installed bst (only
`source track`/`source checkout`), so carry no entry, unchanged
behavior for either.

`pytest tests/unit/test_the_kinds_read_carries_the_options.py`: `16
passed in 0.62s`. `make test-touching`: `105 file(s) selected (30
census + 75 naming the change) - 2700 passed, 35 skipped in 90.56s`.
`ruff check tools/bst_native_build_tracer.py
tests/unit/test_the_kinds_read_carries_the_options.py`: `All checks
passed!`. `python3 tools/dev_sizes.py --check` (post `--adopt --force`,
1 cell changed - `tools/bst_native_build_tracer.py` grew 8745 -> 8768
lines): `sizes ok`. `python3 tools/dev_baseline.py --check`: the two
`reportAttributeAccessIssue` lines it names on `kinds.junctions` /
`kinds.collisions` are pre-existing (measured on the unmodified base
commit `44be6778`, same finding, same "new" status - this task never
touches that line). `python3 -m pymarkdown --config .pymarkdown.json
scan` on this file: clean. `make check-clean`: `OK: no ignored files
are tracked`.

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| drop `--deps` from `_BST_SUBCOMMAND_OPTIONS_ONE_VALUE['build']` (kept `-d`) | `test_every_valued_option_of_the_installed_build_skips_its_value`, `test_the_kinds_read_argv_keeps_the_target_past_deps_all` | 2 failed, 14 passed -> reverted, 16/16 |

**Deviation (merge):** the verifier replayed the claimed mutation and
two of its own (a `skip_value` that never resets, a dash token that
always consumes the next) - each reddened a named case. `track` and
`checkout` stay in `_BST_TARGET_SUBCOMMANDS` from `UX-842` though the
installed bst reaches them only under `source`, so
`bst source track --deps all t.bst` still reads `all`; a capture wraps
`build`, and the row is not filed until a capture is wrapped around
`source`. Nothing added at merge.
