# Round 137 — a prefix this repository can name

Run on 2026-09-22 from `3fa407a`. One row closed (`UX-925`), whose
title is a prediction the round falsified. No track ran; the session
did the work itself.

```text
closed   UX-925   the toolchain axis is this host's gcc, because gcc is not relocatable
pins     gcc 14.3.0, binutils 2.44, cmake 4.1.2 - 37 store paths, 420 MiB
classes  9 of 9 read from the half they declare, against 7 on a host tree
```

## The premise was "a second machine", and the answer was a name

`UX-925` was filed by `UX-914` with a real constraint behind it: gcc's
search paths are string constants compiled in at its configure prefix,
so a toolchain cannot simply be copied somewhere else and asked to
work. The row read that as a hardware problem — a second `arch=`
variant would need a second machine — and the measurement that closes
it changes only one word. The paths are not relocatable, but they do
not have to be: a nix gcc is *already* configured at
`/nix/store/<hash>-gcc-14.3.0`, so staging the closure at exactly that
path makes the compiled-in constants correct. `patchelf` was the route
that looked obvious and cannot work — it edits `PT_INTERP` and
`RUNPATH` only, never a string constant, and rewriting a store path
breaks the content address it is named by.

So the pin is the stock closure, unmoved, and what the repository
supplies is `UX-930`'s parameters pointed at it.

## `-B` is five directories, not three

`UX-930` measured three prefixes on a host-staged tree and that was
the whole truth available there, because a host tree puts the
assembler and the linker on `PATH` where no flag is needed. On the
pin they are inside a store path, and the reading changes:

```text
gcc-libexec  <gcc>/libexec/gcc/x86_64-unknown-linux-gnu/14.3.0   cc1, cc1plus
gcc-libdir   <gcc>/lib/gcc/x86_64-unknown-linux-gnu/14.3.0       libgcc.a
gcc-lib      <gcc-14.3.0-lib>/lib                                libstdc++, libgcc_s
binutils     <binutils-2.44>/bin                                 as, ld.bfd
glibc        <glibc-2.40-224>/lib                                crt1.o
```

Drop the fourth and `as` resolves to the bare name on the host's
`PATH`; drop the third and the link cannot find `-lgcc_s`. That is
why `assembler` and `linker` are classes at all — they are invisible
until a pin makes them askable. Nine classes of nine now answer from
the half they declare, and `cxx-headers` is the one that moved:
`include/c++` lives in gcc's own store prefix, and the driver reaches
it by `argv[0]` relocation with no flag at all, so it is
**toolchain-owned** and `--sysroot` never touches it.

## Two glibcs, declared rather than hidden

The pin links against its own glibc, and bakes
`/nix/store/<glibc>/lib64/ld-linux-x86-64.so.2` into every binary it
produces. That is a second libc in a tree `UX-914` declared as having
one. The round did not hide it behind the runtime rows: the closure's
glibc is a new `glibc-pinned` row on the **toolchain** axis, so the
four runtime rows stay byte-identical — a test writes them out
literally, and a runtime-axis change reddens — while the new fact is
stated where a reader looks. Example output loads 2.40; the tree's
`sh` and coreutils load the host-staged 2.39; the linked app needs at
most `GLIBC_2.34`.

## The mutation table

Each applied, reddened, reverted, re-run green:

```text
A1 a host `gcc` copied over the driver shim    ...StagedOverThePin, 2
A2 a host `cc1plus` over the pin's             ...StagedOverThePin, 1
A3 the binutils store path removed             ...StagedOverThePin, 1
A4 `ld.bfd` gone, so `-B` writes at nothing    ...FromTheClosure, 2
A5 the shim rooted at the tree, not `/`        ...TheSandbox, 1
A6 a host path back in TOOLCHAIN_BINARIES      ...PinIsDeclared, 1
```

A1 is the one worth keeping, because the obvious guard cannot see it.
The version probes ask the driver, and a shim's `/nix/store` flags
resolve only inside the sandbox — so a host `gcc` dropped over the
shim execs the pin's own binaries and answers every probe correctly.
`shim_divergences` reads the file instead of trusting its output, and
the stager runs it.

## The fixture that could build the wrong tree

`UX-930`'s own failure on `#261` was a `cp` fallback landing the clone
one level under itself, so every glob returned `[]` and every class
read as missing — the row's thesis one level down. This round hit the
same shape from the other side and worse: the new mutation fixture
clones with hardlinks and wrote *through* them, so two mutations
corrupted the real staged sysroot with a host `cc1plus` and a mangled
shim. `_replace` unlinks before writing. `make test` is not read-only,
and a sandbox that shares inodes with the tree is not a sandbox.

One defect next door, found the same way: `sysroot_manifest.measure`
probes in a scratch directory, so a **relative** `dest` produced a
relative argv resolving against that scratch and all nineteen rows
read `did not run` — green, and meaningless. Guarded.

## What is owed

The examples are not captured here: this container has neither `bst`
nor `bwrap`, so "every figure re-derived" is unpaid. The substitute
is stronger than a build succeeding — example 05's six cmake projects
configured, compiled, linked, installed and the app **ran** inside a
`chroot` of the staged tree alone, nothing of this host but `/proc`
and `/dev/null` — but it is a substitute, and the Outcome says so.

## Agents

There were **no agents launched** in this round. `UX-925`'s shape
derives `judgement` and the session took it in context: the work is
one decomposition — which half owns which class — and every step of
it reads back a measurement that the next step depends on, so a
briefed track would have been re-briefed at each reading. The ledger
has no row to carry.
