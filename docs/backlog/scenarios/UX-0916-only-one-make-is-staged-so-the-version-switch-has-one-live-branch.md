# UX-916: only one make is ever staged, so `style_for_make_version`'s two branches are never both exercised

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-915 | **Found by:** round 133 — Ruslan asked for the corner cases to be covered after the fast unblock lands (2026-09-21) | **Serves:** every host that runs the examples, whatever its own make | **Topic:** guards | **Area:** tools | **Shape:** judgement

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


**Settled 2026-09-21: both makes come from one source.** The Nix
channel `UX-915` now stages from carries `gnumake-4.2.1` beside
`gnumake-4.4.1`, each its own pinned store path (the measurement is in
`UX-915`'s Required Fix). So this row is a second closure fetch rather
than a second build, and the two branches of
`style_for_make_version` get a live example each without either one
depending on what the staging host happens to ship.

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

**Round 134, 2026-09-21 — closed on one capture that crossed the
switch both ways.** `bst-examples` on `a4541d98`, step 21:

```text
switch-4-2.bst: 'GNU Make 4.2.1\n...' -> 'fd' (UX-916)
switch-4-4.bst: 'GNU Make 4.4.1\n...' -> 'fifo' (UX-916)
Note: switch-4-2.bst keeps its jobserver auth (sandbox make <4.4,
  cmake_meson); make reads the fd directly (UX-913)
giant.bst: off peak 2, auto peak 4, resolved width 2
off=187.32s auto=180.72s
```

One run, two arms, opposite branches, and `grep scrubbed` over that
job's whole log returns nothing - the Acceptance Test's three clauses.

**Both makes are staged.** The same channel carries 4.2.1 beside
4.4.1, both `x86_64`, one glibc, so the second pin costs one 247 KB nar:

```text
$ examples/stage_cpp_toolchain.sh | head -3
Pinned GNU Make 4.4.1 from /nix/store/fnvsac4yaw2146ig4p54xnnm6b6alkjw-gnumake-4.4.1
  staged GNU Make 4.2.1 as /usr/lib/bga-make/4.2/make
  staged GNU Make 4.4.1 as /usr/lib/bga-make/4.4/make
```

The selection is that alias, not a store path: an element puts
`/usr/lib/bga-make/4.2` ahead of `/usr/bin` on its own `PATH`, so a
`.bst` file names a series and survives a pin bump. Sysroot 270M → 272M.
`switch-4-4.bst` and `switch-4-2.bst` are otherwise identical `cmake`
elements on `toolchain.bst` alone, off `UX-857`'s critical path, and
`check_jobserver_width.py`'s fourth assertion reads them out of the
`auto` capture it already takes - no workflow edit.

**The selection is visible in the report.** A probed element's
`jobserver_decisions` row carries `sandbox_make` and `auth_style`,
written where the decisions file is copied out of the capture, because
the probe cache is keyed on the FIFO's dirname and `close_jobserver`
removes it before report assembly. An unprobed element is written
through unchanged: a null would say "probed, and no make", which is a
different fact. The `\n...` above is `probe_make` caching
`make --version`'s whole stdout; only the first line lands in a row now.

**Why a `cmake` pair works at all.** Under `--jobserver auto` the
resolved auth is `fd` (`UX-876`), so `style_for_make_version` is
consulted on one route, `_compiler_safe_makeflags`, which `UX-913`
(#248) narrowed:

```text
454:_FD_DIRECT_POLICIES = frozenset({"cmake_meson"})
713:    if safe is None and policy in _FD_DIRECT_POLICIES:
```

A `cmake` arm on 4.2.1 therefore keeps its raw `fd` instead of being
scrubbed - the `Note:` line above, where the pre-#248 tree printed the
`scrubbed to recipe -jN` that `check_jobserver_width.py` fails on. An
earlier draft of this Outcome read that older tree, called the clause
blocked and added a `Depends on: UX-913`; both are withdrawn.

**Mutations.**

| mutation | guard | result |
|---|---|---|
| both aliases on the 4.4 binary | `test_each_series_alias_runs_its_own_make` | 🔴 |
| `auth_style` a constant | `test_a_4_2_sandbox_reads_fd` | 🔴 |
| the enrichment dropped | all three style clauses | 🔴 |
| both arms' `PATH` on one alias | `..._selects_the_series_its_own_expectation_names` | 🔴 |
| an arm dropped from `all.bst` | `test_both_arms_are_built` | 🔴 |
| `check_switch` returns unread | all five refusal rows | 🔴 |
| a partial miss tolerated | `test_a_missing_arm_is_refused` (KeyError) | 🔴 |
| the 4.2 pin dropped | `test_the_arms_and_the_pins_name_the_same_series` | 🔴 |

Reverted, 26 passed across the three files.

**Deviation from the Required Fix.** It asks for "a 4.3 and a 4.4";
this stages 4.2.1, which the channel carries and 4.3 it does not. Both
sit below `UX-841`'s cutoff, the only property the switch reads.

**Suite.** This branch's full run is in the pull request.
