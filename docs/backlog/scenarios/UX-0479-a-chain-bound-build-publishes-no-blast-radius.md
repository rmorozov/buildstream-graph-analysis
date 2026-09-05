# UX-479: a chain-bound build publishes no blast radius, so the recipe-author never learns what their element reaches

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 72, `UX-468`'s planted walk 2 | **Serves:** the recipe-author who owns the element every other element waits for, and is shown three elements that are worth nothing to fix | **Topic:** analysis | **Area:** bga

## Motivation

`UX-468` generated a project whose whole defect is one fat shared base:
`base.bst` is a build dependency of six apps, costs 21.0s of a 22.0s
critical path, and stages 20,000 files. The recipe-author's published
reader on that run:

```text
"id": "recipe-author",
"question": "Is my element a problem, and what does changing it cost?",
"leads_with": "latent-heavies",
"findings": ["latent-heavies"]

Waiting off the critical path, worth nothing to fix today: app1.bst (1s),
app2.bst (1s) (+1 more) - they bound how far shortening the chain can go
```

The reader's own question is *what does changing it cost*, and the
answer offered is about three other elements that cost nothing. **No
blast-radius finding fired at all:**

```console
$ bga analyze @last --diagnostics --format json | jq -r '.findings[].id'
wait-category  time-concentration  mesh-graph  joint-saving  latent-heavies
cache-hit-ratio  confidence  memory-envelope  capacity-recommendation
criticality  certified-headroom  efficiency-score
```

The mechanism is one branch, closed twice
(`bga/findings.py:1329`, `bga/findings.py:1111`):

```python
    if chain_bound and heaviest_on_path(result):
        ...                                     # the chain-bound arm
    else:
        findings.extend(_ranking_findings(result, chain_bound))

def _ranking_findings(result, chain_bound):
    if chain_bound or not top_blast_radius:
        return []
```

`UX-474` recorded the inner guard as **unreachable** — found while
mutating for `UX-467`, because the caller already decided. This walk is
what the outer branch costs: a build that is chain-bound publishes no
blast radius for any actionable element, and *a build gated by one fat
shared base is exactly the shape that is chain-bound.* The reach is
computed (`elements.blast_radius` carries it) and reaches no reader.

The only blast finding that survives the branch is
`blast-radius-structural`, which selects on `is_structural_kind` —
correctly, `UX-76`/`UX-258`: a toolchain has a thousand dependents on
purpose and that is a fact about the graph, not a task. On the walk's
other two projects it therefore named only the generator's scaffolding:

```text
Reaching most of the graph by design: toolchain.bst (7 downstream),
runtime.bst (7 downstream) - structural elements (import) whose
dependents are the graph's shape, not a task
```

So R2's two graph-shaped findings between them cover the `import` that
nobody edits and nothing else.

## Required Fix

- **Publish the reach on a chain-bound build too.** What `UX-258`'s
  rule excludes is *structural kinds from the ranking*; nothing in it
  says a chain-bound build has no elements worth ranking. Either the
  outer branch stops being exclusive, or the chain-bound arm carries
  its own reach sentence. Say which and why in the code, since the
  branch has now been read wrongly twice.
- **Then delete the inner guard**, which `UX-474` already found cannot
  fire — or, if the outer branch stays, keep it and say in the
  docstring that it is a second belt, so the next mutation round is not
  misled again.
- **A guard whose fixture is chain-bound.** `UX-464`'s
  `shared_base_wide` and this row's `planted-fat-shared-base` are both
  that shape. The clause: a chain-bound run over a graph with one
  6-dependent element publishes a finding naming it, for
  `recipe-author`. It reddens today.

## Out of Scope

- **`blast-radius-structural`'s kind filter.** `UX-76` and `UX-258`
  argued it and the argument holds; a `manual` element with six
  dependents is not the same claim as a toolchain with a thousand.
- **`latent-heavies`.** Its sentence is true — those apps really are
  worth nothing to fix today. It is the wrong lead, not a wrong
  finding, and it becomes the right lead once R2 has the other one.
- **`UX-474`'s own subject**, the ranking that publishes a list of
  zeros. That is the *content* of the finding when it does fire; this
  is about the run where it does not fire at all.

## Acceptance Test

```bash
python3 tools/bga_gen_project.py \
    --spec tests/fixtures/specs/planted-fat-shared-base.json --out /tmp/base
cd /tmp/base && bga snapshot -- bst build all.bst >/dev/null
bga analyze @last --diagnostics --format json | python3 -c '
import json,sys
d = json.load(sys.stdin)
r = next(x for x in d["readers"] if x["id"] == "recipe-author")
print(r["leads_with"], r["findings"])'
```

