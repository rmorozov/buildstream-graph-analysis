# UX-888: the ninja wrapper owns ninja's -j, stripping the recipe's own

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-846, UX-843 | **Found by:** round 128, the user (a `kind: cmake`/`meson` element whose recipe is `ninja -v -j ${JOBS} -C _builddir` — the `-j` literal, `JOBS` a bare count — crashed `ninja: fatal: invalid -j parameter` under `--jobserver auto`) | **Serves:** R2 (a project builds under the jobserver whatever shape its ninja recipe writes `-j`) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** bounded

## Motivation

For a ninja-capable element with the UX-846 wrapper mounted,
`_ninja_aware_env` injects `--setenv JOBS ""` (`bwrap_shim.py:297`) to
neutralize the recipe's own parallelism so the wrapper's token-held
`-j<width>` governs. That empties `JOBS` on the theory the recipe is
`ninja ${JOBS}` — where `${JOBS}` is the whole flag (cmake's
`JOBS: -j%{max-jobs}`) or a bare int the shell drops cleanly. But a
recipe of the third shape, **`ninja -j ${JOBS}`** (the `-j` literal in
the recipe, `JOBS` the bare count), becomes `ninja -j  -C _builddir`
when `JOBS` is emptied: ninja reads the next token (`-C`) as the `-j`
value and dies `invalid -j parameter` (field report). Separately, an
element that writes an explicit `-jN` puts a second `-j` after the
wrapper's prepended one, and ninja takes the last — so the recipe, not
the wrapper's token width, wins, silently defeating the jobserver.

The wrapper's whole job (UX-846) is to be the single source of ninja's
parallelism. It should own the `-j`, not leave the recipe's alongside.

## Required Fix

In `bga_run_wrapped`'s `dashj` branch (`tools/native_trace/wrappers/_common.sh`),
before running `"$real" -j "$width" "$@"`, strip from `"$@"` any ninja
parallelism flag the recipe carries: `-jN` (glued), `--jobs=N`, and a
lone `-j` (with a following bare-integer arg dropped too, but a
following non-integer — a dangling `-j` from an emptied `${JOBS}`, e.g.
before `-C` — left in place). Then the wrapper's own `-j<width>` is the
only one ninja sees. POSIX-sh argv rotation (shift from the front,
re-append kept args to the back), so args with spaces survive.

Scope: the `dashj` (ninja) style only — the reported failure. The
`threads` style (`mold`/`lld` `--threads`) is a symmetric but unreported
case (Out of Scope). No `bwrap_shim.py`/`JOBS`-emptying change: the
strip makes the empty-`JOBS` dangling-`-j` moot for a wrapped ninja.

## Decomposition

surfaces: `tools/native_trace/wrappers/_common.sh` (the `dashj` strip in `bga_run_wrapped`)
guards: `test_the_ninja_wrapper_owns_the_j_flag.py` (new): the real `ninja` wrapper run under `sh` (reuse UX-846's `test_a_held_tool_returns_its_tokens.py` fifo/fake-tool harness) — a dangling `-j` before `-C` is stripped and the real ninja gets exactly one `-j<width>` with `-C`/`_builddir` preserved; an explicit `-j 8` is stripped so only the wrapper's width remains; a glued `-j8`/`--jobs=8` too
gap: a non-wrapped `jobs_env` recipe `<tool> -j ${JOBS}` (no wrapper to strip) still strands the flag when `JOBS` is emptied — a separate filing if it bites; the `threads` analog likewise
track: session's own (a single shell branch + one guard); no parallel item
gate: batch PR (round 128)

Input classes: dangling `-j` (next arg non-integer, e.g. `-C`) → drop the
`-j`, keep the next; `-j 8` (next a bare int) → drop both; `-j8` glued →
drop; `--jobs=8` → drop; no `-j` in the recipe → args unchanged; the
wrapper's own `-j<width>` always the sole `-j` the real ninja receives.

## Out of Scope

The `threads` style (`--threads`) analog. bga's `JOBS`-emptying in
`bwrap_shim.py` (the strip makes it moot for a wrapped ninja). A
non-wrapped `jobs_env` `-j ${JOBS}` recipe. The `flto` style (UX-880,
its own path).

## Acceptance Test

`tests/unit/` new file, reusing UX-846's under-`sh` harness (a real FIFO
seeded with a couple of tokens, a fake `ninja` on PATH past the wrapper
that echoes its argv): the wrapper invoked as `ninja -v -j -C _builddir`
(the emptied-`${JOBS}` shape) runs the fake ninja with exactly one `-j`
(the wrapper's `-j<width>`), `-C _builddir` intact, no stray `-j`;
invoked as `ninja -j 8 build` the `-j 8` is gone and only `-j<width>`
stands; `-j8` and `--jobs=8` likewise. Mutation: delete the strip block
— the dangling-`-j` case reddens (the fake ninja receives two `-j`).

## Outcome

**The gap.** `bga_run_wrapped`'s `dashj` branch was `"$real" -j "$width"
"$@"` — the recipe's own `-j` rode along in `"$@"`. Three shapes broke:
a dangling `-j` (from an emptied `${JOBS}` before a non-integer, e.g.
`-C`) crashed ninja `invalid -j parameter`; an explicit `-jN`/`--jobs=N`
landed a second `-j` and ninja took the last, defeating the token width.

**The close.** A strip loop guards the final `case` when `flag_style =
dashj`: POSIX argv rotation drops `-j[0-9]*`/`--jobs=*` and a lone `-j`
(consuming a following bare integer, leaving a non-integer in place), so
the wrapper's prepended `-j<width>` is the only `-j` the real ninja sees.
`+18 -1` in `_common.sh`; no `bwrap_shim.py` change — the strip makes the
empty-`JOBS` dangling `-j` moot for a wrapped ninja.

**Guard.** `test_the_ninja_wrapper_owns_the_j_flag.py` (new, 5 tests)
runs the real `ninja` wrapper under `sh` against a seeded pipe pair (2
tokens, cap 8 → width 3) with a fake ninja that echoes its argv, reusing
UX-846's `test_a_held_tool_returns_its_tokens` harness.

**Mutation** (delete the strip block, `make test-touching`):

| the argv the guard sends | real ninja receives (mutant) | verdict |
|---|---|---|
| `-v -j -C _builddir` (dangling) | `-j 3 -C _builddir` — the `-C` is now the width | RED |
| `-j 8 build` | `-j 3 -j 8 build` | RED |
| `-j8 build` | `-j 3 -j8 build` | RED |
| `--jobs=8 build` | `-j 3 --jobs=8 build` | RED |
| `-C _builddir` (no recipe `-j`) | `-j 3 -C _builddir` | green (nothing to strip) |

4 of 5 red; reverted, all 5 green.

**Deviation.** None. Scope held to the `dashj` style; the symmetric
`threads` (`--threads`) case is unreported and stays Out of Scope.
