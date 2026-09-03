# UX-557: the drift gate's cause filter admits all 424 files, and `--why` cannot say so

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-476 (which built the filter), UX-442 (the carry), UX-524 (the map) | **Serves:** the round whose PR the gate reddens | **Topic:** guards

## Motivation

`UX-476` added `--base` to the tier-drift gate so a reported file needs
"something in the diff that could account for it", over
`tools/dev_touching.select`. Round 81's PR went red on it:

```text
424 file(s) measured against ci_reference.json (github-actions ubuntu-latest,
test (3.11), -n auto), this run x1.00 from 148 file(s) over 1s, IQR 0.47, and
1 file(s) slower than ci_reference.json records:
tests/unit/test_the_query_asks_about_this_run.py 36.9s against 19.7s recorded, x1.88
```

The file is **unchanged by the round**. Measured here, interleaved,
`PYTEST_XDIST=` single process, branch against its merge-base
`ca825c3`:

```text
rep1 base   12.42s (cold Chrome, 4 errors)   rep1 branch  19.83s
rep2 base   21.16s                           rep2 branch  20.48s
rep3 base   21.66s                           rep3 branch  20.92s
```

13 tests both sides. `main` records it at 19.63-20.25s over five
samples, with the same file content — the +145 lines it carries came
from `2f27f12` (`UX-527`), which is on `main`.

So the filter passed a file with no cause. It passes **every** file:

```text
$ python3 tools/dev_touching.py --base origin/main --why | grep -c '^tests/'
424
$ python3 tools/dev_touching.py --base origin/main --why | grep -c '<- None'
424
```

Both numbers are the whole suite. `select()` short-circuits:

```python
everything = [c for c in changed
              if any(c == e or c.startswith(e) for e in EVERYTHING)]
if everything:
    return sorted(test_files()), {"*": f"shared harness changed: {everything}"}
```

`EVERYTHING` is `tests/conftest.py`, `tests/tiers.py`, `pyproject.toml`,
`Makefile`, `tests/support/`, `tests/dom_shim.mjs`. Round 81 touched
`pyproject.toml` and `tests/tiers.py` — and **adding one row to
`tests/tiers.py` is what a round does when it adds one test file**, so
this is the common case, not the corner.

Two consequences, and the second is the one that reddened a PR:

1. The reason is keyed `"*"` and `--why` reads `why.get(name)`, so all
   424 print `None`. "Which selected each file" — the question
   `make test-touching ARGS=--why` exists to answer — goes unanswered
   exactly when the answer is most surprising.
2. The gate's second condition is vacuously true, so the report rests
   on `UX-442`'s consecutive agreement alone. That is the state
   `UX-476` was written to leave behind, and its outcome says so.

## Required Fix

The `"*"` reason must reach the reader: `--why` should print the
short-circuit's own sentence for each file, or `select` should return
the reason per name. That is the smaller half.

The gate half is the decision: a diff that touches a shared-harness
path gives every file a cause, so `--base` cannot discriminate on
those diffs. Either the gate says so in its line — "no cause filter
applied: shared harness changed" — and the round reads the report
knowing it, or the filter needs a signal that survives the
short-circuit. `UX-524`'s measured touch map is the candidate: it
knows which test files a module's change really reaches, and it is not
the grep.

Whichever is chosen, the gate's line must not present an unfiltered
report as a filtered one.

## Out of Scope

- Whether `test_the_query_asks_about_this_run.py` is genuinely slower
  on CI. The measurement above says the file did not change; whether
  CI's 36.9s is contention belongs to `UX-543`/`UX-546`'s family, and
  splitting it out keeps this row about the filter.
- Loosening the drift gate's threshold, or widening `EVERYTHING`.
  Neither is the defect: the short-circuit is correct as a *selector*
  and wrong only as a *cause*.
- Re-recording `tests/ci_reference.json`, which `UX-420` says is
  adopted from CI and not hand-written.

## Acceptance Test

```bash
python3 tools/dev_touching.py --base origin/main --why | grep -c '<- None'
```

Zero, on a diff that touches `tests/tiers.py`. And the gate's summary
line names whether a cause filter was applied.
