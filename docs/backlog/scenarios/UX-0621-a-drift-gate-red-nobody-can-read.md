# UX-621: a drift-gate red nobody can read

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-418 (the gate), UX-476 (the log-tail route), UX-491 (the gate's line) | **Found by:** round 85, while root-causing UX-619 | **Serves:** a session reading a red tier-drift step | **Topic:** guards

## Motivation

`6febb53` was red on 3.11 only, at step 14 — `Tiers match CI's own
record of them` — and the failure cannot be read from this
environment:

```text
annotation:  Process completed with exit code 1
GET /actions/jobs/{id}/logs  →  productionresultssa1.blob.core.windows.net
                                connect_rejected (403 on CONNECT)
```

`ci.yml` already documents that denial for the artifact route and
prints the reference document into the log for a reader without it
(`UX-476`), and `UX-491` repeats the gate's own verdict line last.
Neither reaches a reader whose egress policy blocks the blob host that
serves the *log* — which is this container, and any agent session
configured like it.

So a step built to be legible over the API is legible only to a reader
who can also fetch the log body, and the one-line summary `UX-491`
added is inside that body.

## Required Fix

The drift gate's verdict survives where the log body does not — as a
check-run annotation, a job summary, or a step output the API returns
in the run's own JSON. Which of those, argued from what an API client
can actually read without the blob host.

## Out of Scope

- `UX-619`, which this was found under and which is closed.
- The gate's arithmetic (`UX-418`) — right, and not touched.

## Acceptance Test

A red drift gate whose reason is readable from the Actions API alone,
with the blob host unreachable.
