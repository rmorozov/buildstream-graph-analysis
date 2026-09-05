# UX-494: the drift gate's explanation filter names the whole suite, so it explains nothing

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-476` built it; `UX-488` is the run that exposed it | **Found by:** round 73, driving PR #191 to green | **Serves:** the contributor whose unrelated branch goes red on one runner's slow afternoon | **Topic:** guards | **Area:** tools

## Motivation

`UX-476` gave the tier-drift gate a second axis: a file over both gates
on two consecutive runs is *confirmed* only when the branch's own diff
could account for it; otherwise it is reported under `unexplained` and
**does not fail the build**. Its Outcome says so.

That bucket has been empty by construction since the day it landed.

`explained_by` asks `tools/dev_touching.select`, the selector behind
`make test-touching`. That function has a fallback:

```python
everything = [c for c in changed
              if any(c == e or c.startswith(e) for e in EVERYTHING)]
if everything:
    return sorted(test_files()), {"*": f"shared harness changed: {everything}"}
```

Change `tests/conftest.py` or `tests/tiers.py` and it returns **every
test file in the suite**. That is right for the question it was built
for — which tests to run, where missing one is the only failure that
matters — and it is no answer to *what could have made this file
slower*. Measured on this branch:

```console
$ python3 -c "from tools import dev_touching as t; c,w = t.select(t.changed_files('origin/main')); print(len(c), w)"
397 {'*': "shared harness changed: ['tests/conftest.py', 'tests/tiers.py']"}
```

397 of 397. So every row over both gates satisfies `row[0] in
explained`, lands in `confirmed`, and fails the build **on a single
run** — strictly worse than the `explained is None` path, which at
least waits for agreement across two.

It fired for real on run `33552128782`. Three browser guards read
1.5–2.3× their reference:

```text
file                                       08490f5  3dd6e03  5705840   spread
test_emphasis_is_a_budget.py                 15.66    15.52    36.34   x2.34
test_a_sentence_lives_on_its_door.py         23.63    23.91    39.75   x1.68
test_a_control_acts_on_what_it_names.py      36.32    36.99    55.77   x1.54
test_the_page_has_geometry.py                68.57    68.87    68.29   x1.01
test_the_two_capabilities_are_offered.py     31.38    31.32    31.97   x1.02
```

Nothing in that branch's diff can reach them — they are Chrome-driven
guards importing `browser` and `pages`, and the diff was documentation,
`tests/ci_reference.json`, and two unrelated test files. The last two
rows are the control: heavy browser files that did **not** move, so the
runner was not uniformly slow. One excursion on three files, failing
the build with no second run to confirm it.

This is fixing guide §5 and CLAUDE.md's most-sighted defect, in the
guard written to enforce them: **an instrument reading a proxy for the
thing it names.** `test-touching`'s selection is a proxy for causal
explanation, and it is deliberately generous — the one property that
makes it useless here.

## Required Fix

- The shared-harness fallback reads as **no evidence** (`None`), not as
  a diff that names every file. `repeated` then confirms on agreement
  across `CI_DRIFT_RUNS`, which is `UX-442`'s behaviour and the
  documented meaning of `None`.
- A clause that reddens when the fallback is read as an explanation
  again — exercised **with the fallback firing**, not with an empty
  diff beside it.
- `UX-476`'s Outcome annotated: it claims a behaviour the code did not
  have.

## Out of Scope

- `dev_touching.select` itself, which is correct for its own question
  and whose fallback `UX-336` put there on purpose. This row changes
  the *reader*, not the selector.
- Sizing `CI_DRIFT_FACTOR`, which is `UX-458`'s question and needs the
  second spread `UX-488` has now put in the reference.
- Whether those three browser guards are genuinely unstable under
  `-n auto`. Three sightings this round say maybe; that is `UX-495`.

## Acceptance Test

```bash
python3 -c "from tools import dev_tier_drift as d; print(d.explained_by('origin/main'))"
```

printing `None` on a branch whose diff touches the shared harness, with
the mutation that reintroduces the defect shown red.

## Outcome (round 73, 2026-09-01) — 🟢 Done

### The gap, measured

```console
$ python3 -c "from tools import dev_touching as t; c,w = t.select(t.changed_files('origin/main')); print(len(c))"
397
$ python3 -c "from tools import dev_tier_drift as d; print(d.explained_by('origin/main'))"
{... all 397 test files ...}
```

Every file over both gates therefore read as caused by the branch, and
run `33552128782` went red on one sample — the run that also proved
`UX-488`'s refresh worked, since the gate ran at all for the first time
since `a54c235`.

### After

```console
$ python3 -c "from tools import dev_tier_drift as d; print(d.explained_by('origin/main'))"
None
```

`repeated` now puts those three rows in `waiting`: printed with their
numbers, not failed on, until a second run agrees.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| D1 | the fallback is read as an explanation again (`if False`) | 1 of 83 — `test_a_selector_that_names_everything_is_no_explanation` |
| D2 | every diff reads as no evidence (`if True`) | 1 of 83 — `test_a_base_that_does_not_resolve_is_no_evidence_at_all`, which holds the other direction |

### The guard of mine that did not discriminate

**D1 passed on the clause's first writing.** It asserted that
`dev_touching.select(["tests/conftest.py"])` reports `"*"` — a property
of the *selector*, not of the fix — and then called
`explained_by("HEAD")`, whose diff is empty, so the fallback never
fired and the second assertion was vacuous. Rewritten to monkeypatch
`changed_files` so the fallback fires inside `explained_by`, after
which D1 reddens. Three clauses in this round have now failed this way
on first writing; the pattern in all three is asserting a *shape* near
the thing instead of the thing.

### The runs

```text
python3 -m pytest tests/unit/test_a_slow_file_says_which_file.py -q
83 passed in 1.00s

make test  5,689 passed, 27 skipped in 339.27s (0:05:39)
make lint  ruff + PyMarkdown, both clean
```

### Deviation from the Required Fix

None.
