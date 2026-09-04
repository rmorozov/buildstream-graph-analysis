# UX-621: a drift-gate red nobody can read

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-418 (the gate), UX-476 (the log-tail route), UX-491 (the gate's line) | **Found by:** round 85, while root-causing UX-619 | **Serves:** a session reading a red tier-drift step | **Topic:** guards

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

**Corrected 2026-09-04 (round 85), one of the three options does not
exist.** A step's entry in `GET /actions/jobs/{id}` carries
`completed_at conclusion name number started_at status` and nothing
else — there is no field a step output could be returned in. Measured
below. The choice was between the remaining two, and it is the
annotation. The filing's text, kept:

> The drift gate's verdict survives where the log body does not — as a
> check-run annotation, a job summary, or a step output the API returns
> in the run's own JSON. Which of those, argued from what an API client
> can actually read without the blob host.

## Out of Scope

- `UX-619`, which this was found under and which is closed.
- The gate's arithmetic (`UX-418`) — right, and not touched.

## Acceptance Test

A red drift gate whose reason is readable from the Actions API alone,
with the blob host unreachable.

## Outcome

**The gap, measured.** Run 33808929465 (`6febb53`), `test (3.11)` red at
step 14, read from this container with `curl` and no auth:

```text
GET /repos/.../check-runs/100825940544/annotations   200
    failure: "Process completed with exit code 1."   (path .github:34)
GET /repos/.../actions/jobs/100825940544/logs        302 ->
    productionresultssa18.blob.core.windows.net/...
    curl: (56) CONNECT tunnel failed, response 403
GET /repos/.../actions/jobs/100825940544             200
    step 14 "Tiers match CI's own record of them" keys:
    completed_at conclusion name number started_at status
GET /repos/.../check-runs/100825940544               200
    output.summary: null   output.annotations_count: 2
```

So the premise holds and is if anything wider than filed: the log body
is a blob host this egress refuses (`sa18` on this run, `sa19` in
`UX-457` — the digits vary, the denial does not), the run JSON has no
per-step field to carry a verdict, and the annotations are JSON on
`api.github.com`. `ci.yml` used `::error::` and `$GITHUB_STEP_SUMMARY`
nowhere; it already used `::warning::` twice (the two adopt jobs), so
the workflow-command route was in the file and this reuses it rather
than inventing a second. The job summary was rejected because no REST
endpoint returns one — `output.summary` above is the check run's, which
Actions leaves null — while the annotation was measured readable.

**The close, measured.** `--annotate` on a red `--against`, one file
confirmed over two runs:

```text
$ python3 tools/dev_tier_drift.py junit.xml --against ref.json \
    --carry carry.json --summary gate.txt --annotate   # second run
exit 1
::error file=tests/ci_reference.json,title=tier drift::164 file(s)
measured against ref.json (unknown), this run x1.00 from 164 file(s)
over 1s, IQR 0.00, and 1 file(s) slower than ref.json records:
tests/unit/test_the_page_has_geometry.py 123.4s against 61.7s
recorded, x2.00
```

(one line in the run; wrapped here). It is `UX-491`'s own sentence, not
a second one computed at the sink (§5). `file=` is not decoration: the
measurement above shows an unattributed annotation lands on `.github`
at the workflow's line, beside the "exit code 1" this replaces.

**Mutations.** `PYTHONDONTWRITEBYTECODE=1 PYTEST_XDIST= pytest
tests/unit/test_a_slow_file_says_which_file.py -k
TestTheVerdictSurvivesWithoutTheLogBody` — 6 passed, 0.37s green.

| # | mutation | reddened | run |
|---|---|---|---|
| 1 | `ci.yml` gate step drops `--annotate` | `..._workflow_asks_the_gate_for_one` | 1 failed, 5 passed |
| 2 | `if args.annotate and code:` → `if args.annotate:` | `..._green_gate_annotates_nothing` | 1 failed, 5 passed |
| 3 | `annotation()` drops `file={path}` | `..._names_the_document_to_act_on` | 1 failed, 5 passed |
| 4 | `annotation()` drops the `%25/%0D/%0A` escaping | `..._annotation_is_one_line` | 1 failed, 5 passed |
| 5 | `if args.annotate and code:` → `if code:` | `..._the_route_is_opt_in` | 1 failed, 5 passed |
| 6 | annotate a fixed string, not the gate's summary | `..._red_gate_says_why_where_the_api_can_read_it` | 1 failed, 5 passed |
| 7 | the guard's own step filter selects nothing | `..._workflow_asks_the_gate_for_one`, on `assert steps` | 1 failed, 5 passed |
| 8 | the "red" fixture scaled x1.0 instead of x2.0 | 3 clauses, on `code == 1` | 3 failed, 3 passed |

7 and 8 are the vacuity pair: an over-broad exclusion removes a
clause's input, and both clauses **failed** on their non-vacuity
assertion rather than passing over an empty set.

**A guard that did not discriminate.** None. Every clause has a
mutation above; 4 was written after noticing the message could contain
a `%` from a future verdict, and 8 showed the red fixture is load-
bearing for three of the six.

**Deviation from the Required Fix.** None on the fix. On the Acceptance
Test: "a red drift gate ... with the blob host unreachable" needs a red
CI run, which this track cannot make without pushing a deliberate red.
It is replayed in two halves instead — the API half against the real
red run 33808929465 above, the emit half locally.
