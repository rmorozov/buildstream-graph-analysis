# UX-457: the reference can only be refreshed from a host the round cannot reach

**Priority:** Low | **Status:** 🟢 Done | **Found by:** round 71, going to add the missing `tests/ci_reference.json` rows for the round's four new files | **Serves:** the contributor who is told to refresh the reference and cannot fetch the thing to refresh from | **Topic:** guards | **Area:** tools

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

**Chosen: the second, with the trade avoided rather than accepted** —
see the Outcome.

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

## Outcome (round 71, 2026-08-31)

### Which of the three, and why the third was not enough

The third option — say in the advice that the download needs a host
some readers cannot reach — tells a reader they are stuck. It does not
get them the numbers, and the numbers are the point.

The second was taken with the reason `UX-441` rejected it removed. That
item did not object to *printing* the document; it objected to printing
370 lines of it in the tail of the job whose failing assertion the
reader was looking for. So the print happens in a job of its own:

```yaml
  tier-reference:
    runs-on: ubuntu-latest
    needs: test
    if: always()
    steps:
      - name: Fetch what test (3.11) recorded
        continue-on-error: true
        uses: actions/download-artifact@v4
        with:
          name: ci-reference-candidate
      - name: The candidate, and nothing else
        run: cat ci_reference.candidate.json || echo "no candidate ..."
```

Nothing there can fail an assertion, so there is no failure for the
document to bury — and `get_job_logs` on that job returns the document
and not a suite. `download-artifact` runs *inside* CI, which reaches
the blob host fine; only the reader outside does not.

It downloads rather than re-records on purpose. A job that ran
`--record` again would print a different run's clock and look
identical.

### What holds it

`tests/unit/test_the_candidate_reaches_a_log.py`, five clauses, each
mutated:

| # | mutation | clause that went red |
|---|---|---|
| M1 | rename the job to `tier-ref` | all five (the job is gone) |
| M2 | download `bst-examples-run-data` instead | `..._fetches_the_artifact_the_tool_names` |
| M3 | `--record` writes `reference.json` | `..._prints_the_file_the_record_step_wrote` |
| M4 | add a `pytest` step to the job | `..._cannot_fail_an_assertion` |
| M5 | drop `if: always()` | `..._runs_on_the_red_runs_too` |

M3 is the one worth naming: the recorded path is read out of the
workflow's own `--record` step rather than compared against a constant
here, so the clause holds the two real sites equal instead of holding
both against a third copy.

`UX-447`'s guard gained the matching clause — every message that says
"re-record" now names the job as well as the artifact, because which
of the two is reachable depends on who is reading. Mutated by deleting
`CI_CANDIDATE_JOB` from one of the four messages:

```console
FAILED tests/unit/test_the_refresh_route_is_written_down.py::test_the_tool_says_where_from_wherever_it_says_re_record
```

### The route, walked

`tier-reference` on run 33413312096 (head `c41a27e`), four steps,
**four seconds** end to end:

```text
Fetch what test (3.11) recorded    16:26:39 -> 16:26:39
The candidate, and nothing else    16:26:39 -> 16:26:40
```

and its log is the document, from `{` to `}`:

```text
{
  "measured_on": "github-actions ubuntu-latest, test (3.11), -n auto",
  "note": "UX-420: one CI run's per-file totals, ...",
  "files": {
    "tests/test_cli.py": 1.94,
    ...
    "tests/unit/test_width_uniformity.py": 0.01
  },
  "spread": { "files": 314, "shift": 1.34, "min": 0.105,
              "p25": 0.796, "p75": 1.269, "max": 7.257 }
}
```

`tests/ci_reference.json` is that document: **376 files -> 385**, a
whole re-record rather than a seventh hand-append, and the four files
round 71 added are in it.

### The measurement that sharpens the item

A direct fetch from this environment is refused *at the same redirect*,
even with the API reachable and a token in hand — so it is the
redirect target, not the API, that is closed:

```console
$ curl -sS -o /dev/null -w "%{http_code}\n" https://api.github.com/rate_limit
200
$ curl -sSL -H "Authorization: Bearer $GITHUB_TOKEN" \
    https://api.github.com/repos/.../actions/jobs/99560544815/logs
curl: (56) CONNECT tunnel failed, response 403
- productionresultssa14.blob.core.windows.net:443 - connect_rejected
```

The route works because the GitHub tooling a round has fetches the log
**server-side** and hands back its text. That is a real route and it is
the one a round actually has; it is not a claim that the blob host
became reachable, and this Outcome says so rather than letting the
green result imply it.

### What the refreshed document then answered

The open question this item started from — why the drift gate had never
named `test_the_served_handoff_counts_its_edges.py`, a 2.8s file with
no reference row — has an answer in the numbers rather than in a theory
about the gate:

```text
tests/unit/test_the_served_handoff_counts_its_edges.py   0.01
tests/unit/test_the_journey_has_an_answer_key.py         0.00
```

It **skips** in `test (3.11)`. The gate was right to say nothing.

### Deviation from the Required Fix

None. The second option was taken, with `UX-441`'s objection removed
rather than accepted; the choice is recorded above the job in
`ci.yml`.
