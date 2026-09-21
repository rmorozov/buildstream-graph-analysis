# UX-914: the examples' sysroot is the host's own /usr/bin, so what the examples measure is decided by whichever machine staged them

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-913 | **Blocks:** UX-910 | **Found by:** round 132 — `UX-913`'s scrub chain starts at "the sandbox's `make` is the host's", and no row owned that | **Serves:** every example, and every reading taken from one | **Topic:** guards | **Area:** tools | **Shape:** judgement

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

Choose the base, and record the reading that chose it. Four
candidates, each with the question it has to answer first. None is
obviously right and this row does not pick one.

**1. Stay host-staged, and build one tool.** Build GNU Make 4.4 on
the host during staging and stage it beside the rest. The smallest
change, keeps the no-network property, and closes `UX-913`'s chain.
It fixes nothing else: every other tool stays the staging host's, so
the next version-sensitive finding costs this row again. *Question:
how long does the build add to staging, and where does the source
come from with no network?*

**2. `debootstrap` a pinned Debian.** glibc, as today, so the
examples' own C++ builds stay the same kind of measurement and their
recorded figures stay comparable. Pins every tool version, make
included. *Questions: does it need root or `--foreign` plus a second
pass; how large is the result against today's hardlinked-from-host
~0; and does gcc's compiled-in search path still resolve when the
sysroot is no longer the host's layout?*

**3. Alpine.** The smallest image by a wide margin. But musl is a
different libc, so every wall, every artifact size and every symbol
count the examples have recorded is a measurement of a different
program. *Question: which of the repository's recorded example
figures are re-derived, and does anything downstream assume glibc?*

**4. Adopt freedesktop-sdk's sysroot.** The repository already builds
against it — `.github/workflows/real-project-capture.yml` captures it
weekly and monthly — so the plumbing exists and is maintained. The
blocker is not in that workflow, it is where the examples are worked
on: freedesktop-sdk bootstraps from a 238 MB OCI seed on
`cdn.registry.gitlab-static.net`, which the development container's
egress proxy refuses with a `403` to `CONNECT`, and its cache at
`cache.freedesktop-sdk.io:11001` resets the TLS handshake through the
same proxy — both recorded with their real error text in `UX-53`.
Adopting it would make the examples CI-only. *Question: is that
acceptable, given every example figure in the docs is currently
re-derivable locally?*

## Out of Scope

`UX-913`'s second gate — restoring the auth did not raise `peak`
above 2, and that is its own unfinished reading whatever sysroot runs
underneath it. `UX-910`'s unbanded assertion, which stays wrong on
any toolchain. The real-project capture's own target choice. Anything
about the *host* the examples run on in CI, as opposed to the sysroot
they run inside.

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
