# UX-457: the reference can only be refreshed from a host the round cannot reach

**Priority:** Low | **Status:** 🔴 Not Started | **Found by:** round 71, going to add the missing `tests/ci_reference.json` rows for the round's four new files | **Serves:** the contributor who is told to refresh the reference and cannot fetch the thing to refresh from | **Topic:** guards

## Motivation

`UX-427` built the refresh route on purpose: CI writes the refreshed
document to `ci_reference.candidate.json` and uploads it as the
`ci-reference-candidate` artifact, so a refresh is *a copy rather than
a guess* — its own words, in `.github/workflows/ci.yml`. `UX-447` then
put that artifact's name in all four places that advise the refresh.

The advice is correct and the artifact exists. It is the fetch that
fails. Both hosts GitHub serves run output from are denied by the
egress policy of the environment these rounds are actually worked in:

```console
$ curl -sSL -o r.zip "https://results-receiver.actions.githubusercontent.com/rest/runs/.../logs?..."
curl: (56) CONNECT tunnel failed, response 403
- results-receiver.actions.githubusercontent.com:443 — connect_rejected

$ curl -sSL -o cand.zip "https://productionresultssa19.blob.core.windows.net/actions-results/.../ci-reference-candidate.zip?..."
curl: (56) CONNECT tunnel failed, response 403
- productionresultssa19.blob.core.windows.net:443 — connect_rejected
```

(artifact 9763741205, run 33407037683, `test (3.11)` on head `9acb5fb`;
the artifact is listed, unexpired, 5,785 bytes — it is reachable to
list and not to read.)

So round 71 added four test files and left `tests/ci_reference.json`
at the 376 rows it had. The one measurable consequence found so far is
small — the drift step has been green on every run since `ea122e5`
added the first of them, so nothing is being gated — but the reference
is now four files stale by construction, and the *reason* it is stale
is not laziness: the documented route does not run from here.

The alternative that must **not** be taken is writing the rows from a
developer machine's seconds. `UX-418` established that CI's seconds
and a local report are not the same measurement, and a reference half
recorded on each is the "comparison across machines" defect of fixing
guide §5 with a JSON file around it.

## Required Fix

Pick one, and record which:

- Have the workflow itself commit or comment the candidate — the
  numbers then arrive somewhere a round can read without an egress
  exception.
- Or print the candidate document to the job log again, behind a flag,
  accepting what `UX-441` traded away (a red run's failure scrolling
  out of reach) only when the refresh is what is being asked for.
- Or state in the advice that the refresh needs a machine that can
  reach GitHub's artifact host, so a reader who cannot stops looking
  instead of concluding the artifact is missing.

## Out of Scope

- **The egress policy.** It is the environment's, not this
  repository's, and `UX-445` already records the same class of block
  for `ui.perfetto.dev`.
- **The four missing rows themselves**: they arrive with whichever
  route this item picks, and adding them by hand from local seconds is
  the `UX-418` mistake this item exists to refuse.

## Acceptance Test

```bash
python tools/dev_tier_drift.py <the refreshed document> --against ...
```

run from a round's own environment, against a reference whose newest
rows came from a CI run and not from a laptop — with the command that
fetched them pasted here.

## Outcome

_Not started._
