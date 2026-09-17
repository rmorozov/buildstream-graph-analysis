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

`UX-888`. `bga_run_wrapped`'s `dashj` branch now strips the recipe's own
`-jN`/`--jobs=N`/dangling-`-j` before prepending the wrapper's token-held
`-j<width>`, so the wrapper is ninja's single source of `-j` whatever
shape the recipe wrote it. `+18 -1` in `tools/native_trace/wrappers/_common.sh`;
no `bwrap_shim.py` change. Guard: `test_the_ninja_wrapper_owns_the_j_flag.py`
(new, 5 tests, the real wrapper under `sh` over a seeded pipe pair).

## The verifiers found

No verifier track — the session held the change and its falsify pass
(the strip block deleted reddens 4 of the 5 guards, the field-bug
dangling-`-j` case among them; reverted, all green). `make test-touching`
green over the diff but for the round's own close markers; the full
`make test` gate is the row below.

## Agents

This round has no agents launched — the fix was the session's own (a
single shell branch in `bga_run_wrapped` plus one under-`sh` guard), too
small to brief a track and cheaper done in place than through a worktree
round.

## The gate

| run | head | result |
|---|---|---|
| 0 | the filing | red only on the round-open bootstrap guards; docs-only |
| 1 | the fix + close | `make test` green; the gate the push hook covers |

## Standing

One field bug closed. A ninja recipe under `--jobserver auto` now builds
whatever shape it writes `-j` — the flag inside `${JOBS}` (cmake), a bare
count in `${JOBS}` (the crash), an explicit `-jN`, or none — because the
wrapper strips the recipe's and owns its own. The `threads`-style analog
(`mold`/`lld --threads` beside a recipe's own) is unreported and unfiled;
if it bites, it is a one-line symmetric strip in the same branch.
