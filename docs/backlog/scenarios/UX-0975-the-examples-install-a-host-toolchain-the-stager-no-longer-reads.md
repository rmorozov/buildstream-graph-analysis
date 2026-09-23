# UX-975: the examples still install a host toolchain the stager no longer reads, and two CI comments say it copies from one

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-925 | **Blocks:** — | **Found by:** architecture review 26 (2026-09-23) — `UX-925` emptied the stager's toolchain array and the four sentences that told a reader to install one stayed | **Serves:** whoever stands the C++ examples up from `examples/README.md`, and the next reader of `ci.yml`'s staging steps | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

Since `UX-925` the stager copies five runtime binaries off the host and
nothing on the toolchain axis:

```text
$ grep -n "^\s*/usr/bin/env\|^TOOLCHAIN_BINARIES" -A1 examples/stage_cpp_toolchain.sh
54:  /usr/bin/env /usr/bin/sh /usr/bin/uname /usr/bin/sort /usr/bin/cat
56:TOOLCHAIN_BINARIES=(
57-)
$ grep -n "/usr/share\|/usr/lib/gcc\|/usr/include\|print-prog-name\|print-file-name" \
    examples/stage_cpp_toolchain.sh | grep -v "^\s*[0-9]*:#"
$                                                   # nothing
```

gcc, binutils and cmake come from `tools/nix_toolchain.py`'s pinned
closure. Four sentences still say the host's own packages are the
source:

```text
$ grep -n "build-essential" examples/README.md
191:sudo apt-get install -y build-essential cmake
243:sudo apt-get install -y build-essential cmake
$ grep -n "copy from\|THIS runner's own" .github/workflows/ci.yml
1104:        # the host to copy from.
1240:        # A full real sysroot staged from THIS runner's own installed
```

`ci.yml:1101-1104` says `cmake` is installed "because staging the
example toolchain below needs it on the host to copy from", and
`:1240-1243` that the sysroot is "staged from THIS runner's own
installed build-essential/cmake packages". `examples/README.md`'s `05`
and `06` blocks open with the same `apt-get` line, directly below the
section `UX-925` rewrote to say the toolchain axis is entirely pinned.

`build-essential` is still needed elsewhere - the hook and spine
compile on the host (`tools/bga_doctor.py:152`) - so the `ci.yml` jobs
that run those tests keep it. `cmake` has no host reader left in the
stager.

## Required Fix

Correct the two `ci.yml` comments and the two README blocks to what the
stager reads: the runtime axis off the host, the toolchain from the pin.
Whether the three `apt-get` lines (`ci.yml:954`, `:1105`, `:1221`) drop
`cmake` is a CI reading, not a reading this container can take: drop it
on a branch and let `bst-examples` say.

## Out of Scope

The stager's own header, which `UX-925` already rewrote.
`real-project-capture.yml`'s prerequisites. A guard over free prose.

## Acceptance Test

```text
grep -n "copy from\|THIS runner's own" .github/workflows/ci.yml   # nothing
grep -n "build-essential cmake" examples/README.md                # nothing, or a line saying what it is for
```

and, if `cmake` is dropped from an `apt-get` line, `bst-examples` green
on that branch.

## Outcome
