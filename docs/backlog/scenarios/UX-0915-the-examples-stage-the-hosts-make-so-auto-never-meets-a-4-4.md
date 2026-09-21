# UX-915: the examples stage the host's own make, so `--jobserver auto` has never met a make 4.4

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-914 | **Blocks:** UX-913 | **Found by:** round 133 — Ruslan split `UX-913`'s remedy into a fast unblock and a corner-case row (2026-09-21); this is the fast one | **Serves:** every example whose element joins the jobserver | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`UX-913`'s scrub chain begins at one reading:

```text
style_for_make_version("GNU Make 4.3") -> fd
```

4.3 is not a choice this repository made. It is what Ubuntu 24.04
ships, what `examples/stage_cpp_toolchain.sh` copies into every
example's sysroot, and therefore what `/usr/bin/make` is inside every
sandbox those examples build in. `UX-874` downgrades a `fifo:` auth for
a make below 4.4 and `UX-878` then scrubs the `fd` that downgrade
produced, so **the `fifo` pool-fill path has never run in this
repository's own examples**.

`giant.bst` carries a `public: bga: jobserver-auth: fd` annotation
(`a14ba0c1`) that forces the style past the scrub. That was the right
move to isolate the second gate, and it is a per-element override
standing in for a host fact: on a make 4.4 no override is needed,
because no downgrade happens and nothing is scrubbed.

## Required Fix

Build GNU Make 4.4.x on the host during `stage_cpp_toolchain.sh`, stage
it at the path the sandbox's `make` resolves, and pin the version in
this repository so the staging host's own `make` cannot decide what the
examples measure.

The open question is where the source comes from. `ftp.gnu.org` is
refused at `CONNECT` from the development container, measured
2026-09-21:

```text
$ curl -sS -o /dev/null -w "%{http_code}\n" -L https://ftp.gnu.org/gnu/make/
000
```

So this row needs either `UX-914`'s network precondition carried, or a
vendored source with its checksum in the tree. Pick one and record the
reading that picked it; the rest of this row does not depend on which.

**Settled 2026-09-21: the source is the Nix binary cache, and it is a
download rather than a build.** `*.nixos.org` is already in the
environment's Trusted allowlist, so no policy change and no vendoring
is needed. Measured from the development container:

```text
cache.nixos.org 200 · releases.nixos.org 200 · hydra.nixos.org 200
  (bare nixos.org is 000 - subdomains only)
channels.nixos.org/nixos-25.11/store-paths.xz -> 216,353 paths, incl.
  /nix/store/1kxihdh72rdyl170dh19zka2nmd179cc-gnumake-4.4.1
  /nix/store/4320g8b6bl4wpgbmk0mdjr3rr2jr4xh6-gnumake-4.2.1
cache.nixos.org/1kxihdh....narinfo
  References: gnumake-4.4.1 glibc-2.40-224 · FileSize 302608
cache.nixos.org/nar/1jkn9z....nar.xz -> 302 KB -> 1.66 MB, "GNU Make" in it
```

This supersedes both earlier candidates - building from `ftp.gnu.org`
(refused) and the `mirror/make` + `coreutils/gnulib` clone pair (works,
but needs a gnulib bootstrap and `autopoint`/`gettext`/`makeinfo`,
none of which the host has). Keep them as fallbacks, not the plan.

Two constraints the implementation carries. A Nix store path is
absolute and baked into each binary's interpreter and RPATH, so the
sandbox must carry `/nix/store` at that exact path - stage the closure
there rather than relocating it, which is *more* reproducible than
today's host staging, not less, since the paths are content-addressed
and pinned. And unpacking a `.nar` needs either Nix (root, a daemon)
or a small reader; write the reader, walking the closure through each
narinfo's `References` field.

## Out of Scope

Everything else in the sysroot — that is `UX-914`'s axis A, and this
row deliberately moves one tool rather than settling the base.
Staging 4.3 *and* 4.4 to cover the version switch on any host, which is
`UX-916`. `UX-913`'s second gate, which is why `peak` stayed at 2 with
the auth kept and is unaffected by which make is staged.

## Acceptance Test

A guard reads the version out of the staged sysroot and compares it
against the version this repository pins. A mutation staging the host's
own `/usr/bin/make` over the pinned one must redden it.

