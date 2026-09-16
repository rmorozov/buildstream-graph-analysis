# UX-876: jobserver auto picks fd, the style every make accepts

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-841, UX-874 | **Found by:** round 123, the user (a cmake element whose sandbox-built cmake runs /usr/sysroot/bin/make, GNU Make 4.4 on the host) | **Serves:** R2 (a project builds under --jobserver auto whatever makes its sandboxes ship) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`jobserver_auth_style("auto")` picks `fifo:` from the **host**
`make --version` when the host is GNU Make 4.4 or newer
(`tools/bst_native_build_tracer.py`). `UX-874` tried to narrow that
per element by probing the sandbox make, but the probe reads bare
`make` on the sandbox `PATH` and covers only `make`/`autotools`
kinds - and the make that actually consumes the string can be neither.
The user's `kind: cmake` element runs `cmake --build _builddir --
${JOBS}`, which invokes `/usr/sysroot/bin/make` (a make built inside
the sandbox, below 4.4) by absolute path, and it dies:
`make: *** internal error: invalid --jobserver-auth string
'fifo:/tmp/.bst-native-trace/jobserver'. Stop`, exit 2. There is no
way for `auto` to identify, ahead of the build, every make a recipe
might invoke. `fd`-style auth is accepted by every GNU Make from 4.2
up, so it works across a mixed toolchain; `fifo` only buys robustness
against sub-processes that drop inherited fds, on a toolchain known to
be 4.4 throughout. So `auto` should pick the safe one and leave `fifo`
to an operator who knows their toolchain.

## Required Fix

`tools/bst_native_build_tracer.py`: `jobserver_auth_style("auto")`
returns `"fd"` - unconditionally, no host `make --version` probe. An
explicit `fd` or `fifo` request is unchanged (`fifo` is the opt-in for
a uniformly >= 4.4 toolchain). `bwrap_shim.style_for_make_version`
stays (UX-874's per-element sandbox narrowing still reads it for an
explicit `fifo`), but `auto` no longer calls it. `docs/guides/cli.md`:
the `--jobserver-auth` row says `auto` is `fd`, and `fifo` is the
opt-in whose whole sandbox toolchain must be GNU Make 4.4 or newer.

## Decomposition

Input classes: requested fd, fifo, auto (host make 4.3, 4.4, absent -
all three now `fd` for auto). Surfaces: `tools/bst_native_build_tracer.py`
(`jobserver_auth_style`) · `docs/guides/cli.md` ·
`tests/unit/test_the_jobserver_fifo_has_a_lifecycle.py` (its `auto` ->
fifo-at-4.4 assertion flips). Parallel with UX-877 (disjoint file).

## Out of Scope

The sandbox-side per-element downgrade for an explicit `fifo`
(`UX-877`). Removing `fifo` support. `style_for_make_version` itself,
still shared with the sandbox probe.

## Acceptance Test

`tests/unit/test_the_jobserver_fifo_has_a_lifecycle.py`:
`jobserver_auth_style("auto", "GNU Make 4.4\n")` is `"fd"` (was
`"fifo"`), `jobserver_auth_style("auto", "GNU Make 4.3\n")` is `"fd"`,
`jobserver_auth_style("fifo")` is `"fifo"` and
`jobserver_auth_style("fd")` is `"fd"` unchanged. Mutation: let `auto`
return `style_for_make_version(...)` again - the 4.4 case reads `fifo`
and reddens. The guide's `--jobserver-auth` row read against the code
by the doc-parse guard.
