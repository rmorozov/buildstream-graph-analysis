# UX-918: the wrapper shims open on `dirname`, which a staged-toolchain sandbox has not got

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-846, UX-880, UX-913 | **Found by:** UX-913's first design, measured red on run 35610762079 — nine cmake elements compiled through a shim they could not source | **Serves:** any element that drives LTO under a jobserver, and every future wrapper | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`tools/native_trace/wrappers/_common.sh` is sourced by every wrapper and
opens on external tools:

```sh
bga_self_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
bga_tool=$(basename -- "$0")
```

with `readlink`, `head`, `grep` and `date` further down, all under
`set -eu`. `examples/stage_cpp_toolchain.sh:36` stages exactly

```text
gcc g++ cc c++ cmake make ld ld.bfd as ar ranlib nm strip env sh uname sort cat
```

None of those tools is in it. That is survivable for the held-tool
wrappers — `ninja`, `ld.gold`, `ld.lld`, `lld`, `mold` shadow nothing a
staged sandbox invokes — but the `flto/` subdir shadows `cc`, `gcc`,
`g++` and `c++`, all four of which *are* staged. Putting it on `PATH`
for every cmake element failed `examples/06-macro-micro-optimization`
with exit 255 (`.github/workflows/ci.yml:1409`, run 35610762079):

```text
OK: 11 element key(s) equal with and without the mode's environment
##[error]Process completed with exit code 255.
```

`UX-880` had already recorded this shape in `_wrapper_mount`'s docstring
and narrowed `flto_active` to a matched element to avoid it; `UX-913`
widened it, measured the same 255, and narrowed back. So the shims work
only where an operator's sandbox happens to carry coreutils, and the
`flto` override is undeliverable on exactly the toolchain `examples/`
stages — which is every example in this repository.

## Required Fix

Make `wrappers/_common.sh` and the wrappers that source it run with
nothing but the shell. `dirname`/`basename` are parameter expansions
(`${0%/*}` / `${0##*/}`, the form `wrappers/flto/*` already uses for its
own directory); `bga_find_real`'s `head -3 | grep` is a bounded `while
read` loop; `readlink -f` is already optional; `date +%s.%N` is the
ledger's only use and must not abort the wrapper when absent.

## Out of Scope

Making the shims *defuse* a real `gcc -flto` end to end — that is
`UX-884`'s live ICE reproduction, and this row's guard is argv-level and
sandbox-level only. Do not re-widen `_FD_DIRECT_POLICIES` to mount the
shims by default; that is a separate decision once this row lands.

## Acceptance Test

A guard that runs each wrapper with `PATH` holding only the binaries
`stage_cpp_toolchain.sh:36` stages, and asserts it exits 0 and execs the
real tool. Mutate by restoring one `dirname` call and watch it redden.
Then `examples/06` builds green with `flto_active` forced on for every
cmake element.

## Outcome

Not started.
