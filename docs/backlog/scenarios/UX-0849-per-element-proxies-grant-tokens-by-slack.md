# UX-849: per-element proxies grant tokens by slack

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-845, UX-847 | **Found by:** round 117, Direction 20 | **Serves:** R4 (the critical path gets the cores first) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

One FIFO is first-come: the element with three hours of slack and
the element on the critical path read the same pipe. bga computes
`slack` and `criticality_probability` per element and, with
`UX-847`, each element's achieved parallelism and peak RSS - a plan the
next capture can run. A per-element cap (`UX-842`'s `-jK`) needs a
per-element pool too.

## Required Fix

`tools/bst_native_build_tracer.py`: `--jobserver auto --plan
<analyze.json>` opens one proxy FIFO per sandbox behind a broker; the
broker moves tokens from the global pool into the proxy of the running
element with the least slack in the plan first, caps a proxy at the
element's `-jK`, and treats an element absent from the plan as
median-slack. The shim binds each sandbox its own proxy. Without a
plan every proxy is equal - stage 2's behaviour byte for byte.

## Decomposition

Input classes: no plan, a plan naming every element, a plan missing
half (a changed graph), two elements tied on slack; the journey it
extends is R4's second capture after the first's analysis.

## Out of Scope

Preempting a running element's tokens - declined: a token taken is
a job started.

## Acceptance Test

`tests/unit/test_the_broker_grants_by_slack.py` drives the broker
with two proxies and a plan and asserts the order of grants; mutation:
grant round-robin - red. On examples/07 with the plan from `UX-848`'s
first capture, the wall against stage 2 is pasted.

## Outcome

**Gap measured.** Before this item `--jobserver auto` had no `--plan`
flag at all - one global FIFO, first-come, no notion of slack. `bga
capture run --plan --help` did not exist; `tools/bst_native_build_
tracer.py run --help` was 59 lines (`tests/unit/test_help_is_short.py`'s
`CAP`).

**Close measured.**
`python3 -m pytest tests/unit/test_the_broker_grants_by_slack.py -v`:

```text
TestPopulation::test_zero_running_elements_returns_every_token_to_the_global_fifo PASSED
TestPopulation::test_one_running_element_is_capped_at_its_own_jk_minus_one PASSED
TestPopulation::test_two_running_elements_grant_least_slack_first PASSED
TestThePlan::test_an_element_absent_from_the_plan_gets_the_median_slack PASSED
TestThePlan::test_a_tie_on_slack_is_broken_by_name_order PASSED
TestDrain::test_an_element_ending_drains_its_proxy_back_to_the_global_fifo PASSED
test_without_a_plan_the_shims_argv_is_byte_for_byte_unchanged PASSED
7 passed in 2.59s
```

`tests/unit/test_the_pool_follows_the_machine.py`,
`test_bwrap_shim.py` (37), `test_help_is_short.py` (`CAP` 59 -> 63),
`test_the_environment_surface_is_an_inventory.py` (`BST_TRACE_PROXY_DIR`
row) all green; `dev_baseline.py --check`/`dev_sizes.py --check` clean
(`--adopt --force`/`--write --force --reason UX-849` where either
listed growth - mostly pre-existing drift on this base, not this diff).

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| grant round-robin instead of by-slack fill | population/plan/tie tests | 3/7 red |
| drop the per-element `-jK` cap | one-element cap, drain tests | 2/7 red |
| a proxy always injects `fifo:`, ignoring `BST_TRACE_JOBSERVER_AUTH` | the fd-style proxy test | 1/3 red |

**Two real defects, found and fixed live.** (1) UX-846's wrapper mount
used a new top-level `/.bga/wrappers` - a real sandbox root refuses one
(`Can't mkdir parents ...: Read-only file system`); rehomed under the
trace bind (`WRAPPER_BIND_SUBDIR`), the coordinator's fix, applied here
along with the same move for this item's own proxy bind. (2) A proxy
always used `fifo:` - GNU Make 4.3 (this box, CI) rejects that string
outright (`internal error: invalid --jobserver-auth string`, reproduced
directly). Fixed: a proxy now follows `BST_TRACE_JOBSERVER_AUTH`, the
*same* style the global FIFO already resolved to (`_resolve_proxy_auth`
mirrors `open_jobserver_fd` exactly) - `fd` opens the proxy itself,
inheritable, no bind; `fifo` binds the host path unchanged, as the
global one already does.

**Live reading, both walls**, examples/10-jobserver, fresh cache each,
this box's `make --version` (GNU Make 4.3, so `jobserver_auth: fd`):

```sh
bga capture run --run-dir run-C --jobserver auto examples/10-jobserver plane2-C.json -- bst build all.bst
bga analyze run-C --plane2 plane2-C.json -f json -o plan-C.json
bga capture run --run-dir run-D --jobserver auto --plan plan-C.json examples/10-jobserver plane2-D.json -- bst build all.bst
```

No `--plan`: **32.23s**. `--plan plan-C.json`: **41.41s** - slower, the
broker (`grants: 3, drains: 3`) redistributing an already 16-way-
oversubscribed 4-core box, a second real cost (100ms) on top of
`PoolController`'s own (250ms) with nothing idle either can hand out.
Dated stage-3 line added under the README's stage-1 paragraph.
