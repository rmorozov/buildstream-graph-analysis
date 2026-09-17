# Round 128 — the ninja wrapper owns ninja's -j

Run on 2026-09-17, after round 127 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit, and closed with the round.

## The premise

A field report on latest bga: a `kind: cmake`/`meson` element whose
recipe is `ninja -v -j ${JOBS} -C _builddir` crashed
`ninja: fatal: invalid -j parameter` under `--jobserver auto`. Root
cause: with the UX-846 ninja wrapper mounted, `_ninja_aware_env` empties
`JOBS` (`--setenv JOBS ""`) to neutralize the recipe's own parallelism —
but that assumes the recipe is `ninja ${JOBS}` (the flag *inside* `JOBS`,
or a bare int dropped cleanly). This recipe writes the `-j` itself and
puts a bare count in `JOBS`, so an emptied `JOBS` leaves `ninja -j  -C`
— ninja reads `-C` as the `-j` value and dies. Separately, an explicit
`-jN` in a recipe lands a second `-j` after the wrapper's, and ninja
takes the last, so the recipe silently defeats the wrapper's token width.

The wrapper's whole job (UX-846) is to be ninja's single source of `-j`.
It was leaving the recipe's alongside its own.

## Plan

| wave | rows | why |
|---|---|---|
| build | `UX-888` | the `dashj` branch of `bga_run_wrapped` strips the recipe's own `-jN`/`--jobs=N`/dangling-`-j` from the args before prepending the wrapper's `-j<width>` |

One row, the session's own (a single shell branch + one guard);
immediate workaround for the reporter meanwhile: `--jobserver off`, or
`--jobserver-auth-override 'off:<element>'` to scrub just that element
(the scrub path drops the `JOBS` override, so BuildStream's own count
stands and `-j ${JOBS}` is valid).

## What closed

_(filled at close)_

## The verifiers found

_(filled at close)_

## Agents

No agents launched — the fix was the session's own (a single shell
branch in `bga_run_wrapped` plus one under-`sh` guard), too small to
brief a track and cheaper done in place than through a worktree round.

## The gate

| run | head | result |
|---|---|---|
| 0 | the filing | red only on the round-open bootstrap guards; docs-only |

## Standing

_(filled at close)_
