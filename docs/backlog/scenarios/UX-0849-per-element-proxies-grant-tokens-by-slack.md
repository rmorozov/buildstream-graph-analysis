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
