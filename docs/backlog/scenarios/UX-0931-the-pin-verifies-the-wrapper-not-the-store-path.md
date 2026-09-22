# UX-931: the pin verifies the compressed wrapper, not the store path, so a cache that re-compresses reds as a broken pin

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-927 | **Blocks:** — | **Found by:** `UX-927` — it named this Out of Scope on one observation, and the closure walk then made it four | **Serves:** every pinned component the examples stage, and the next person to read a red pin | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`nix_store_fetch.PINS` carried one digest per pin, `sha256`, and
`fetch` checked it against the downloaded `.nar.xz` before unpacking.
That is the digest of **one compression** of the store path, not of
the store path. A binary cache may re-compress a path without its
content moving, and `cache.nixos.org` does. Measured 2026-09-22 while
walking closures for `UX-927`, four paths in two closures:

```text
path                  declared     served      FileHash  NarHash
glibc-2.40-224        9,096,823    9,099,653   differs   exact
gcc-14.3.0            (3 of 15 zstd paths in the gcc closure)  differs   exact
gcc-14.3.0-lib        3,025,670    3,025,670   agrees    exact
gnumake-4.4.1           312,636      312,636   agrees    exact
gnumake-4.2.1           252,792      252,792   agrees    exact
```

`NarSize` was exact in every case, and `NarHash` — the store path's own
content address, the thing that makes a pin checkable at all — was
exact in every case. Only the wrapper moved.

**What it costs.** Both `make` pins agree today, so this buys no fix
and repairs no red. It buys a *diagnosis*. When `cache.nixos.org`
re-compresses `gnumake-4.4.1` the way it already has `glibc-2.40-224`,
the old gate fails with `sha256 <a>, pinned <b>` on a pin that is
perfectly correct, and the obvious reading — the pin is broken, or the
cache served the wrong thing — is wrong. `UX-914`'s whole argument is
that a pinned artifact's checkability is what a pin is for; checking
the wrong digest spends that credibility on a false alarm.

This is the same distinction `UX-927` already drew inside
`tools/nix_closure.py`, which gates on `NarHash` and warns on
`FileHash`. The two modules disagreed about what a pin means, and this
closes that.

## Required Fix

Pin the content, warn on the wrapper. Each entry in `PINS` carries
`nar_sha256` (the NAR's own digest) and `nar_size` beside the renamed
`file_sha256`, and the gate moves past the decompressor: a
`nar_sha256` or `nar_size` mismatch is fatal, a `file_sha256`
mismatch prints and continues.

The disk cache is keyed on the content address too. A cache keyed on
the wrapper cannot hold a path whose wrapper moved, which is the same
defect one layer down.

`file_sha256` is kept rather than dropped. A wrapper that moves is
worth knowing about — it is how this was found — and the URL's own
`nix-base32` digest is that same value, which
`test_the_staged_closure_is_complete.py` already reads.

## Out of Scope

`tools/nix_closure.py`, which already gates correctly — this row makes
the single-NAR path agree with it, not the other way round. Re-pinning
on a different channel, moving either `make` version, or the `zstd`
question `UX-927` settled. The examples' sysroot, which stages the
same bytes either way: no figure moves, because nothing about what is
staged changes.

Sharing one verification routine between the two modules. `nix_closure`
imports `nix_store_fetch`, so the reverse import is a cycle, and the
two differ in what they read the digest *from* — a narinfo the cache
serves, against a table this repository types. Fifteen duplicated
lines are cheaper than the seam that would remove them.

## Acceptance Test

`tests/unit/test_the_staged_make_is_the_pinned_one.py` builds a NAR,
compresses it, and serves it over `file://`: a `nar_sha256` that
disagrees raises, a `nar_size` that disagrees raises, a `file_sha256`
that disagrees warns and returns the NAR anyway, and a second fetch
reads the cache after the source file is deleted.

Every pin carries both digests as 64 hex characters and a positive
`nar_size`, so a pin that lost its content digest cannot fall back to
no gate at all.

Both pinned makes fetch from `cache.nixos.org`, verify against
`nar_sha256`, unpack, and report their own versions.

## Outcome (round 136, 2026-09-22) — 🟢 Done

**Premise:** held — the gate read the wrapper, and the wrapper is the
one field of a narinfo a cache is free to change.

### The gap, measured

```text
$ git show HEAD:tools/nix_store_fetch.py | grep -A1 '"sha256"'
                "sha256": ("0e8fca4b762af3cc369c319d7332b84e"
                           "87a298fc259f8bc14e1bfab655ec651e")   <- the .nar.xz
$ python3 -m tools.nix_closure --plan --root 7nbi22pcc92y2fqbkyp7h3srvvklmckb
  declared FileSize 9096823   served 9099653   FileHash differs   NarHash exact
```

Four paths across two closures arrived re-compressed, `glibc-2.40-224`
among them, every one with `NarHash` and `NarSize` exact. Both `make`
pins agree today, so the old gate is not failing — it is checking a
field that can move for reasons that are not a broken pin, and when it
does move the message names the wrong culprit.

### After

```text
$ python3 -c "...fetch_nar(pin, cache) for each pin..."
make-4.2  NAR 1,207,592 bytes  sha256 ok=True  size ok=True
make-4.4  NAR 1,607,448 bytes  sha256 ok=True  size ok=True
$ <staged loader> .../make --version     (both, after unpacking)
GNU Make 4.2.1
GNU Make 4.4.1
```

The gate is now `nar_sha256` and `nar_size`, checked after the
decompressor; `file_sha256` prints `recompressed; nar_sha256 decides`
and continues. The disk cache is keyed on the content address, so a
path whose wrapper moved still hits it. `nix_store_fetch` and
`nix_closure` now mean the same thing by a pin.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| B1 | the `nar_sha256` gate never fires | 1 clause |
| B2 | the `nar_size` check never fires | 1 clause |
| B3 | a `file_sha256` mismatch is fatal again — the old gate | 1 clause |
| B4 | the cache is keyed on `file_sha256`, not the content | 1 clause |
| B5 | a pin carries a `nar_sha256` that is not hex | 1 clause |

Each reddens exactly one clause, which is the discrimination this row
wanted: B3 in particular fails *only* the recompression clause, so
that clause is the whole of the behaviour change and nothing else
silently depended on the old gate.

### Deviation from the Required Fix

One. The two modules still carry their own fifteen-line verify rather
than sharing one: `nix_closure` imports `nix_store_fetch`, so the
reverse import is a cycle, and they read the digest from different
places — a narinfo the cache serves against a table this repository
types. Recorded in Out of Scope rather than taken.

`unpack_nar`, the `.nar.xz` wrapper, lost its last caller when the
decompression moved into `fetch_nar`, so it is gone;
`unpack_nar_data` is what both modules use.

```text
$ make lint
All checks passed!
$ make test
9212 passed, 180 skipped, 1 warning in 309.92s (0:05:09)
```