`examples/10-jobserver`'s `check_jobserver_decision.py` reports a
`fifo` style for a `cmake` element on a host whose own make is 4.3 —
the reading that says the sysroot, not the host, decided it.

And the sharpest one: `giant.bst`'s `public: bga: jobserver-auth: fd`
annotation is **removed**, and `examples/11-serial-giant`'s
`check_jobserver_width.py` still reports no scrubbed auth. An override
that is no longer needed is the proof that the host fact is gone.

## Outcome

**Round 134, 2026-09-21 — closed on CI's own capture.** Neither
example reading can run in a session container (no `bst`, no `bwrap`),
so the close is `bst-examples`' run on `33884772`.

**The gap and the close.** The host's own make was copied verbatim
into every sysroot, below `UX-841`'s cutoff, so `style_for_make_version`
read `fd` on every host this repository has run on. The pin replaces it
with a binary a sandbox actually execs, run through the interpreter
symlink the staging leaves behind rather than trusted from the table:

```text
$ make --version | head -1            -> GNU Make 4.3
$ examples/stage_cpp_toolchain.sh | head -2
Pinned GNU Make 4.4.1 from /nix/store/fnvsac4yaw2146ig4p54xnnm6b6alkjw-gnumake-4.4.1
Staged toolchain to .../05-cmake-cpp-toolchain/files/toolchain (270M)
```

**A trap in the source.** `store-paths.xz` indexes two `gnumake-4.4.1`
store paths, one per architecture, the name saying nothing about which:

```text
$ file .../1kxihdh.../bin/make -> ELF ... ARM aarch64
$ file .../fnvsac.../bin/make  -> ELF ... x86-64
```

So the pin is keyed on `platform.machine()`, an unpinned arch refused
rather than defaulted. The absolute-path catch is answered without a
glibc closure: `stage_interpreter_link` writes one relative symlink at
the binary's own `/nix/store/<glibc>/lib` into the sysroot's staged
glibc, sound because both pins stop below the host's:

```text
$ objdump -T .../{fnvsac,4320g8b}.../bin/make | grep -oP 'GLIBC_[0-9.]+' | sort -V | tail -1
GLIBC_2.38   (both pins)
$ ldd --version | head -1
ldd (Ubuntu GLIBC 2.39-0ubuntu8.7) 2.39
```

The `.nar` catch cost 60 lines of reader - no Nix, no root, no `zstd`,
since the gnumake nars are `xz`.

**Mutations.** `tests/unit/test_the_staged_make_is_the_pinned_one.py`:

| mutation | guard | result |
|---|---|---|
| the host's `/usr/bin/make` copied over the pinned symlink | `test_usr_bin_make_resolves_into_the_pinned_store_path`, `test_the_staged_make_reports_the_pinned_version` | 🔴 `assert 'GNU Make 4.3' == 'GNU Make 4.4.1'` |
| `sandbox_make` written as the probe's whole stdout | `test_only_the_first_line_of_make_s_own_output_lands` | 🔴 |

Reverted, 6 passed.
**Both capture readings, from `bst-examples` on `33884772`.** A cmake
element on a real sandbox taking the branch that had never run here,
and a silence where the scrub line used to be:

```text
core.bst decision: {'auth_style': 'fifo', 'decision': 'joined',
 'element': 'core.bst', 'kind': 'cmake', 'policy': 'cmake_meson',
 'max_jobs': 4, 'sandbox_make': 'GNU Make 4.4.1\n...'}
giant.bst: off peak 2, auto peak 4, resolved width 2 (UX-913: exceeded)
off=123.00s auto=122.59s
```

`grep scrubbed` over that job's whole log returns nothing, with the
four `jobserver-auth: fd` annotations gone - removed here and,
independently, by `UX-913` (#248), so the merged diff has no `.bst`
change.

`sandbox_make` ends `\n...` because `probe_make` caches the whole
stdout, so the first run to publish the key put six lines of GPL
notice in one field. Only the first line lands now.

**Deviation from the Required Fix.** One. The fix says "build GNU Make
4.4.x on the host"; this downloads a pinned, content-addressed binary,
which the Required Fix pre-authorises ("a vendored source with its
checksum in the tree. Pick one and record the reading that picked
it") - a checksum over a binary rather than a source.

**Suite.** Green since `UX-917` landed on `main`; this branch's full
run is in the pull request.