names a finding whose text carries `base.bst` and its downstream count.

## Outcome (round 73, 2026-09-01) — 🟢 Done

### The gap, measured

`UX-464`'s `shared_base_wide`, built at capacity so the chain is the
run, with a base someone owns rather than an `import`. Eleven
elements, one of which six depend on:

```text
chain_bound 1.0 task_horizon
['execution-bound', 'time-concentration', 'blast-radius-structural',
 'joint-saving', 'optimization-horizon', 'latent-heavies',
 'confidence', 'criticality', 'efficiency-score']
recipe-author: latent-heavies ['blast-radius-structural', 'latent-heavies']
```

The reader whose question is *what does changing my element cost* leads
with a finding about three other elements that cost nothing, and the
one element with six dependents is named nowhere. Same graph, two
lanes instead of six:

```text
scheduler_bound 0.549 task_horizon
['wait-category', 'blast-radius-ranking', 'blast-radius-structural',
 'confidence', 'criticality', 'certified-headroom', 'efficiency-score']
```

The reach is computed either way — `elements.blast_radius` carries
`toolchain.bst: 6` in both payloads. Only the diagnosis decided
whether any of it reached a reader.

### After

The Acceptance Test, on `UX-468`'s planted project:

```console
$ python3 tools/bga_gen_project.py \
      --spec tests/fixtures/specs/planted-fat-shared-base.json --out /tmp/base
{"out": "/tmp/base", "name": "planted-fat-shared-base", "elements": 8}
$ cd /tmp/base && bga snapshot -- bst build all.bst >/dev/null
$ bga analyze @last --diagnostics --format json | python3 -c '...'
blast-radius-reach ['blast-radius-reach', 'blast-radius-structural', 'latent-heavies']

diagnosis: chain_bound 0.99 task_horizon
   blast-radius-reach | What a change to these rebuilds: base.bst (7 downstream),
     app0.bst (1 downstream), app1.bst (1 downstream) - the cost of touching them
     is not their own duration but everything downstream that has to be built again
   blast-radius-structural | Reaching most of the graph by design: toolchain.bst
     (8 downstream), runtime.bst (8 downstream) - structural elements (import)
     whose dependents are the graph's shape, not a task
```

`base.bst` with its downstream count, led with, for the recipe-author.
That is `UX-468` walk 2's answer key.

**One thing the Acceptance Test as written cannot do twice on the same
machine**, and it is worth recording rather than quietly working
around: the generated project is deterministic, so a second run of
those exact commands hits the artifact cache and the build is
incremental. Measured — `diagnosis: inconclusive`, three findings, no
`recipe-author` reader at all, because a run with no task durations
has no chain share to compare. The figures above are from
`XDG_CACHE_HOME=/tmp/ux479cache bga snapshot -- bst build all.bst`,
which is the reproducer a later round needs.

### The fix: one gate on one claim, not one gate on three

`_ranking_findings` makes three claims and had one `chain_bound` gate
in front of all of them, with `compute_findings` branching on the same
value and calling it only in the `else`. Separated:

- `blast-radius-ranking` — *which element to shorten first*. `UX-65`
  argued this is the graph's question, and on a chain
  `time-concentration` already orders the same names (`UX-76`'s one
  table). **Still gated**, now by `shown` rather than by an early
  return.
- `blast-radius-reach` — *what a change to this element rebuilds*.
  New, `medium`, reader `recipe-author`. Published either way.
- `blast-radius-structural` — *these reach most of the graph by
  design*. A fact about the graph's shape; gating it on the diagnosis
  was never argued for anywhere.

The early return became `if not top_blast_radius`. The inner
`chain_bound` half — the one `UX-474` found unreachable while mutating
for `UX-467` — is deleted rather than kept as a belt, because the
caller no longer decides and a second copy is what got this read
wrongly twice. The docstring says all of that, since the Required Fix
asked for it in the code.

`blast-radius-reach` selects on `downstream_count > 0` rather than
truncating a pre-sorted list, so it is born without `UX-474`'s defect:
it cannot publish a row reading "0 downstream". The clause that says
so is asserted, not assumed.

### The census

```console
$ python3 tools/dev_finding_coverage.py | tail -1
(a clone) 22 findings | 20 produced by a capture | 2 declared unreachable | 0 neither
```

