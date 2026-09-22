# UX-914: the examples' sysroot is the host's own /usr/bin, so what the examples measure is decided by whichever machine staged them

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-913 | **Blocks:** UX-910 | **Found by:** round 132 — `UX-913`'s scrub chain starts at "the sandbox's `make` is the host's", and no row owned that | **Serves:** every example, and every reading taken from one | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`examples/stage_cpp_toolchain.sh` builds the sysroot that examples
05, 06, 10, 11 and 12 run inside by copying this host's own binaries
into it, at their absolute paths, because gcc's internal search paths
are compiled in and not relocatable. Its own header says why that
design was chosen:

```text
staged from this *host's* own installed packages (Ubuntu) rather than
a container/Alpine pull - no docker/debootstrap/network image pull
needed, and this host already has real gcc/g++/cmake/make/binutils
installed
```

That property is real and worth keeping in view: the examples build
today with no network at staging time. What it costs is that **the
toolchain under test is whatever the staging machine happened to
have**, and nothing in the repository says which that was.

**The first bill has already arrived.** `UX-913`'s chain begins with
`style_for_make_version("GNU Make 4.3") -> fd`. 4.3 is not a choice
this repository made; it is what Ubuntu 24.04 ships and what
`/usr/bin/make` therefore is inside every one of these sandboxes:

```text
$ make --version | head -1
GNU Make 4.3
```

`UX-874` downgrades a `fifo:` auth for a make below 4.4 and `UX-878`
then scrubs the `fd` that downgrade produced, so `--jobserver auto`
and `--jobserver off` are the same build on these examples. The
jobserver mode cannot be evaluated on them at all, and which host ran
the staging decides that, silently.

**The second is that the sysroot cannot build anything from source.**
Ruslan's proposal for `UX-913` — build a make 4.4 inside the sandbox
and use it for every element — does not fit in it. Sixteen of the
tools a `./configure && make` needs are absent from `BINARIES`:

```text
$ for t in sed grep awk tr mkdir rm cp mv chmod expr cut basename \
           dirname ls install printf; do
    grep -q "/usr/bin/$t\b" examples/stage_cpp_toolchain.sh || echo -n "$t "
  done
sed grep awk tr mkdir rm cp mv chmod expr cut basename dirname ls install printf
```

So "stage a newer make" is not a line in `BINARIES`; it is a decision
about what the sysroot **is**.

## Required Fix

Choose the base, and record the reading that chose it. The choice is
**two independent axes**, not one four-way pick: the *runtime* (libc,
coreutils and `make`) and the *toolchain* (compiler, binutils,
headers). `stage_cpp_toolchain.sh` fuses them only because it stages
both off one host; nothing else requires that, and the two axes are
blocked on different questions.

### Axis A — the runtime

This is the axis `UX-913` needs. Its chain starts at
`style_for_make_version("GNU Make 4.3")`, and `make` is a runtime
package, not a toolchain one — no compiler choice moves it.

**A1. Stay host-staged, and build one tool.** Build GNU Make 4.4 on
the host during staging and stage it beside the rest. The smallest
change, keeps the no-network property, and closes `UX-913`'s chain.
It fixes nothing else: every other tool stays the staging host's, so
the next version-sensitive finding costs this row again. *Question:
how long does the build add to staging, and where does the source
come from with no network?*

**A2. `debootstrap` a pinned Debian.** glibc, as today, so the
examples' own C++ builds stay the same kind of measurement and their
recorded figures stay comparable. Pins every tool version, `make`
included. *Questions: does it need root or `--foreign` plus a second
pass; how large is the result against today's hardlinked-from-host
~0; and which suite — bookworm's `make` is 4.3, the same wall this
row is about, so only trixie or later answers `UX-913`.*

**A3. Alpine.** The smallest image by a wide margin, and its `make`
is already past the gate:

```text
pkgs.alpinelinux.org/package/v3.22/main/x86_64/make -> 4.4.1-r3
```

So this axis alone closes `UX-913`'s chain. What it costs is musl: a
different libc, so every wall, every artifact size and every symbol
count the examples have recorded is a measurement of a different
program. *Question: which of the repository's recorded example
figures are re-derived, and does anything downstream assume glibc?*

