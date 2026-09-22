# UX-927: a pin is one NAR, so a compiler staged that way reaches outside itself, and nothing in the tree says so

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-915 | **Blocks:** UX-925 | **Found by:** `UX-925` — its Required Fix names the closure walk, the isolation proof and the decompressor as three requirements the `make` pin never had to meet | **Serves:** every pinned component the examples stage, and `UX-925`'s toolchain axis | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`tools/nix_store_fetch.py` stages **one** NAR per pin. That is enough
for `make`, whose only absolute references are its ELF interpreter and
its RUNPATH, both answered by a single symlink into the sysroot's
already-staged glibc (`stage_interpreter_link`, `UX-915`). Measured
2026-09-22, that pin's real closure is not one path:

```text
$ python3 -m tools.nix_closure --plan --root fnvsac4yaw2146ig4p54xnnm6b6alkjw
zstd     30180096  /nix/store/7nbi22...-glibc-2.40-224
xz        1607448  /nix/store/fnvsac...-gnumake-4.4.1     <- the only one staged
zstd       201848  /nix/store/fv5lgy...-xgcc-14.3.0-libgcc
zstd      2078896  /nix/store/hjwppd...-libunistring-1.4.1
zstd       368208  /nix/store/qywg7b...-libidn2-2.3.8
#   5 paths   34436496 bytes unpacked
```

So the mechanism `UX-925` would reuse for a compiler stages 1 path of
5 and works anyway, because the symlink reaches a glibc someone else
staged. A compiler is not that shape. The same walk on the x86_64 gcc:

```text
$ python3 -m tools.nix_closure --plan --root ipr6y28viyqkhkg58rdvy27m01q5j5nh
#  15 paths  317552512 bytes unpacked   (92.9 MiB fetched)
```

gcc, gcc-lib, two libgcc paths, glibc and its `-dev` and `-bin`,
linux-headers, isl, gmp, mpfr, mpc, zlib, libidn2, libunistring. One
NAR of that is a sysroot that compiles by reaching outside itself, and
**nothing in the tree would say so** — it would simply resolve on a
staging host that has the rest.

**Three facts that decide the design**, all measured 2026-09-22:

- **A gcc closure is 100% `zstd`.** All 15 paths. `UX-915` chose `xz`
  deliberately because `lzma` is in the standard library; that choice
  does not carry over, and stdlib alone stages *none* of a compiler.
  `cache.nixos.org` serves no uncompressed NAR (`nar/<narhash>.nar`
  is 404), so the decompressor cannot be dodged.
- **`FileHash` is not the integrity check; `NarHash` is.**
  `glibc-2.40-224` arrives here as 9,099,653 bytes against a declared
  `FileSize: 9096823`, with `FileHash` disagreeing and `NarHash` and
  `NarSize` exact. `gcc-14.3.0-lib`, also `zstd`, agrees on all three.
  `NarHash` is the store path's own content address; `FileHash`
  describes one *compression* of it, which a cache is free to replace.
- **The channel carries one store path per architecture under the same
  name**, the trap `UX-915` already hit with `make`. There are four
  `gcc-14.3.0` paths. `ipr6y28...` is the x86_64 one, identified by
  its `References` naming `7nbi22...-glibc-2.40-224` — the exact glibc
  the x86_64 `make` pin names. `8ybmj60...` names a different
  `glibc-2.40-224` hash under the same version string.

## Required Fix

A closure stager, beside the single-NAR pin rather than replacing it:
walk a `.narinfo`'s `References` transitively, stage every path
reached at its own absolute `/nix/store/<hash>-name` under a
destination root, and verify each against `NarHash`.

**Nothing is relocated.** `UX-925` ruled `patchelf` out — rewriting a
store path breaks the content-address that makes a pin checkable at
all — so the mechanism that keeps the *host's* store out is a bind
mount of the staged store at `/nix/store` inside the sandbox.

**The completeness claim must not be "the build worked".** A green
build says only that *something* answered. The check is static: scan
the staged tree for `/nix/store/<hash>-name` byte references and
report every one the tree does not carry. That runs on a machine with
no Nix at all, which is the point — a path named but not staged is one
the staging host would have answered.

**The decompressor is declared, not assumed.** `zstd` is probed
through the four backends that exist, in order, and the staging fails
by name when none does.

## Out of Scope

`UX-925`'s toolchain axis itself — which gcc is pinned, `-B` and
`--sysroot`, the PATH shim, and which target sysroot owns the start
files, `libgcc`, `libstdc++` and the headers. This is the staging
mechanism that row needs, not the row. `stage_cpp_toolchain.sh` and
`tools/sysroot_manifest.py` are untouched here, so the runtime axis
`UX-914` closed cannot move.

`nix_store_fetch.PINS`' hand-typed hex `sha256` of the `.nar.xz`,
which the `FileHash` finding above says is pinning the wrapper rather
than the content. Both `make` pins verify today; re-pinning them on
`NarHash` is a separate row, filed if it ever reds.

