# UX-930: the toolchain's two parameters are assumed rather than read back, and the one that decides which `cc1` runs fails silently

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-914 | **Blocks:** UX-925 | **Found by:** `UX-925` — its `-B`/`--sysroot` route names a silent-fallback hazard and owes two readings | **Serves:** every example, and the comparison class a `variant` dimension names | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`UX-925` proposes not relocating the pinned toolchain but
parameterizing it: `-B` for the exec prefix, `--sysroot` for the
target parts. Both flags are silent when they are wrong, and they are
silent in *different* ways. Measured on this host's gcc 13.3.0,
pointing each flag at an empty directory:

```text
$ gcc -B <empty> -print-prog-name=cc1
/usr/libexec/gcc/x86_64-linux-gnu/13/cc1       <- the compiled-in prefix
$ gcc -B <empty> h.c -o h        exit 0, 0 bytes on stderr
$ gcc --sysroot=<empty> h.c -o h exit 1
h.c:1:10: fatal error: stdio.h: No such file or directory
```

`--sysroot` is self-checking for a program that includes anything;
`-B` is not. A `-B` at a directory with no `cc1` compiles the whole
example against **the staging host's compiler** and says nothing —
`UX-914`'s shape exactly, one layer down, and the layer that decides
what the measured program is.

**Which flag moves what is a property of the driver, not of gcc.**
Ubuntu's 13.3.0 is configured with no `--with-sysroot`
(`--prefix=/usr --program-prefix=x86_64-linux-gnu- --libexecdir=/usr/libexec`),
and on it `--sysroot` moves the C headers and nothing else:

```text
                          no flags                    --sysroot=<tree>
crt1.o        /usr/lib/x86_64-linux-gnu/crt1.o   unmoved
libc.so       /usr/lib/x86_64-linux-gnu/libc.so  unmoved
libgcc.a      /usr/lib/gcc/.../13/libgcc.a       unmoved
libstdc++.so  /usr/lib/gcc/.../13/libstdc++.so   unmoved
C headers     /usr/include                       <tree>/usr/include
C++ headers   /usr/include/c++/13                unmoved
```

`-B` moves the link-time file search as well as the programs
(`-B <dir> -print-file-name=crt1.o` reports `<dir>/crt1.o`), and the
C++ headers move under neither flag — they are an absolute
`--with-gxx-include-dir`. A differently configured driver answers
differently, so the per-file-class ownership `UX-925` asks for is a
**reading**, not a table anyone can write once.

**`-print-file-name` answers with `..` hops.** `crt1.o` comes back as
`/usr/lib/gcc/x86_64-linux-gnu/13/../../../x86_64-linux-gnu/crt1.o`,
which *starts with* the gcc libdir and normalizes to
`/usr/lib/x86_64-linux-gnu/crt1.o`. A prefix match on the raw string
reads every start file as toolchain-owned — a proxy for the thing it
names, fixing guide §5.

## The two readings `UX-925` owed

**1. `make_relative_prefix` relocates a whole-tree move.** The row's
own title says gcc's search paths are not relocatable. For a *whole
tree* that is wrong: the driver derives its prefixes from `argv[0]`,
so a tree copied elsewhere finds its own helpers, its own `libgcc`
and its own internal headers, and links and runs:

```text
$ cp -a <driver> <tree>/usr/bin/gcc
$ cp -a /usr/libexec/gcc/x86_64-linux-gnu/13 <tree>/usr/libexec/gcc/x86_64-linux-gnu/
$ cp -a /usr/lib/gcc/x86_64-linux-gnu/13     <tree>/usr/lib/gcc/x86_64-linux-gnu/
$ <tree>/usr/bin/gcc -print-prog-name=cc1
<tree>/usr/bin/../libexec/gcc/x86_64-linux-gnu/13/cc1
$ <tree>/usr/bin/gcc -E -v empty.c   # #include <...> starts here:
<tree>/usr/lib/gcc/x86_64-linux-gnu/13/include
 /usr/local/include   /usr/include/x86_64-linux-gnu   /usr/include
$ <tree>/usr/bin/gcc t.c -o t && ./t     LINK OK, RUN OK
```

Same answer through `PATH` and through a bare `./gcc`. What does *not*
move is the target half — the three absolute entries above. So the
premise to keep is narrower than the row's title: **gcc relocates its
own half and never the target's**, which is the same seam `-B` and
`--sysroot` cut along. It does not make a staged nix closure
prefix-free: the closure's binaries still name absolute interpreters
and RUNPATHs, which is the loader's problem, not the driver's.

**2. What the shim costs.** A `#include <stdio.h>` compile-and-link,
under `strace -f -e trace=execve,clone`:

```text
            execve   clone   output
direct        16       0     ref
via shim      17       0     byte-identical to ref
shim size    305 bytes
```

One `execve`, no process, identical bytes — the ledger cost `UX-925`
predicted, now measured.

## Required Fix

Declare both parameters and read them back, on whatever toolchain the
sysroot carries — the host's today, `UX-925`'s pinned closure when it
lands. `tools/toolchain_params.py`:

- one row per **file class** (exec prefix, `libgcc`, gcc's own
  headers, the start files, `libstdc++`, the C headers, the C++
  headers), each declaring its owner — `toolchain` or `sysroot` — and
  the question that asks the driver where the file really came from;
- the answer normalized before it is classified, so the `..` hops
  above cannot read a start file as the toolchain's;
