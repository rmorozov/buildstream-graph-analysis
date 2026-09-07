# UX-755: the gate and CI disagree, and the gate is the one that is wrong

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-336 (the loop), UX-418 (a slow file CI sees differently) | **Serves:** the session that runs `make test` and believes it | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

**Corrected**, against the diagnosis track's own measurement: this row
was filed on an isolated-passes / suite-fails split
(`25 passed in 47.30s` alone against `18 errors` inside `make test`)
that does not hold. Run alone again, same container, same file:
`7 passed, 18 errors in 12.44s` — no suite involved at all. The split
was never a property of xdist, ordering, or `LD_PRELOAD`; it was a
snapshot of a *moving* quantity, read once on each side.

The real mechanism: BuildStream's `cache.reserved-disk-space` default
(`5%`) is computed against `shutil.disk_usage(volume).total` — the
nominal filesystem size — not `.free`. On a container whose real free
space is small next to its nominal size, that reserve alone can exceed
what is actually free, and `bst` then refuses every build
("Cache too full") before a single subprocess runs — hence
`Processes traced: 0`. The margin (`free - reserved`) moves by
gigabytes as other activity fills or clears `/tmp`: clearing 1.5 GB of
stale `pytest-of-root` scratch moved it from `+1.776 GB` to
`+3.361 GB` in one step. A short isolated run and a long suite run
sample this margin at different, uncoordinated moments — that is the
whole "split".

A second, independent sighting: `track/ux-751` (a two-file docs/guard
diff touching nothing in the capture path) hit 12 failures across
7 files under a full `make test` (593s) — every one a real-`bst`
end-to-end test, every one passing clean run alone immediately after.
Same class, same cause, seven files wide, not the contention its own
verifier first read it as.

## Required Fix

1. Find what the full suite does to the capture that neither CI nor
   an isolated run does — a shared `TMPDIR`, a `casd` left running,
   an `LD_PRELOAD` the suite unsets, an ordering dependency. Name it.
2. Either make the file work under the suite, or make it **skip with
   a stated reason** on a host where its precondition does not hold —
   `test_every_skip_reason_is_declared` already governs that shape.
   Eighteen errors a session must learn to ignore is the worst of the
   three outcomes.
3. **The inverse check:** whatever the diagnosis, it must predict the
   isolated run passing *and* the in-suite run failing. A cause that
   explains only one of those is not the cause.

## Out of Scope

- `UX-741`, the wall-clock spine guard that reds on a loaded host.
  It is separately filed, it is a different mechanism, and it was the
  only other local-only failure this round.
- Making CI stricter. CI is the side that is right here; the defect
  is that the local gate reports failures a session cannot act on,
  which teaches the session to discount it.

## Acceptance Test

**Restated** — not isolated-passes/suite-fails; that split does not
hold and is not the bar. Instead: with `free - reserved-disk-space`
(BuildStream's own arithmetic) deliberately driven to `<= 0`, the file
fails without the fix and passes with it; at the container's normal,
higher margin, it continues to pass.

## Outcome

**The gap measured.** Isolated, unmodified: `7 passed, 18 errors in
12.44s` (repeated: `44.40s`) - the split the row was filed on does not
reproduce. A bare `bst build all.bst`, no bga/pytest/LD_PRELOAD, fails
identically: `Cache too full`. Root cause:
`buildstream/_context.py`'s `cache.reserved-disk-space` (default `5%`)
reads `shutil.disk_usage(volume).total` (270.55 GB), not `.free`
(13.3-16.9 GB across measurements minutes apart) - `5%` of total is
13.53 GB, so `free - reserved` straddles zero and moves by gigabytes as
`/tmp` fills or clears (clearing 1.5 GB of stale `pytest-of-root`
moved it `+1.776 GB -> +3.361 GB`). Upstream, not this repo's code.
Second sighting: `track/ux-751`'s `make test` (593s, unrelated diff)
hit 12 failures across 7 real-`bst` files, all clean alone immediately
after - same class, wider blast radius than one file.

Ruled out, each checked directly: an env var the suite sets (`tests/
conftest.py` in full - no autouse fixture, no worker branch); a shared
global `cachedir` (no `~/.config/buildstream*.conf` existed); a stale
`casd` reused across workers (none running; `detect_stale_casd`'s own
warning never fired); a module-level cache/global leaking across a
shared xdist worker (grepped `bst_native_build_tracer.py` and
`bga/run_store.py` - none). A margin-narrows-over-one-run test (before/
after a 612-test `large`-tier run) did not show shrinkage here
(`+1.73 GB -> +2.16 GB`) - this run's own footprint was 11 MB; the
container's other concurrent tracks dominate that signal, so this
specific angle is inconclusive, not confirming.

**The close measured — fixed, not skipped.** `tools/bst_show_to_graph.
run_show` already threads `bst_options` through for a replayed build;
BuildStream itself reads `$XDG_CONFIG_HOME/buildstream(2).conf`
(`_context.py`), so one env var on the `walked` fixture's `env` reaches
both the wrapped build and `extract_run`'s internal `bst show` with no
per-call-site plumbing. Added `tests/fixtures/macro_micro/
xdg_config_home/{buildstream,buildstream2}.conf` (`cache: {quota: 3G,
reserved-disk-space: 500M}` - absolute values, no percent-of-total),
repo-owned, referenced only via this test's own `env` dict - never
`~/.config/`, so no other track's `bst` is touched.

**Inverse check, at a deliberately-lowered margin** (`fallocate`'d a
file to `free - reserved = -0.92 GB`, BuildStream's own arithmetic):

| env dict | result |
|---|---|
| without the `XDG_CONFIG_HOME` override | `7 passed, 18 errors in 7.06s` |
| with it (this commit) | `25 passed in 61.65s` |

Same margin, opposite result - the fix discriminates. At the container's
normal margin afterward: `25 passed in 42.07s`.

Filed, not fixed here: the upstream `total`-vs-`.free` read; 6 other
files sharing this exposure (`test_a_generated_project_builds.py` and
6 more, from `track/ux-751`'s 12 failures) - same fix would apply,
out of this row's declared scope.
