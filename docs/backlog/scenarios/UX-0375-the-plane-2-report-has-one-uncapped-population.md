# UX-375: the Plane 2 report has one uncapped population

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-297 (extraction streams), UX-300 (what a two-gigabyte snapshot does to a store) | **Serves:** anyone whose store has to hold a monorepo's captures | **Topic:** capture

## Motivation

Round 60 asked whether Plane 2 capture is memory-bounded all the way to
the capture directory. On disk it is, and the numbers say so. Five
generated projects, each element a real `make -j4` over gcc, built and
captured with `bga snapshot` on a 4-core host:

```text
elements x native components            procs     raw log plane2.json    snapshot  peak RSS
1 x (4 so, 2 a, 2 exe, 1 static)           57          4k         10k         65k    36.8 M
1 x (100 so, 10 a, 10 exe, 1 static)      609         37k         10k        104k    37.7 M
4 x (100 so, 10 a, 10 exe, 1 static)    2,436        153k        198k        432k    40.6 M
10 x (100 so, 10 a, 10 exe, 1 static)    6,090        379k        248k        753k    46.2 M
40 x (100 so, 10 a, 10 exe, 1 static)   24,360       1565k        506k       2414k    74.9 M
```

The raw log is 64 B a process and the snapshot 97 B a process, both
flat — the hook appends and never buffers. Extraction is 1,644 B a
process, which is `UX-297`'s documented `O(processes)` floor re-measured
on real captures rather than on a generated trace, and extrapolates to
**4.1 GB resident at the 2.7 M processes `UX-297` names**. That is the
known floor, `UX-313` answered it, and this item is not about it.

**`plane2.json` is the column that does not track processes.** It goes
10k → 10k → 198k → 248k → 506k while the process count goes 57 → 24,360,
and one section is the reason:

```text
run   elems    stored  above 50ms     bytes  % of report
C         4       267         179   155,005        91.7%
D        10       267         206   174,399        87.2%
E        40       267         247   278,510        76.8%
```

`redundant_operations` is **77–92% of the Plane 2 report**. Its row
count is the number of distinct command signatures seen under 2+
elements — flat at 267 here because the source names are — and each row
carries an `elements` list that grows with the run, which is why the
bytes rise while the count does not.

It is the only population in `plane2/v2` with no cap. `binary_cost`
takes a `top_n` of 5; `by_binary`, `per_element_parallelism`,
`opens_captured` and `static_census` are `O(elements)` or
`O(distinct binaries)`. `detect_redundant_operations` returns every
finding and `load_and_summarize` writes the list whole
(`bst_native_build_tracer.py:4125`).

**The floor that exists is applied to the rendering, not to the
contract.** `_REDUNDANCY_MIN_SECONDS = 0.05` is read at line 4985, in
`_format_text`, which drops the sub-50ms findings from the terminal and
says how many it omitted. The stored JSON keeps all of them.

**What this does not cost.** The exported page does not carry the
section — checked on the 40-element capture:

```text
exported page (40 elements, 24,360 processes)
  whole file         2,481,631 B
  embedded data      2,213,872 B  (4 blocks)
  page source          267,759 B
  redundant_operations present in the embedded data: False
```

So the cost is store size and the memory to build and serialise the
list, which is `UX-159`'s and `UX-300`'s axis, not the page's.

## Required Fix

The section takes a stated bound, the way `binary_cost` has one:

- A cap on rows, ranked by the figure the section already ranks by
  (`max_element_duration_s`), with the number omitted published beside
  it rather than inferred — the shape `redundant_operations_coverage`
  already has for its two exclusion reasons.
- The 50 ms floor moves to where the list is built, so the contract and
  the terminal agree about what a finding is, or it stays in the
  renderer and the contract says explicitly that it holds findings the
  terminal will not show.
- Each row's `elements` list takes the same treatment: a count plus the
  worst element is what every consumer reads, and the full list is what
  makes the row grow with the run.

## Falsification

Generate two projects of the same element count and different signature
counts, capture both, and assert `len(redundant_operations)` is bounded
by the cap in each while `redundant_operations_coverage` names the
omitted count. Today the first assertion fails at any cap.

The other direction, so the fix is not "drop the section": the highest
`max_element_duration_s` finding on `tests/fixtures/macro_micro`
survives the cap unchanged, and the terminal renders the same list it
renders today.