`blast-radius-reach` reaches five committed captures
(`a_build_that_pulls`, `macro_micro`, both halves of
`same_build_twice`, `with_timeline`); `blast-radius-ranking` still
reaches two (`one_source_many_elements`, `shared_base_wide`). The
21st and 22nd findings are `UX-473`'s two, produced in CI by a
generated failing build.

### What it cost the export, and what that turned up

`macro_micro`'s export went past its stated 450,000 B bound, and the
first split said why:

```text
findings         13,145 -> 14,630   (+1,485)
provenance        8,262 -> 13,217   (+4,955)
readers           1,163 ->  1,216   (+53)
```

**The provenance record was three times the finding it explains.**
Both blast claims cited `elements.blast_radius` — the whole map — and
`bga/provenance.py::record` inlines whatever a path resolves to, so
the run carried that population three times: once published and once
inside each claim. `UX-288`'s rule, which `UX-344` had applied to the
finding itself and not to the record beside it.

Nothing had ever caught it because **neither committed fixture had
ever produced a blast finding**: both golden and `macro_micro` are
chain-bound, and the arm that publishes these is the one this item
opened. Opening it turned the latent duplication into fifteen red
guards, and the three that named it were right:

```text
tests/test_golden.py::test_mixed_task_kinds_golden_snapshot
test_no_level_carries_nothing.py::test_every_map_keyed_by_a_uid_declares_its_values[golden]
test_no_level_carries_nothing.py::test_fewer_leaves_are_deeper_than_three[golden]
test_every_number_says_what_it_is.py::test_nothing_renders_from_a_guess[golden]
  golden: 8 numeric leaves render from a name-sniffed guess:
  ['provenance.[].evidence.[].value.app.bst.downstream_count', ...]
... 15 failed, 5599 passed, 27 skipped in 429.41s
```

`downstream_count` under a uid key is a leaf the schema describes at
`elements.blast_radius.*.downstream_count` and cannot describe at
`provenance[].evidence[].value.<uid>.downstream_count`.

So both blast claims now cite one scalar per element they name, which
the path grammar's bracket form (`UX-227`) makes expressible at all —
a uid contains dots:

```json
{"path": "elements.blast_radius[base.bst].downstream_count",
 "value": 2, "resolved": true, "quantity": "count"}
```

Provenance: 13,217 B → **10,039 B**, against 8,262 B before either
claim could fire. The re-measured export:

```text
                   page      golden data   macro_micro data
before          291,588 B      110,076 B          158,276 B
after           291,588 B      111,730 B          161,592 B
                    +0 B       +1,654 B           +3,316 B
```

Not one byte of page. `macro_micro`'s bound moves 450,000 → 458,000
with that table pasted above it; golden's 406,000 stands. Both
recorded figures were stale — golden by 152 B, `macro_micro` by
2,825 B, so the bound had 136 B of headroom rather than the ~3 KB its
comment claimed.

> **Annotated by `UX-493` (round 75): golden's 406,000 did not stand.**
> `UX-469` closed later the same day and moved it 406,000 → 411,000, at
> 407,265 B — its +2,228 B (2,114 source, 114 payload) tripped the
> bound this sentence had just left standing. The tree carries
> `("golden", GOLDEN, 411_000)`. `macro_micro`'s 458,000 above is
> still the tree's (457,284 B, 716 B of headroom). The measurement is
> right as of this item's run and is not revised; what was missing is
> the line beside it, because round 73 did not run
> `git grep 406,000 docs/backlog/scenarios` before committing `UX-469`.

**`UX-483`** is what is left: the builder will inline the next
population just as happily, and the fifteen guards caught this one
only because it happened to be uid-keyed and numeric.

### Two guards that were reading a proxy

`test_element_kind_heuristics.py::test_key_findings_tags_structural_top_element_but_not_real_work_one`
and
`test_headline_points_at_the_time.py::test_structural_elements_are_excluded_not_merely_tagged`
both asserted a structural element's name was **absent from the whole
block**, as a proxy for "it is not ranked". That held only while
`blast-radius-structural` could not fire on their fixtures — both are
chain-bound. It fires now, and the guards caught the sentence
`UX-258` added on purpose:

```text
Reaching most of the graph by design: bootstrap/symlinks.bst (124 downstream)
  - structural elements (unknown) whose dependents are the graph's shape,
    not a task
```

Fixing guide §5: an instrument reading a proxy for the thing it names.
Both now slice the table's own rows — four-space indent under the
heading, where the report is at two — and assert **both** halves of
`UX-258`'s split: not in the ranking, and named in the report with its
reach. Which is more than they asserted before.