**A4. Adopt freedesktop-sdk's sysroot.** The repository already
builds against it — `.github/workflows/real-project-capture.yml`
captures it weekly and monthly — so the plumbing exists and is
maintained. The blocker is not in that workflow, it is where the
examples are worked on: freedesktop-sdk bootstraps from a 238 MB OCI
seed on `cdn.registry.gitlab-static.net`, which the development
container's egress proxy refuses with a `403` to `CONNECT`, and its
cache at `cache.freedesktop-sdk.io:11001` resets the TLS handshake
through the same proxy — both recorded with their real error text in
`UX-53`. Adopting it would make the examples CI-only. *Question: is
that acceptable, given every example figure in the docs is currently
re-derivable locally?*

**All four of A1..A4 need a host this container cannot reach**,
measured 2026-09-21: `deb.debian.org`, `dl-cdn.alpinelinux.org`,
`ftp.gnu.org` and `cdn.registry.gitlab-static.net` all fail at
`CONNECT` through the egress proxy:

```text
$ curl -sS -o /dev/null -w "%{http_code}\n" -L \
    https://deb.debian.org/debian/dists/trixie/Release
000
```

So the reading that picks the base has to be taken somewhere the
mirror is reachable, or the environment's network policy has to
carry these four first. That is a precondition of this row, not a
finding against any candidate.

### Axis B — the toolchain

Host-staged gcc is in this repository for one reason, which the
staging script's own header states: gcc's internal search paths are
compiled in and not relocatable. **A ready-made cross toolchain does
not have that property.** `crosstool-ng` builds a `--with-sysroot`
toolchain and clang resolves its paths relative to the driver
binary, so either unpacks anywhere inside a sysroot and works. That
is a real answer to the constraint that shaped the current design,
and it is worth its own row. Two costs first:

- **Network at staging.** Both are *builders*, not tarballs, and
  their outputs are GitHub release assets. The repositories clone
  from this container; the assets do not:

  ```text
  git clone --depth 1 .../cross-tools/clang-cross        -> ok, 604K
  curl -L .../cross-tools/clang-cross/releases/latest    -> 403
  ```

  `crosstool-ng` fetches sources and builds a toolchain, so it is
  not a drop-in for a staging script at all. `clang-cross` is a
  `release.yaml` that publishes one `<target>.tar.xz` per target, so
  it is a drop-in *if* the asset can be fetched — which is a network
  policy question, not a design one.

  Its 44 targets carry both libcs, `x86_64-unknown-linux-gnu` and
  `aarch64-unknown-linux-gnu` among them at glibc 2.44 (clang
  22.1.8). **So this axis does not force musl.** Only Alpine as a
  runtime does, and that is axis A. The two are independent.

- **clang is not gcc, and bga already counts them differently.**
  `gcc`/`g++` sit in `ORCHESTRATION_BINARIES`
  (`bst_native_build_tracer.py:4339`) because they are drivers that
  exec `cc1plus`; `clang`/`clang++` sit in `WORK_BINARIES`
  (`:4332`) because clang compiles in-process. No example exercises
  that split today. And `UX-878`'s `_COMPILER_SAFE_POLICIES`
  (`bwrap_shim.py:445`) exists for gcc's `lto-wrapper` grandchild,
  which a clang/`lld` build does not have — so changing the
  compiler changes the very thing `UX-913` is measuring.

Take axis A first, on its own reading, because it is what `UX-913`
is blocked on. Axis B is a separate row, and its argument is
relocatability and a second `arch=` variant without a second
machine — not the jobserver.

## Out of Scope

`UX-913`'s second gate — restoring the auth did not raise `peak`
above 2, and that is its own unfinished reading whatever sysroot runs
underneath it. `UX-910`'s unbanded assertion, which stays wrong on
any toolchain. Axis B itself: picking, fetching or landing a cross
toolchain is its own row, and this one only records why it is a
separate question from the runtime. The real-project capture's own
target choice. Anything about the *host* the examples run on in CI,
as opposed to the sysroot they run inside.

## Acceptance Test

A guard reads the version out of the staged sysroot and compares it
against a version this repository pins, so a staging host whose own
`make` differs cannot change what the examples measure without
reddening. A mutation staging the host's `/usr/bin/make` over the
pinned one must redden it.

`examples/10-jobserver`'s `check_jobserver_decision.py` reports a
style other than the scrubbed one for a `cmake` element, on a host
whose own make is 4.3 — which is the reading that says the sysroot,
not the host, decided it.