## Out of Scope

- Extraction's `O(processes)` record list. Measured again here, answered
  by `UX-313`, unchanged.
- The exported page. It does not carry this section at all, measured
  above on the 40-element capture, so nothing here changes what a
  reader sees.

## Outcome

Round 61. The population is bounded, and the *other* half of the
Required Fix was declined with a measurement rather than done.

**The cap.** `REDUNDANCY_FINDINGS_MAX = 40`, applied after the ranking
that already existed, with what it dropped published. On the same
40-element capture the filing measured:

```text
                    before      after
findings stored        267         40
section bytes      278,510     32,728
share of report      76.8%      31.6%
```

40 rather than a round 10, and the same number as the viewer's
`TABLE_OPENS_BOUNDED_ABOVE`: it is what this repository already uses
for "more rows than a reader will act on", and the list is ranked by
the figure a reader acts on, which is what makes cutting the tail safe.

`redundant_operations_coverage` gains `findings_cap`,
`omitted_beyond_cap`, `total_findings` and `display_floor_seconds`, so
a shorter list cannot read as a cleaner build — `UX-73`'s own argument
for the two exclusion counts that were already there.

**The floor stayed in the renderer, and that is the finding.** The
Required Fix offered two endings: move `_REDUNDANCY_MIN_SECONDS` into
the contract so both agree, *or* leave it and have the contract say so.
Moving it looked obviously right. It is not, and the committed fixture
is what says so:

```text
tests/fixtures/macro_micro       20 findings
  below the 50 ms display floor  14
```

`correlate.py` iterates **every** finding to build each element's
`redundancy_count` and `worst_redundancy`. Moving the floor would have
silently changed a published per-element number on every capture, for a
reason no reader could see — a bigger defect than the one being fixed.
So the floor stays a display threshold, the contract states plainly that
the list includes findings the terminal will not show, and the terminal
now has two sentences rather than one: a finding can be missing for
being below the floor (it *is* in the JSON) or for falling outside the
cap (it is in no output).

This was found by writing the guard first. The clause asserting the
fixture's findings all clear the floor failed at 14 of 20, which is how
the wrong ending got caught before it shipped.

**`element_count` is added; `elements` is not bounded.** With the rows
capped, 64% of what remains is the `elements` lists, and they still
grow with the run — 20,400 B of the capped 31,888 at 40 elements.
Replacing that list with a count is what the filing's third bullet
asks, `correlate` is the only consumer and reads `worst_element`
instead, and removing a published key bumps `plane2/v2` to `v3` across
five files. The count is added now (additive, no bump); the removal is
`UX-384`.

### Falsification run

Six mutations against the committed tree. All six caught:

| # | Mutation | Caught by |
| --- | --- | --- |
| M1 | the cap is removed — the defect | 3 clauses |
| M2 | the cap is applied before the ranking | `test_what_survives_the_cap_is_the_most_costly` |
| M3 | the omitted count is not published | 2 clauses |
| M4 | the display floor moves into the contract after all | 2 clauses |
| M5 | the note stops saying the list holds what the terminal hides | `test_the_contract_says_the_list_holds_what_the_terminal_hides` |
| M6 | a finding stops carrying its element count | `test_a_finding_carries_its_element_count` |

M2 is the one worth keeping: a cap over an unranked list drops findings
by accident of dictionary order, and every other clause stays green
while it does.

### Verification Log

```text
$ python3 -m pytest tests/unit/test_the_population_that_had_no_ceiling.py -q
10 passed in 0.24s

$ bga capture report <40-element capture>/plane2.log.gz
Redundant cross-element operations (267 found, 40 above 0.05s):
  40x across 40 elements (mod0.bst, ...) - up to 0.781s recoverable
  wall-clock (worst element: mod23.bst); 12.756s total machine time
    gcc -O0 -fPIC -static -o fs0 fs0.c
  (227 further finding(s) fall outside the 40-finding cap and are in no
   output; the list is the most costly first, so these are the cheapest
   of what was found)

$ coverage
{"findings_cap": 40, "omitted_beyond_cap": 227, "total_findings": 267,
 "display_floor_seconds": 0.05, ...}
```

Tiered small on landing at 0.24s.
