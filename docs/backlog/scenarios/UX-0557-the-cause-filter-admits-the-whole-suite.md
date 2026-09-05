# UX-557: the drift gate's cause filter admits all 424 files, and `--why` cannot say so

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-476 (which built the filter), UX-442 (the carry), UX-524 (the map) | **Serves:** the round whose PR the gate reddens | **Topic:** guards | **Area:** tools

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

A second file joined the report on the fifth run, and it is the same
shape. `tests/unit/test_docs_links_and_commands.py` at 16.2s against
10.0s recorded, x1.58 — plausibly this round's doing, since that file
walks the backlog and the round added rows. Measured, it is not:

```text
backlog files: base 550, branch 557
rep1 base 7.56s   rep1 branch 7.22s
rep2 base 7.54s   rep2 branch 7.66s
```

So the gate has now named two files, neither of which is slower on this
branch when measured, and it cannot tell them apart from one that would
be — because the filter that was supposed to make that distinction
admits all 424.

Two consequences, and the second is the one that reddened a PR:

1. The reason is keyed `"*"` and `--why` reads `why.get(name)`, so all
   424 print `None`. "Which selected each file" — the question
   `make test-touching ARGS=--why` exists to answer — goes unanswered
   exactly when the answer is most surprising.
2. The gate reports on `UX-442`'s consecutive agreement alone. That is
   the state `UX-476` was written to leave behind, and its outcome
   says so.

### Correction: the mechanism, read from the code rather than inferred

The filing above says the gate treats all 424 as *explained*. It does
not — `UX-494` already caught that, and `explained_by` detects the
`"*"` fallback and refuses. The defect is one step further on:

```python
explained_by(...)  ->  None          # "the diff could not be read"
repeated(...):     elif explained is None or row[0] in explained:
                       confirmed.append(row)      # -> the build fails
```

`UX-494` made the shared-harness case return the **same `None`** as a
failed fetch, and `None` is documented as "confirm on agreement, so a
failed fetch is loud rather than silently green". So the two situations
share a verdict while being opposites: a failed fetch is *no
information about the diff*, and the shared-harness case is *complete
information the selector cannot use*.

That is why five consecutive runs failed on a file measured unchanged.
The gate was not fooled into thinking the diff explained it; it was
told to confirm because no filter could run.

## Required Fix

The `"*"` reason must reach the reader: `--why` should print the
short-circuit's own sentence for each file. That is the smaller half.

The gate half is the decision, and it is a **third** verdict, not a
better filter. "Cannot read the diff" and "cannot discriminate on the
diff" must stop sharing `None`. A row with no cause evidence belongs
in `UX-476`'s `unexplained` bucket — printed with its readings, not
failed on — which is exactly what `UX-476` argued for the case where
the diff names nothing. Naming nothing and being unable to ask are the
same amount of evidence.

`UX-524`'s measured touch map was considered and not used: it answers
"which test files did this module's change reach", which is a better
selector, not a cause. It would narrow the set, and a narrower set that
still cannot see a browser file's wall clock would fail the same way.

The gate's line must not present an unfiltered report as a filtered one.

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

## Outcome (round 81, 2026-09-03) — 🟢 Done

**Premise:** falsified — `UX-494` had already fixed the cause filter; the defect was one step on, `None` read as "diff unreadable".

### The gap, measured

Five consecutive `test (3.11)` runs red on the drift gate, never on a
test, on a file measured unchanged by the branch:

```text
d7b68ee  test_the_query_asks_about_this_run.py 36.9s vs 19.7s  x1.88
4d8c14a  (same)
b3f10d4  (same)
5a384fa  34.6s  x1.69
39ce82b  36.9s  x1.83; and test_docs_links_and_commands.py 16.2s vs 10.0s x1.58
```

Both files, interleaved against the merge-base, single process:

```text
query_asks   base 21.16/21.66s   branch 19.83/20.48/20.92s   13 tests both
docs_links   base  7.56/7.54s    branch  7.22/7.66s          550 vs 557 rows
```

And the reader could not see why:

```text
$ python3 tools/dev_touching.py --base origin/main --why | grep -c '<- None'
424
```

### After

```text
$ python3 tools/dev_touching.py --base origin/main --why | grep -c '<- None'
0
$ python3 tools/dev_touching.py --base origin/main --why | head -2
tests/test_cli.py
    <- shared harness changed: ['pyproject.toml', 'tests/conftest.py', 'tests/tiers.py']
```

The four cause states, driven through `repeated` with this branch's
own row and history:

```text
shared harness (this branch)   confirmed=0 unexplained=1 -> reports
diff unreadable                confirmed=1 unexplained=0 -> FAILS
diff names it                  confirmed=1 unexplained=0 -> FAILS
diff names something else      confirmed=0 unexplained=1 -> reports
```

Real drift still fails. Only the row with no cause evidence reports.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| M1 | `NO_CAUSE_FILTER` → `None` (UX-494's state) | `test_a_selector_that_names_everything_is_no_explanation`, `test_a_tiers_edit_is_no_evidence_either_way` — 2 failed, 1 passed |
| M2 | the sentinel confirms instead of reporting | `test_no_cause_filter_reports_rather_than_failing` — 1 failed, 2 passed |
| M3 | an unreadable diff reports instead of confirming | `test_an_unreadable_diff_confirms_on_agreement_alone` — 1 failed, 2 passed |
| M4 | `--why` drops the `'*'` fallback lookup | `<- None` back to 424 of 424 |

### The filing's own mechanism was wrong

The Motivation said the gate treats all 424 files as explained. `UX-494`
had already fixed that, and `explained_by` refuses correctly. The real
defect was one step on: the refusal returned `None`, which `repeated`
reads as "the diff could not be read" and **confirms** on. Two opposite
situations — no information, and complete information the selector cannot
use — shared the verdict that fails the build. The correction is in the
Motivation above rather than rewritten over, because a later round reading
this needs to know the first reading was wrong and how.

### Deviation from the Required Fix

**One.** The Required Fix offered `UX-524`'s touch map as the candidate
for a filter that survives the short-circuit. Not used: it answers
"which test files did this module's change reach", which is a better
*selector*, not a cause. A narrower set that still cannot see a browser
file's wall clock fails the same way. The third verdict is the fix.
