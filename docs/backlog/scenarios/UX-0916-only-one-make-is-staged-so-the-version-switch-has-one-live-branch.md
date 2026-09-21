# UX-916: only one make is ever staged, so `style_for_make_version`'s two branches are never both exercised

**Priority:** Medium | **Status:** 🟡 In Progress | **Depends on:** UX-915 | **Found by:** round 133 — Ruslan asked for the corner cases to be covered after the fast unblock lands (2026-09-21) | **Serves:** every host that runs the examples, whatever its own make | **Topic:** guards | **Area:** tools | **Shape:** judgement

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

**Round 134, 2026-09-21 — all three clauses are in.** Status 🟡 until a
CI run reads the two arms.

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

**The selection is visible in the report.** A probed element's
`jobserver_decisions` row now carries `sandbox_make` (the sandbox
`make --version`'s first line) and `auth_style`. Enriched where the
decisions file is copied out of the capture, because the probe cache is
keyed on the FIFO's dirname and `close_jobserver` removes it before
report assembly. An unprobed element is written through unchanged: a
null would say "probed, and no make", which is a different fact. Read
back off a real capture, `bst-examples` on `33884772`:

```text
core.bst decision: {'auth_style': 'fifo', 'kind': 'cmake',
 'policy': 'cmake_meson', 'sandbox_make': 'GNU Make 4.4.1\n...'}
```

That `\n...` is `probe_make` caching `make --version`'s whole stdout;
only the first line lands in a row now.

**The two arms are `cmake`, which `UX-913` is what makes possible.**
Under `--jobserver auto` the resolved auth is `fd` (`UX-876`), so
`style_for_make_version` is consulted on one route,
`_compiler_safe_makeflags`. `UX-913` (PR #248, merged) narrowed it:

```text
$ grep -n "_FD_DIRECT_POLICIES" tools/native_trace/bwrap_shim.py
454:_FD_DIRECT_POLICIES = frozenset({"cmake_meson"})
713:    if safe is None and policy in _FD_DIRECT_POLICIES:
```

so a `cmake` arm on 4.2.1 keeps its raw `fd` rather than being
scrubbed, and `lto_preflight_warnings` prints `keeps its jobserver
auth` where it printed the `scrubbed to recipe -jN` that
`check_jobserver_width.py` fails on. An earlier draft of this Outcome
read the pre-#248 tree, called the third clause blocked and added a
`Depends on: UX-913`; both are withdrawn.

`switch-4-4.bst` and `switch-4-2.bst` are that pair: identical `cmake`
elements on `toolchain.bst` alone, differing only in the alias their
`PATH` leads with, so neither sits on `UX-857`'s critical path.
`check_jobserver_width.py`'s fourth assertion reads both rows out of
the one `auto` capture it already takes, so no workflow edit is needed.

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
