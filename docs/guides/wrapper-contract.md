# The wrapper contract (`UX-880`/`UX-881`)

`bga capture run --wrapper-dir PATH` (`UX-881`) lets an operator mount
their own directory of wrapper scripts alongside, or instead of, the
one `bga` ships (`tools/native_trace/wrappers/`). This is what a script
in that directory must do to behave the way the shipped ones do.

## Why a wrapper directory at all

A jobserver-active capture (`--jobserver`) binds a directory read-only
ahead of BuildStream's own `PATH`, so a recipe that invokes a
token-holding tool **by bare name** (`ninja`, `ld.lld`, `gcc`, …) gets
a shim instead of the real tool. `bga`'s own shims cover the tools it
ships; a compiler at a custom prefix, invoked by absolute path
(`/usr/sysroot/bin/gcc-13`) or through `toolchain.cmake`'s
`CMAKE_C_COMPILER`, is never on that `PATH` at all and `--wrapper-dir`
exists for exactly that case: point it at a directory holding your own
shim, named the way the real compiler is invoked.

## The entry point

Every script sources `_common.sh` (shipped alongside the reference
shims — copy it, or write your own that speaks the same entry point)
and calls its one function:

```sh
#!/bin/sh
set -eu
. "$(dirname -- "$0")/_common.sh"
bga_run_wrapped <flag_style> "$@"
```

`bga_run_wrapped` does the rest: finds the real tool further down
`PATH` (never itself — the second half below), reads a jobserver auth
from `MAKEFLAGS`, acquires tokens non-blockingly, runs the real tool
with that width, and returns exactly the tokens it held.

## `<flag_style>`

The one argument `bga_run_wrapped` takes, naming how the real tool
spends the acquired width:

| style | passed to the real tool as | shipped example |
|---|---|---|
| `dashj` | `-j <width>` | `ninja` |
| `threads` | `--threads=<width>` | `ld.lld`, `lld`, `ld.gold`, `mold` |
| `flto` | not a token-holder at all — see below | the `flto/` GCC-driver shims |

`flto` is a different mechanism: it never holds a token. It strips
`--jobserver-auth=…` from the `MAKEFLAGS` it hands the real compiler
(a grandchild across the sandbox boundary cannot open the raw fd) and,
only when `-flto`/`-flto=jobserver`/`-flto=auto` is already in argv,
rewrites it to a static `-flto=$BST_TRACE_LTO_CAP`. It is gated on
`BST_TRACE_FLTO_ACTIVE=1`, set only for a `flto:`-matched element
(`--jobserver-auth-override`), so a bystander element's compiler
invocation is untouched even though the shim is on its `PATH` too.

## Finding the real tool, and never re-entering yourself

A wrapper must skip its own directory when it looks for "the real
tool" — the reference implementation (`bga_find_real` in
`_common.sh`) walks `PATH`, skips its own directory, resolves symlinks
(`readlink -f`), and also skips any candidate whose own first three
lines carry a UX-846 marker (a copy of a wrapper, not a symlink, would
otherwise re-enter). It additionally exports `BGA_WRAPPER_TOOL` and
refuses outright (exit 127) if a process already carries that same
tool name — belt and braces against the loop a symlink or relocated
copy produced in production once (32,000 processes, a container
restart).

## The token-return trap

Tokens acquired must be returned even when the wrapped tool is killed:
the reference sets `trap bga_release EXIT INT TERM HUP` immediately
after acquiring, so the parent shell process (running the tool as a
foreground job, not exec'ing into it for the token-holding styles)
always gives them back. A wrapper that is itself killed (not its
child) leaks until the next audit pass.

## What `--wrapper-dir-mode` changes

- `augment` (default): the operator's directory is mounted **and**
  bound ahead of the shipped one on `PATH` — the shipped `ninja`/
  `ld.lld`/… coverage stays, the operator's own scripts take priority
  for anything they also name.
- `replace`: **only** the operator's directory is mounted, at the same
  path the shipped one would have used. No shipped shims, no shipped
  `flto/` subdir — the operator's directory is theirs to populate
  completely, including a `flto/` shim of their own if they want the
  LTO-cap behaviour above.

## What this cannot validate

`bga` cannot check at runtime that a foreign script actually honours
this contract — a malformed wrapper simply behaves like whatever
`sh` makes of it. A lint-style `--check-wrapper-dir` that greps for
the entry points is a possible follow-up (filed, not built).