Every example figure the documents carry is re-derived and the
deviation recorded, because whichever option wins changes the program
being measured.

## Outcome

**Round 135, 2026-09-22 — the base chosen: per-package pins, not a
base image.** A1-A4 each need a mirror still refused at CONNECT,
re-measured from the development container:

```text
deb.debian.org 000  dl-cdn.alpinelinux.org 000  ftp.gnu.org 000
cdn.registry.gitlab-static.net 000  cache.nixos.org 200  channels.nixos.org 200
```

The last two rows dissolve the four-way pick. `UX-915` proved a Nix
store path fetches and unpacks with no Nix, daemon or root, so a
*component* can be pinned without a base distro and without touching
libc — which is what made A3 cost every recorded figure. The base stays
host-staged, and a component becomes a pin when its version is shown to
decide a reading. `make` was the first (`UX-913`'s chain); nothing else
has been, and pinning on a hypothesis is a filing, not a build.

**The gap.** `make` alone was declared. Three verification logs name
`gcc 13 / cmake 3.28` in prose (`round-10.md`,
`case-study-06-macro-micro.md`, `directions.md`); nothing read them
against a sysroot, and glibc, binutils, coreutils and the shell were
named nowhere.

**The close.** The one `BINARIES` array is now `RUNTIME_BINARIES` and
`TOOLCHAIN_BINARIES`, and `tools/sysroot_manifest.py` declares one row
per package — axis, origin, declared version, the pinned rows read out
of `nix_store_fetch.PINS` rather than typed twice:

```text
runtime:
  glibc      host    2.39  (1 probed, 0 staged)
  coreutils  host    9.4  (4 probed, 4 staged)
  dash       host    dash answers no --version, so the sysroot cannot state it  (0 probed, 1 staged)
  make-4.2   pinned  4.2.1  (1 probed, 1 staged)
  make-4.4   pinned  4.4.1  (2 probed, 2 staged)
toolchain:
  gcc        host    13.3.0  (4 probed, 4 staged)
  binutils   host    2.42  (7 probed, 7 staged)
  cmake      host    3.28.3  (1 probed, 1 staged)
```

Twenty probes over eighteen staged names, one per binary. The first
draft asked `env` for coreutils and the 4.4 alias for `make-4.4`;
staging the host's `/usr/bin/make` over the pin then left it reporting
`4.4.1` and exiting 0. A package-level probe is a proxy for its own
members (fixing guide §5), and `make-4.4` reading `4.3, 4.4.1` is the
per-binary version catching it.

**Two verdicts, not one.** A *pinned* divergence exits 1: the pin did
not take. A *host* divergence warns and reddens the guard — a different
working host is not a broken sysroot, it is a different program under
measurement. Fusing those two is the mistake `UX-913` undid.

**The mutation table.** Each applied, reddened, reverted, re-run green:

```text
M1  declare gcc 13.2.0                      1 failed (staged), check warns, exit 0
M2  drop /usr/bin/cat from the declaration  2 failed (claim + axis)
M3  coreutils onto the toolchain axis       1 failed (axis)
M4  probe one binary per package            1 failed (probed-rather-than-sibling)
M5  host /usr/bin/make over the pin         1 failed, check exit=1
M6  fuse the axes back into one BINARIES    13 failed (the wrapper guard)
```

M6 is the one worth keeping.
`test_a_wrapper_runs_where_coreutils_do_not` builds its sandbox `PATH`
from the script's array, so a regex left matching only the composed
`BINARIES=(...)` would have read zero paths and passed whatever the
wrappers did. Its parser reads both arrays and asserts a non-empty set.

**The deviation: no figure moved.** Re-run end to end, staging reports
the same `272M` and the same pin; the declaration lives in `examples/`,
outside every `files/toolchain` tree, so no cache key moves. Clause 2
was already answered by `UX-916`'s own capture, quoted in its Outcome —
`switch-4-2.bst -> 'fd'` beside `switch-4-4.bst -> 'fifo'` in one run
on a runner whose own `make` is 4.3. Clause 3 is therefore vacuous here
and is the live cost of `UX-922`, which adds one thing to this row's
axis B survey: the nix cache carries gcc 14.3.0 and 15.1.0.
