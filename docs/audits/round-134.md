# Round 134 — the examples stage their own make, and a switch with two live arms

Run on 2026-09-21, landed as #252. Two rows closed (`UX-915`,
`UX-916`), both on `bst-examples`' own captures, because neither
reading can run in a session container: there is no `bst` and no
`bwrap`.

```text
closed  UX-915  the examples stage the host's make, so `auto` never meets a 4.4
closed  UX-916  only one make is staged, so the version switch has one live branch
pins    GNU Make 4.4.1 and 4.2.1 from cache.nixos.org, 270M -> 272M
```

**Written retroactively in round 135**, from this round's own committed
records — `UX-915`'s and `UX-916`'s Outcomes and the ledger's round-134
row — and from nothing else. `UX-782` is why `git log` is not a source:
reachability is a property of the clone. Every figure below is quoted
from one of those two Outcomes, where the command that produced it is
also recorded.

## What was wrong, and what replaced it

The host's own `make` was copied verbatim into every sysroot, below
`UX-841`'s cutoff, so `style_for_make_version` read `fd` on every host
this repository has ever run on. The pin replaces it with a binary the
sandbox actually execs:

```text
$ make --version | head -1            -> GNU Make 4.3
$ examples/stage_cpp_toolchain.sh | head -2
Pinned GNU Make 4.4.1 from /nix/store/fnvsac4yaw2146ig4p54xnnm6b6alkjw-gnumake-4.4.1
Staged toolchain to .../05-cmake-cpp-toolchain/files/toolchain (270M)
```

Two catches, both recorded in `UX-915`. `store-paths.xz` indexes **two**
`gnumake-4.4.1` store paths, one per architecture, the name saying
nothing about which — so the pin is keyed on `platform.machine()` and
an unpinned arch is refused rather than defaulted. And the absolute
paths baked into the binary are answered without a glibc closure: one
*relative* symlink at the binary's own `/nix/store/<glibc>/lib` into
the sysroot's staged glibc, sound because both pins stop at
`GLIBC_2.38` against the host's 2.39. The `.nar` cost 60 lines of
reader — no Nix, no daemon, no root, and no `zstd`, since the gnumake
nars are `xz`.

## The switch, crossed both ways in one capture

`UX-916` is the same channel carrying 4.2.1 beside 4.4.1 for one more
247 KB nar, and an element selects a series by PATH alias rather than
store path, so a `.bst` survives a pin bump. `bst-examples` on
`a4541d98`, step 21:

```text
switch-4-2.bst: 'GNU Make 4.2.1\n...' -> 'fd' (UX-916)
switch-4-4.bst: 'GNU Make 4.4.1\n...' -> 'fifo' (UX-916)
giant.bst: off peak 2, auto peak 4, resolved width 2
```

One run, two arms, opposite branches of `style_for_make_version`, and
`grep scrubbed` over that job's whole log returns nothing. It is the
first time the `fifo` branch has run on a real capture.

## What the round got wrong first

`UX-916`'s Outcome was written once against a pre-#248 tree, declared
its third clause blocked and added a `Depends on: UX-913`; both were
withdrawn when `UX-913`'s `_FD_DIRECT_POLICIES` landed and the `cmake`
arm on 4.2.1 kept its raw `fd` instead of being scrubbed. The
self-review below is what caught it, and it could not have been caught
by reading the diff: the claim was about behaviour no guard in the
diff reads.

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| general-purpose | sonnet | `UX-915`/`UX-916` (self-review) | 159k | 61 | 10.3 m | the Important finding needed a direct call into `_compiler_safe_makeflags` with a cached 4.2.1 probe: the Outcome's claim was about behaviour no guard in the diff reads, so reading the diff could not have caught it |

One Important finding and three nits, all four acted on, and the
clause landed as two live arms.
