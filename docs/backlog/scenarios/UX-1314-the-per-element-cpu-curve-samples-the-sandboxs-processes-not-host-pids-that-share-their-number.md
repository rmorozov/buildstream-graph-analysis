# UX-1314: The per-element CPU curve samples the sandbox's processes, not host pids that share their number

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** UX-1134's architect, round 152; promoted from the bookkeeping ledger in round 169 | **Serves:** R1, R5 | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_cpu_curve_reads_the_sandboxes_descendants.py`

## Motivation

`ElementCpuSampler._run` (`tools/bst_native_build_tracer.py:1210-1222`)
reads the host's `/proc/<pid>/stat` with pids taken from the trace log.
Those pids are namespace-local: the hook sets `g_pid = getpid()` inside
`bwrap --unshare-pid` (`tools/hook.c:821`), and the spine writes
`START pid=%d` as sandbox pid 2 (`tools/spine.c:443`, `:48-53`).

Every sandbox therefore starts at pid 2, so concurrent elements
overwrite each other in `_live`, which is keyed by pid. Host `/proc/2`
is `kthreadd` (cpu ~0) and the next low pids are kernel threads, so a
sample is near-zero or absent; a larger pid that does exist reads an
unrelated host process. `cpu_time.per_element_series`
(`tools/bst_native_build_tracer.py:1246`, `bga/schemas.py:5030`) is
never per-element CPU. Nothing in `bga/viewer` reads it today (grep),
so the page is unaffected until something does. Read from the code, not
reproduced against a live bwrap capture.

## Decomposition

Input classes: one element in a sandbox; two concurrent elements (both
pid 2); an element that forks a deep process tree; a host with
kernel threads at the pids the sandboxes report. Journey: a real
`bga capture -- bst build` with `--jobserver auto` under bwrap, read
`cpu_time.per_element_series` against `top` per sandbox.

## Decision

```text
Route:     ElementCpuSampler takes the element's sandbox root as the host pid of the bwrap the shim execs (already in the decision row as `pid`), and each tick sums utime+stime over that pid's host /proc descendants (children via /proc/<pid>/task/*/children, fallback to a ppid scan); trace-log pids are dropped as the key.
Rejected:  translating namespace pids via /proc/<pid>/status NSpid — needs a host pid to start from anyway, and costs a read per process per tick.
Rejected:  cgroup per sandbox — bwrap creates none.
Rejected:  keeping the trace log's START pid=2 keying — every sandbox collides on 2 by construction (spine.c:443).
Files:     tools/bst_native_build_tracer.py (ElementCpuSampler ~1170-1246: key by element, root from decision row, descendant walk); tests/unit/test_the_cpu_curve_reads_the_sandboxes_descendants.py (new)
Guard:     that test replays a scripted /proc root (injectable proc_root) where two sandboxes' trace pids are both 2, host roots 4100/4200 each with descendants carrying distinct utime+stime, /proc/2 a kthreadd stub; asserts two series, each equal to its own descendants' sum.
Mutation:  key `_live` by trace pid again (or sum over proc_root/<trace pid>) → the series collapse / read kthreadd's 0.
Class:     product
Split:     one track, parallel with UX-1310.
Question:  none — bwrap 0.9.0 and --unshare-pid run in this container, so the two-sandbox live reading is reachable here.
```

## Required Fix

Shape with or after UX-1134, which plans the same mechanism: the shim
adds `"pid": os.getpid()` to its decision row (the host pid it execs
bwrap with), and the series becomes the sum of utime+stime over the
host `/proc` descendants of each element's sandbox root, never the
trace log's namespace pids.

## Out of Scope

The viewer drawing the series; the per-process CPU in the trace log.

## Acceptance Test

Two concurrent elements under bwrap each get their own series, and each
series follows that element's descendants' CPU (checked against the
sum of their `/proc` times); a guard replays a scripted `/proc` root in
which two sandboxes both report pid 2. Reading taken in this container.

## Outcome

### The gap, measured

No `bwrap` in this container (`command -v bwrap` empty), so two
`unshare --user --map-root-user --pid --fork --mount-proc` namespaces,
one CPU burner each, stand in. The base sampler (`d0e434e2`) fed the
`START pid=2 element=…` lines each sandbox's spine writes:

```text
a.bst host root 4922 burner ns pid 2
b.bst host root 4923 burner ns pid 2
_live: {2: 'b.bst'}
series: {'b.bst': [[624251000, 0.0], [625251000, 0.0], [626251000, 0.0], [627256000, 0.0]]}
```

One series, not two; `a.bst` is overwritten, and `b.bst` reads host
`/proc/2` (`kthreadd`) at 0.0 cores while its burner ran.

### The close, measured

Same container, rooted at each decision row's host `pid`
(`a.bst` two burners, `b.bst` one; 1 s ticks; `indep` is a second
ppid walk over real `/proc`, read just before each tick; this kernel
has no `task/*/children`, so the ppid-scan fallback is the path read):

```text
a.bst host root 21343 namespace pids: 1 2 3 5 6 7
b.bst host root 21345 namespace pids: 1 2 4 5 6
host /proc/2: (kthreadd) cpu_us 30000
element          t_us  series   indep    diff
a.bst      3960044000   0.776   0.776   0.000
a.bst      3961078000   0.725   0.706   0.019
a.bst      3962125000   0.774   0.793  -0.019
a.bst      3963180000   0.682   0.673   0.009
a.bst      3964216000   0.763   0.772  -0.009
b.bst      3960044000   0.335   0.345  -0.010
b.bst      3961078000   0.455   0.455   0.000
b.bst      3962125000   0.334   0.334  -0.000
b.bst      3963180000    0.18   0.180  -0.000
b.bst      3964216000   0.347   0.347  -0.000
```

Both namespaces hold a pid 2; each gets its own series, within one
jiffy per burner (0.01 core at 1 s; `a.bst` has two) of its
descendants' `/proc` sum. The walk and the decision-row follow are
`tools/jobserver/memory.py`'s, beside `MemoryGate`'s `_descendants`.

### Mutations verified red and reverted (5)

`python3 <scratchpad>/mutate.py`, reverted from a copy, then 4 passed:

| # | mutation | reddened |
|---|---|---|
| M1 | `follow_sandbox_roots` keys by trace pid 2 (`roots[2] = …`) | all 4 tests |
| M2 | `sandbox_tree` returns `[root]` (no descent) | 3 (all but root-exit) |
| M3 | ppid fallback empty (`in {}.items():`) | `[ppid-scan]`, 1 |
| M4 | rows keyed by root, not by host pid | 3 (all but root-exit) |
| M5 | an exited root is not pruned (`pass` for the pop) | root-exit test, 1 |
