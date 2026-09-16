# UX-874: the jobserver auth style follows the make that consumes it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-841, UX-869 | **Found by:** round 122, the user (a make-kind element from a tar source, GNU Make 4.4 on the host) | **Serves:** R2 (a make element joins the jobserver whatever make its own sysroot ships) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** mechanical

## Motivation

`jobserver_auth_style("auto")` runs `make --version` **on the
host** and picks `fifo:` for GNU Make 4.4 and newer
(`tools/bst_native_build_tracer.py:1090`), then hands the one style to
every sandbox through `BST_TRACE_JOBSERVER_AUTH`. Its docstring states
the assumption - "the sandboxes here run the host's own toolchain, so
the host's version is representative" - and the field falsified it: a
`kind: make` element built from a `tar` source stages its own older
`make`, and that make rejects the string the host's 4.4 chose:
`make: *** internal error: invalid --jobserver-auth string
'fifo:/tmp/.bst-native-trace/jobserver'. Stop`, exit 2, the build
dead on that element. `UX-869` put the FIFO where the sandbox can
reach it; the path is right (`/tmp/.bst-native-trace/jobserver`, no
`mkdir parents` error) - the *style* is wrong, chosen from a make that
is not the one that runs. `fd` style is accepted by every make from
4.0 up, so the host that picked `fifo` loses nothing by falling back
to it when the sandbox make is older. The instrument reads a proxy
(the host make) for the thing it names (the sandbox make); fixing
guide section 5.

## Required Fix

`tools/native_trace/bwrap_shim.py`: when the resolved style is
`fifo` (`BST_TRACE_JOBSERVER_AUTH == "fifo"`), the shim probes the
sandbox's own `make --version` before it injects - through the real
`bwrap` the way `probe_ninja` already does, cached beside
`ninja_probe.json` under the jobserver dir - and falls back to `fd`
for that element when the sandbox make is below 4.4 (or make is
absent/unparseable, which `jobserver_auth_style` already treats as
`fd`). The fd path needs the descriptor open, so the downgrade opens
the jobserver read-write and inheritable as `open_jobserver_fd` does
for the fd case. The global FIFO and UX-849's per-element proxy both
follow the downgrade, since both are consumed by the same sandbox
make. `jobserver_auth_style`'s host probe stays as the *request*
default; the sandbox probe is the *consumer* check that can only
narrow fifo to fd, never widen.

## Decomposition

Input classes: sandbox make >= 4.4 (fifo stands), sandbox make <
4.4 (downgrade to fd), make absent or unparseable (fd), a proxy under
each. Boundary: the exact 4.4 cutoff `jobserver_auth_style` already
uses, shared not re-coded. Surfaces: `tools/native_trace/bwrap_shim.py`
(the probe, the downgrade, `open_jobserver_fd`) ·
`tests/unit/test_bwrap_shim.py` and
`tests/unit/test_the_jobserver_fifo_has_a_lifecycle.py`. Serial after
nothing; parallel with UX-875 (disjoint surfaces).

## Out of Scope

The host request default (`UX-841`'s `auto` -> fifo/fd from the host
make) - only the sandbox-consumer narrowing is new here. Making a
sandbox with no make at all join anything. Caching the sandbox make
probe across elements (per-element like `ninja_probe` is enough).

## Acceptance Test

`tests/unit/test_bwrap_shim.py`: with `BST_TRACE_JOBSERVER_AUTH=fifo`
and a fake `make` on the sandbox `PATH` reporting `GNU Make 4.3`, the
composed `MAKEFLAGS` carries `--jobserver-auth=<fd>,<fd>`, not
`fifo:`, and the build runs clean through the read-only-root fake
bwrap; with the fake make at `4.4` the `fifo:` string stands.
Mutation: drop the sandbox-make probe so the host style is used
verbatim - the `4.3` case keeps `fifo:` and reddens. A live pair on a
make-kind element whose sysroot make is below 4.4, pasted in the
Outcome (or, if this box has only one make, a fake-make sandbox
reading pasted instead, said to be that).