- `--check <sysroot>`, which exits 1 on a class whose measured owner
  is not its declared one, in `stage_cpp_toolchain.sh` beside
  `sysroot_manifest --check`;
- `--shim`, which writes the PATH shim: shell-only, `exec`, the
  driver's absolute path and both flags baked in by the writer rather
  than read from the environment at run time. It needs no `PATH`
  search past itself, so `UX-846`'s recursion hazard does not arise
  and `_common.sh` is not sourced.

## Out of Scope

`UX-925`'s store closure — the transitive `References` staging, the
decompressor, and keeping the host's `/nix/store` out of the build.
This row is the parameterization half and lands against the toolchain
already staged. The runtime axis, closed by `UX-914`. Choosing the
pinned gcc's store path. Re-deriving the examples' figures, which is
`UX-925`'s to do when the compiler actually changes.

## Acceptance Test

`python3 -m tools.toolchain_params --check <sysroot>` prints one row
per file class with its measured owner, and exits 0 on the sysroot
`stage_cpp_toolchain.sh` stages today.

`tests/unit/test_the_toolchain_parameters_are_read_back.py` reddens
under the mutation that matters: a shim whose `-B` points at a
directory holding no `cc1` — the case that exits 0 and says nothing —
and under a classifier that skips the normalization.

The shim runs on a `PATH` holding only what
`examples/stage_cpp_toolchain.sh` stages, read from its own axis
arrays rather than a copy of them (`UX-918`'s harness), and passes
both flags through to the driver with the argv unchanged.

## Outcome (round 136, 2026-09-22) — 🟢 Done

**Premise:** held — and half of `UX-925`'s title falsified with it.
`make_relative_prefix` **does** relocate a whole-tree move through
`argv[0]`: a copied tree's driver found its own `cc1`, `libgcc` and
internal headers and linked a running binary, through `PATH`, an
absolute path and `./gcc` alike. Only the target's half stays.

### The gap, measured

Nothing asked where a file class came from, and neither flag says:

```text
$ gcc -B <empty> -print-prog-name=cc1
/usr/libexec/gcc/x86_64-linux-gnu/13/cc1       <- the compiled-in prefix
$ gcc -B <empty> h.c -o h    exit 0, 0 bytes on stderr
```

`-B` at a directory with no `cc1` compiles the whole example against
the host's compiler; `--sysroot` at least fails the `#include`.

### After

```text
$ python3 -m tools.toolchain_params --check <sysroot>
-B<sysroot>/usr/libexec/gcc/x86_64-linux-gnu/13/
-B<sysroot>/usr/lib/x86_64-linux-gnu/
-B<sysroot>/usr/lib/gcc/x86_64-linux-gnu/13/
--sysroot=<sysroot>
  exec-prefix  toolchain toolchain  <sysroot>/usr/libexec/.../13/cc1
  libgcc       toolchain toolchain  <sysroot>/usr/lib/gcc/.../13/libgcc.a
  gcc-headers  toolchain toolchain  <sysroot>/usr/lib/gcc/.../13/include/stddef.h
  start-files  sysroot   sysroot    <sysroot>/usr/lib/x86_64-linux-gnu/crt1.o
  libstdc++    toolchain toolchain  <sysroot>/usr/lib/gcc/.../13/libstdc++.so
  c-headers    sysroot   sysroot    <sysroot>/usr/include/stdio.h
  cxx-headers  sysroot   mounted    /usr/include/c++/13/vector
toolchain_params: cxx-headers answers /usr/include/c++/13/vector, which
no parameter moves - the sandbox answers it from the tree (UX-930).
exit 0
```

Two numbers came out of it. **`-B` is three directories, not one**:
the libexec prefix alone leaves five of seven classes on the host, and
adding the gcc libdir still leaves the start files. And **six classes
of seven carry** — the C++ headers move under neither flag, so they
are declared in `UNREADABLE_HERE` rather than excused silently.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | `-B` pointed at a directory with no `cc1` | `TestAParameterShort...`, 3 |
| A2 | `return answer` for `os.path.normpath(answer)` | `...NormalizesFirst`, 1 |
| A3 | `flags_for` writes a `-B` for a prefix that is not there | `...NeverWrittenAtNothing`, 1 |
| A4 | every `mounted` answer excused, not only the declared one | `...OnlyAClassNoParameter...`, 2 |
| A5 | the header probe left canonicalizing | `...not_its_realpath`, 1 |

A guard of my own that did not discriminate: g++'s **first** include
directory as the C++ header class. It reads gcc's internal directory
whenever the C++ ones are absent, and they go absent without a word.
Replaced by `-H` on a real `#include <vector>`.

One defect it found in its own instrument: a **relative** `dest` made
relative `-B` flags whose answers sat outside the absolute tree and
read as the host's — this row's failure shape, from the inside. Each
prefix is found under either layout now, `/usr` or a closure's own
`/nix/store/<hash>`: `UX-925`'s staged closure keeps the start files
in **glibc's** path, not gcc's.

### Deviation from the Required Fix

The shim is written by `--shim` and **not installed**. Installing it
today shadows the driver with a shim pointing at the same tree: one
more `execve` per compile (measured 16 to 17) for no change in what is
compiled, re-dating every figure. It installs when the pin moves.

```text
9210 passed, 175 skipped in 400.73s     make test
All checks passed!                      make lint
```