One of the two turned out to have a non-discriminating half, and it is
written into the file rather than quietly left:
`bootstrap/symlinks.bst` appears in that fixture's `blast` map and in
no element's duration detail, so nothing could ever have ranked it —
M7 below leaves that clause green. Its positive half is what carries
it, and M8 reddens that.

### Mutations verified red and reverted (8)

Each mutation was written to a file and applied by a script that
asserts the anchor matches exactly once, and each row's landing was
proved with a `grep -c` before the run. Counts are what pytest
printed.

| # | mutation | reddened |
|---|---|---|
| M1 | the outer `else:` in `compute_findings` put back, so `_ranking_findings` is called only on the scheduler-bound arm | 5 of 10 — the four chain-bound clauses and the structural pair |
| M2 | the inner `if chain_bound or not top_blast_radius: return []` put back — the guard `UX-474` found unreachable | the same 5 |
| M3 | `if reaching and not shown` → `if reaching`, so reach fires on both arms | 1 — `test_the_same_graph_below_capacity_ranks_instead` |
| M4 | `reaching = list(actionable)`, dropping the `downstream_count > 0` filter | 3 — the naming clause, the zeros clause, and the structural-only case, which starts publishing a reach of six zeros |
| M5 | `shown = actionable[:BLAST_RADIUS_SHOWN]`, ungating the ranking as well | 4, including `test_the_ranking_stays_gated_on_the_chain` |
| M6 | `CHAIN_BOUND_RATIO = 1.01`, so no run can be chain-bound | 7, including `test_at_capacity_is_chain_bound` — which is what says the setup clauses are not vacuous |
| M7 | `real = [d for d in detail if d.get('duration_us')]` — the ranked table stops excluding structural kinds | 1 of 2 — `test_element_kind_heuristics`, whose `root.bst` carries a duration; the headline fixture's does not, recorded above |
| M8 | M2 again, against the two repointed guards | both — each one's "named in the structural report" half |

M6 is the one that matters for `CLAUDE.md`'s standing trap. Every
clause in this file turns on the diagnosis, so a fixture that silently
stopped being chain-bound would have made the whole file pass on
whatever the gate under test did. The diagnosis is asserted first,
separately, and M6 proves that assertion discriminates.

### The fixture

`shared_base_wide` gains `base_kind` (default `"import"`, unchanged)
and its `lanes` docstring is corrected: it said *"`_ranking_findings`
returns nothing at all on a chain-bound run"*, which was true when it
was written and is the sentence this row falsified. The covering set's
committed capture is byte-identical — the census above is over the
same tracked runs.

### Deviation from the Required Fix

Two things done that the Required Fix did not ask for, both because
`make test` was red without them and neither is a choice about scope:
the two blast claims' provenance paths, and the two proxy-reading
guards. Both are recorded above with their measurements. The
provenance narrowing is the only one that changes what the tool
publishes, and it makes the record smaller and more precise rather
than saying anything new.

Otherwise none. All three clauses done: the branch stops being exclusive (with
the reason in the docstring, since it had been read wrongly twice),
the inner guard is deleted rather than kept, and the guard's fixture
is chain-bound and reddened by six mutations.

The Required Fix suggested `shared_base_wide` or
`planted-fat-shared-base` as the guard's fixture. `shared_base_wide`
at its committed parameters is neither — it is scheduler-bound by
construction (`lanes=2 < dependents=6`) and its base is an `import`,
so it has no actionable element with a dependent at all. The guard
uses the same factory at `lanes=6, base_kind="manual"`, which is that
shape; `planted-fat-shared-base` needs a real `bst` and is the
Acceptance Test above rather than a unit guard.

### The runs

```text
python3 -m pytest tests/unit/test_a_chain_bound_build_still_has_a_blast_radius.py
                                              10 passed in 0.32s
python3 -m pytest tests/unit/test_the_report_you_can_attach.py
                                              24 passed in 5.45s
make test-touching                            684 tests, 1 failed -> the export
                                              bound above, then green
make test                                     15 failed, 5599 passed, 27 skipped
                                              in 429.41s -> the provenance map
                                              and the two proxy guards, then
                                              5614 passed, 27 skipped, 1 warning
                                              in 318.06s (0:05:18)
make lint                                     All checks passed!
```

`make test-touching` is a selector and it selected 684 tests that all
passed while fifteen others were red: the grep names modules a diff
touches, and `test_no_level_carries_nothing` and
`test_every_number_says_what_it_is` read the *payload*, not
`findings.py`. That is the gap §3 states and this round paid it once.
