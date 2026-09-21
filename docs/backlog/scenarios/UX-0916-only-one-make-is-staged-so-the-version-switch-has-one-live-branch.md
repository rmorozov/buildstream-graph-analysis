# UX-916: only one make is ever staged, so `style_for_make_version`'s two branches are never both exercised

**Priority:** Medium | **Status:** 🟡 In Progress | **Depends on:** UX-915, UX-913 | **Found by:** round 133 — Ruslan asked for the corner cases to be covered after the fast unblock lands (2026-09-21) | **Serves:** every host that runs the examples, whatever its own make | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`style_for_make_version` has two outcomes, `fifo` and `fd`, and which
one a capture takes is decided by whichever single `make` the staging
host happened to have. Today that is 4.3 everywhere, so the `fd` branch
is the only one with a live example behind it; after `UX-915` it will
be 4.4 everywhere and the `fd` branch loses its example instead. One
staged make can only ever exercise one branch, and a repository whose
examples measure what the host decided is exactly the defect `UX-914`
names.

`UX-874`, `UX-878`, `UX-879` and `UX-880` all turn on this switch. None
of them has an example that crosses it.

## Required Fix

Stage both a 4.3 and a 4.4, and give an example a way to say which one
its elements build against, so a single run crosses the switch in both
directions on any host. Whether that is two toolchain elements in one
example, two examples, or a variable the project declares is a choice
this row makes with a reading rather than up front.

Whatever it is, the selection has to be visible in the report: a
capture that took the `fd` path and one that took `fifo` must be
distinguishable without reading the workflow that produced them.

## Out of Scope

Staging make 4.4 at all, which is `UX-915` and comes first. The rest of
the sysroot (`UX-914`). Changing any jobserver default, and `UX-913`'s
second gate.

## Acceptance Test

One CI run captures the same element under both staged makes and the
two captures report different styles, each the one its version implies.
A mutation pointing both arms at the same make must redden the guard
that holds them different — a switch with one live branch is what this
row exists to end, so a guard that passes when both arms agree guards
nothing.

`examples/11-serial-giant`'s `check_jobserver_width.py` reports no
scrubbed auth under either arm.

## Outcome

**Round 134, 2026-09-21 — two of the three clauses are in, and the
third turned out to depend on `UX-913`.** Status 🟡.

**Both makes are staged.** The same channel carries 4.2.1 beside
4.4.1, both `x86_64`, both referencing one glibc, so the second pin
costs one 247 KB nar:

```text
$ examples/stage_cpp_toolchain.sh | head -3
Pinned GNU Make 4.4.1 from /nix/store/fnvsac4yaw2146ig4p54xnnm6b6alkjw-gnumake-4.4.1
  staged GNU Make 4.2.1 as /usr/lib/bga-make/4.2/make
  staged GNU Make 4.4.1 as /usr/lib/bga-make/4.4/make
```

The selection mechanism is that alias, not a store path: an element
puts `/usr/lib/bga-make/4.2` ahead of `/usr/bin` on its own `PATH`, so
a `.bst` file names a version series and survives a pin bump. The
sysroot grew 270M → 272M.

**The selection is visible in the report.** A probed element's
`jobserver_decisions` row now carries `sandbox_make` (the sandbox
`make --version`'s first line) and `auth_style`. Enriched where the
decisions file is copied out of the capture, because the probe cache is
keyed on the FIFO's dirname and `close_jobserver` removes it before
report assembly. An unprobed element is written through unchanged: a
null would say "probed, and no make", which is a different fact.

**The third clause needs `UX-913`, and this is the reading that says
so.** Under `--jobserver auto` the resolved auth is `fd` (`UX-876`),
so `style_for_make_version` is consulted on exactly one route -
`_compiler_safe_makeflags`, for the `_COMPILER_SAFE_POLICIES`. That
gives two arms and neither works today:

| arm's kind | policy | on 4.4.1 | on 4.2.1 |
|---|---|---|---|
| `cmake` | `cmake_meson` | probed, `fifo:` kept | probed, **scrubbed** |
| `autotools` | `make` | never probed | never probed |

A `cmake` arm on 4.2.1 emits `scrubbed to recipe -jN`, which
`check_jobserver_width.py` fails on by design; an `autotools` arm is
never probed at all, so it publishes no style to differ. So "one CI
run captures the same element under both staged makes and the two
captures report different styles, each the one its version implies"
needs `UX-913`'s narrowing (PR #248) first - after it, a `cmake` arm on
4.2.1 keeps its raw `fd` instead of being scrubbed, and both arms
publish a style. `Depends on` now says `UX-913` as well.

That last clause is also why no example gained an arm here: adding one
now would red `examples/11-serial-giant`'s existing CI check rather
than exercise anything.

**Mutations.**

| mutation | guard | result |
|---|---|---|
| both series aliases point at the 4.4 binary | `test_each_series_alias_runs_its_own_make` | 🔴 |
| `auth_style` written as a constant `"fifo"` | `test_a_4_2_sandbox_reads_fd`, `test_two_elements_on_two_makes_are_distinguishable` | 🔴 |
| the enrichment dropped, rows copied through | all three style clauses | 🔴 |

Reverted, 15 passed across the two files.

**Deviation from the Required Fix.** The fix asks for "a 4.3 and a 4.4";
this stages 4.2.1, which the channel carries and 4.3 it does not. Both
sit below `UX-841`'s cutoff, which is the only property the switch
reads, so the branch under test is the same one.

**Suite.** With `UX-915`'s commit: see that row's Outcome for the
figure; this branch's full run is in the pull request.