Vendoring a pure-Python `zstd` decoder. It is ~800 lines of bit-level
decoding whose failure mode is a corrupt sysroot, against a dependency
that installs in one line; if the dependency is ever refused, that is
the fallback and this paragraph is where it is recorded.

## Acceptance Test

`tools/nix_closure.py --plan` reports the closure of a store path, and
staging it lands every member at its own `/nix/store/<hash>` name.
`--check` on a staged tree exits 0 when complete and exits 1 naming
the file and the reference when it is not.

`tests/unit/test_the_staged_closure_is_complete.py` is hermetic — the
suite does not reach the network (`tests/conftest.py`), so its NARs
and narinfos are synthesized and served over `file://` — and covers
the two-hop walk, a reference cycle, the `NarHash` gate, the
`FileHash` warning, an unknown compression, and a staged tree with a
reference nothing carries.

The staged closure runs on a machine with **no `/nix` at all**, both
directly through its own loader and through a bind mount of the staged
store at the real `/nix/store`.

## Outcome (round 136, 2026-09-22) — 🟢 Done

**Premise:** held — the single-NAR pin stages 1 path of 5 for `make`
and would stage 1 of 15 for gcc, and the tree says nothing either way.

### The gap, measured

```text
$ ls examples/05-cmake-cpp-toolchain/files/toolchain/nix/store   # before
fnvsac4yaw2146ig4p54xnnm6b6alkjw-gnumake-4.4.1
$ python3 -m tools.nix_closure --plan --root fnvsac4yaw2146ig4p54xnnm6b6alkjw
#   5 paths   34436496 bytes unpacked
$ python3 -m tools.nix_closure --plan --root ipr6y28viyqkhkg58rdvy27m01q5j5nh
#  15 paths  317552512 bytes unpacked        (gcc 14.3.0, x86_64)
```

One of five, and `make` works anyway because `stage_interpreter_link`
symlinks into a glibc `stage_cpp_toolchain.sh` staged from the host.
A compiler has no such single reference. Of gcc's 15, **15 are `zstd`**
— stdlib `lzma` stages none of them, and `nar/<narhash>.nar` is 404, so
the decompressor cannot be dodged.

### After

```text
$ python3 -m tools.nix_closure --root fnvsac4yaw2146ig4p54xnnm6b6alkjw $D
zstd  /nix/store/7nbi22...-glibc-2.40-224
xz    /nix/store/fnvsac...-gnumake-4.4.1
zstd  /nix/store/fv5lgy...-xgcc-14.3.0-libgcc
zstd  /nix/store/hjwppd...-libunistring-1.4.1
zstd  /nix/store/qywg7b...-libidn2-2.3.8          real 1.820s
$ python3 -m tools.nix_closure --check $D
zstd backend    zstandard
staged paths    5                                exit 0
$ [ -e /nix ] || echo "this host has no /nix at all"
this host has no /nix at all
$ unshare -r -m sh -c "mkdir -p /nix/store; mount --bind $D/nix/store \
    /nix/store && /nix/store/fnvsac...-gnumake-4.4.1/bin/make --version"
GNU Make 4.4.1
```

Five of five, in 1.8s. The last two lines are the isolation claim
rather than an illustration: the binary execs at its own absolute store
path, through its own baked-in interpreter, on a machine with no `/nix`
— so nothing it resolved came from a host store, because there is none.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| A1 | `closure()` walks only the root's own `References` | 4 clauses |
| A2 | `dangling_store_refs` returns `[]` | 2 clauses |
| A3 | the `NarHash` gate never fires | 1 clause |
| A4 | an unknown `Compression` passes through undecompressed | 1 clause |
| A5 | `nix32_decode` shifted one bit | 12 clauses |
| A6 | a narinfo naming another store path is accepted | 1 clause |

A5 is the widest because the decoder is checked against the two digests
`UX-915` typed as hex — the pin's two spellings have to agree, so a
decoder that drifts takes the closure walk down with it. A1 is the
defect the row was filed for and A2 the guard that would hide it.

### Deviation from the Required Fix

Two. **`FileHash` is a warning, not a gate**: `glibc-2.40-224` arrives
9,099,653 bytes against a declared 9,096,823 with `FileHash`
disagreeing while `NarHash` and `NarSize` are exact, so gating on it
would refuse a correct store path over its wrapper. **`zstd` is a
declared dependency, not a vendored decoder**: ~800 lines of bit-level
decoding whose failure mode is a corrupt sysroot, against one
`pip install`; the fallback is recorded in Out of Scope.

```text
$ make lint
All checks passed!      (3 findings forced by UX-927: S110, S310, S607)
$ make test
9206 passed, 180 skipped, 1 warning in 299.24s (0:04:59)
```
