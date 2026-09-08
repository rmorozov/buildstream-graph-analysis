# UX-796: the host sampler claims more busy cores than the host has, under load

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-675 (the sampler and its ceiling), UX-741 (the same shape in the spine's guard) | **Found by:** round 110, in a `make test` gate on a loaded machine | **Serves:** the gate that reds on a host reading nothing in the diff touched | **Topic:** guards | **Area:** bga | **Shape:** mechanical

## Motivation

```console
$ make test        # load average 7.02, 10.88, 12.25 on 4 cores; seven agents running
FAILED tests/unit/test_the_host_was_asked.py::TestTheCoresAreSampledToo::test_no_sample_claims_more_cores_busy_than_the_host_has
E   assert 5.686 <= 4.784313725498253      # (row, gap) ... gap 0.05099999999947613
$ for i in 1 2 3; do pytest tests/unit/test_the_host_was_asked.py -k test_no_sample_claims_more_cores_busy -q; done   # load 7.02
1 passed / 1 passed / 1 passed
```

`UX-675`'s ceiling allows one jiffy per core over the host's count
(4.78 on 4 cores); the sample read 5.69 busy cores. The busy jiffies
summed across CPUs cannot exceed cores × elapsed unless the elapsed
wall time is read short — the sampler reads `/proc/stat` and the
clock at different instants, and under load the process is
descheduled between them. The guard is right; the sampler's window
is the defect.

## Required Fix

`tools/bst_native_build_tracer.py`'s `HostSampler` measures its window
with the same source it reads busy time from — the sum of all-CPU
jiffies (busy + idle) at each read, not a wall clock beside it — so
busy/total cannot exceed one per core by construction. The ceiling's
one-jiffy allowance stays. (Corrected from `bga/hostinfo.py`, which
is the manifest module; the sampler and its `/proc/stat` read live here.)

## Out of Scope

- Skipping the guard under load — `UX-741`'s row closed that route on
  measurement: no threshold exists.

## Acceptance Test

`tests/unit/test_the_host_was_asked.py` gains a clause that feeds the
sampler two `/proc/stat` snapshots whose wall-clock gap is shorter
than their jiffy gap (a descheduled read) and asserts busy cores ≤
the host's; mutation: restore the wall-clock window — red.

## Outcome

**Gap measured:** `test_no_sample_claims_more_cores_busy_than_the_host_has`
under `for i in $(seq 12); do yes >/dev/null & done` (4 cores), three
runs before the fix — not reproduced in this pass (see below); the
row was filed on the Motivation's pasted `5.686 <= 4.784` read.

**Close measured:**

```console
$ nproc
4
$ for i in $(seq 12); do yes >/dev/null & done; sleep 1
$ for i in 1 2 3; do pytest tests/unit/test_the_host_was_asked.py \
    -k test_no_sample_claims_more_cores_busy_than_the_host_has -q; done
1 passed / 1 passed / 1 passed
$ pkill yes
```

`_to_cores` now divides `busy_delta * cores` by `cpu_total_jiffies`
delta (the same `/proc/stat` read's busy+idle sum) instead of
`_TICKS_PER_S * wall_elapsed`; `busy ⊆ total` by construction, so
`cpu_busy_cores ≤ cores` always. `t` (wall clock) still gates presence
and still rides in the written sample for the timeline join
(`bga/utilisation/envelope.py:wall_samples`) — unchanged.

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| `_to_cores` division reverted to `(busy - was_busy) / (_TICKS_PER_S * elapsed)` | new clause `test_a_descheduled_read_does_not_claim_more_cores_than_exist` | `600.0 <= 4` assertion failed, 1 failed / 19 deselected |

Restored from a copy taken before the mutation
(`tools/bst_native_build_tracer.py.orig` in the scratchpad), never
`git checkout --`; full file re-run green after restore (20 passed).

**Deviation.** The Required Fix named `bga/hostinfo.py`; the sampler is `tools/bst_native_build_tracer.py`'s, corrected in the file. The verifier's finding, recorded: the presence gate still reads wall time while the ratio divides by the jiffy window, so under a long deschedule the figure is a jiffy-window average stamped on a shorter wall bucket in `envelope.py`'s join — the ceiling holds by construction, the label does not say so; `UX-110`-adjacent, left for the row that reads the timeline. The row's own red did not reproduce under 12 hogs on 4 cores (5 of 5 green); the synthetic pair reproduces the filed 5.686 reading. One commit, one verifier (PASS).
