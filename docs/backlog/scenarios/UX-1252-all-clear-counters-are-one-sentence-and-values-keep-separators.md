# UX-1252: zero counters take a row each, counts lose their separators, and an absence names the wrong series

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding L2 | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_an_all_clear_run_is_one_sentence.py` (browser, `macro_micro` + served two-plane store) and `tests/unit/test_a_quantity_is_formatted_where_it_is_shown.py` (bare count, raw seconds; 1,200-element `counted` page)

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §L2).

- `#plane2_coverage` spends six rows on 0 or none (CPU reconciled, exec chains, fork-only exits, unmatched ends, disagreements, aggregate); `#floors` spends five on the absent cold path (none, no, none, none, none).
- "2194 downstream" in the decision and finding lists, "1978 upstream" in a finding title; the next finding reads "2,194" (`UX-1213`'s residue).
- `#utilization_envelope` asks "Were the cores the binding resource?" and answers that the capture "has no host memory series".
- `#floors`' capacity note prints "605.81 s" one row above "LB CPU 10.1 min", the same quantity.
- In the rail, the hidden-until-needed "· save trace" breaks after its separator, leaving a lone "·" line.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     (a) renderPairs folds a run of >=2 0/none/no/empty values in one dl into "None: A, B, C."; JSON keeps every field. (b) rail "· save trace" nowrap. (c) findings.py:1763,1914,1952,1971 use {n:,}. (d) analyzer.py:2098's absence names the host CPU series. (e) cli.py:168 uses qty.duration. (f) styleguide §6e.12 extended.
Rejected:  per-section sentences (drift); viewer patches of Python prose (a second formatter).
Files:     bga/viewer/pairs.js, bga/viewer/style.css, bga/findings.py, bga/analyzer.py, bga/cli.py, docs/design/styleguide.md, tests/unit/test_an_all_clear_run_is_one_sentence.py, tests/unit/test_a_quantity_is_formatted_where_it_is_shown.py
Guard:     no dl.pairs with two consecutive 0/none rows; no rail line holding only "·"; cores absence names CPU; no bare 4+ digit count and no \d+\.\d\d s in prose.
Mutation:  fold off; drop :, at findings.py:1952; restore :.2f} s; restore "memory".
Class:     product
Split:     A viewer (a,b,f) parallel; B Python (c,d,e) after 1245/1246/1248/1249. Fold applies page-wide (reversible default).
```

## Required Fix

Styleguide §6e.12 extends: a run of zero or absent counters in one block is one sentence naming them; every count in reader text carries the group separator; an absence names the series its question reads; a quantity in prose uses the duration format its row uses.

## Out of Scope

The fields themselves; the JSON door keeps every one.

## Acceptance Test

On this page no block shows two or more consecutive zero/none rows, no four-digit count lacks a separator, the cores question's absence names CPU, and no prose duration is a raw seconds float. Mutation: restore the rows, and the guard reds.

## Outcome

Gap measured (base `9a1c124f`; the Motivation's 2,402-element page rebuilt, `bga view @last --reanalyse --export`, and
`macro_micro`; text nodes outside `code, pre, td`, details open, Chromium 1440x900 and 390x844, both widths alike):

```text
                                 2,402 before   2,402 after   macro_micro after
dl.pairs clear rows running            17             0             0
folded "None: ..." rows                 0             8            10
bare 4+ digit counts                    9             0             0   (decision "2194 downstream" x2, blast x3, fan-in x3, "1978 upstream")
"\d+.\d\d s" in prose                   1             0             0   (floors note "605.81 s" -> "10.1 min")
cores absence             "no host memory series" -> "no host CPU series"
served rail "· save trace", 1440    2 lines -> 1   (`.toc a { display: block }` put the link under its "·")
```

Close measured (`test_the_page_has_a_volume_budget.py`'s `_LOOK`, 1440x900, same paths before/after):

```text
                         before      after     bound
macro_micro opened px    37,805     37,287    39,188
macro_micro words        13,338     13,361    13,500   (textContent glued dt to dd: "elements0Hit" was one token; per text node 17,430 -> 17,416)
macro_micro controls        872        872       872
xl_both opened px        44,292     43,852    46,822
xl_both words            13,160     13,190    13,200
xl_both controls          1,190      1,190     1,192
page bytes              162,460    162,936   165,000
macro_micro data half   100,278    100,229   100,000   (this tree's longer path; -49 B, the absence sentence)
```

| Mutation | Reddened | Count |
|---|---|---|
| fold off (`empty: false` in `renderPairs`) | `test_no_block_draws_two_clear_rows_running` [macro_micro, two_plane] | 2 failed |
| rail CSS removed (`nowrap` + inline link) | `test_the_rail_separator_keeps_its_link[two_plane]`, 2 lines at 1440 | 1 failed |
| absence back to "host memory series" | `test_the_cores_absence_names_the_cpu_series` | 1 failed |
| `{count:,}` -> `{count}` at the blast-radius line | `test_no_count_lacks_its_separator[counted]`, 3 bare | 1 failed, 3 passed |
| `tally()` dropped from `decision.js`'s reach | `test_no_count_lacks_its_separator[counted]`, 2 bare | 1 failed, 3 passed |
| `{lb_cpu_us / 1e6:.2f} s` restored in `cli.py` | `test_no_prose_duration_is_raw_seconds` [macro_micro, two_plane] | 2 failed, 2 passed |

Deviation: a row carrying the run's advice (`attribution`'s buckets, `UX-390`) and a signed delta keep their rows; `decision.js`,
outside the Decision's Files, printed the decision list's "2194 downstream"; textContent words +23 on `macro_micro`, under its bound.
