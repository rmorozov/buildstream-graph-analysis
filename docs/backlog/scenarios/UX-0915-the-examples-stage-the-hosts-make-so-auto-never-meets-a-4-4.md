# UX-915: the examples stage the host's own make, so `--jobserver auto` has never met a make 4.4

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-914 | **Blocks:** UX-913 | **Found by:** round 133 — Ruslan split `UX-913`'s remedy into a fast unblock and a corner-case row (2026-09-21); this is the fast one | **Serves:** every example whose element joins the jobserver | **Topic:** guards | **Area:** tools | **Shape:** judgement

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
