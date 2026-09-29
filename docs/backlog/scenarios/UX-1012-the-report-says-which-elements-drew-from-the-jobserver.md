# UX-1012: the report says which elements drew from the jobserver, not only which were offered it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1005 | **Found by:** Ruslan on the Graviton thread (2026-09-25): "does bga show in report which elements actually used jobserver and which are not?" | **Serves:** R4, R5 | **Topic:** analysis | **Area:** bga | **Shape:** mechanical | **Reading:** container

**Guard:** test_the_report_says_which_elements_drew.py

## Motivation

`jobserver.per_element[uid].joined` (`bga/correlate.py:1404-1451`)
reads `yes | pinned | held | unknown_kind`, and `yes` is the offer, not
the draw. The draw is read from the element's peak width against its
own `max-jobs`, which lives in a separate table
(`per_element_parallelism`); the Graviton readings proved use that way
(`giant.bst` peak 8 -> 16, run 36116507787). The report never sets the
two side by side, and `bga analyze`'s terminal prints no per-element
jobserver line at all (`bga/report/text.py` never reads
`report["jobserver"]`; the only jobserver text is `bga compare`'s mode
header, `text.py:101-112`).

## Decomposition

surfaces: `bga/correlate.py` (the verdict), `bga/report/text.py` (the terminal table), the page's jobserver section
guards: an element whose peak exceeds its `max-jobs` under the pool reads `drew`; one joined at peak <= `max-jobs` reads `offered, not drawn`; `pinned` never reads `drew`
gap: what a `drew` verdict means once UX-1005 track B admits sandboxes on a token
track: after UX-1005

## Required Fix

One per-element table, terminal and page alike: joined, peak against
`max-jobs`, a `drew` verdict derived from the two, tokens held.

## Decision

Route:    `compute_jobserver_per_element` (bga/correlate.py, ~l.1530-1579) also takes `per_element_parallelism` and the admission wait by element (tools/jobserver/ledger.py ~l.77). Verdict: `drew` when joined and `peak_work_concurrency` > the element's own `max_jobs` from its decision row; `offered, not drawn` when joined and peak <= max_jobs; `pinned`/`held`/`unknown_kind` unchanged and never `drew`. Under admission the admission token is the element's implicit slot, not a draw, so `drew` keeps this definition; the admission wait prints as its own column. `bga/report/text.py` gets its first `report["jobserver"]` table (element, joined, peak/max-jobs, verdict, tokens held, admission wait). The page reads the same block through `bga/schemas.py`'s `_ANALYZE_HINTS["jobserver"]`.
Rejected: `drew` from `joined == "yes"` alone (that is the offer) · `drew` from `tokens_held_max` (under admission every sandbox holds one token).
Files:    bga/correlate.py, bga/report/text.py, bga/schemas.py, tests/unit/test_the_report_says_which_elements_drew.py
Guard:    peak 16 vs max-jobs 8 is `drew`; 8 vs 8 is `offered, not drawn`; pinned at peak 3 never `drew`; an element holding only an admission token at peak 1 is not `drew`; the text output prints the row.
Mutation: derive the verdict from `joined` alone (offered case reds); let `pinned` fall through to the peak test (pinned case reds).
Class:    product
Acceptance amended: the Graviton capture is not kept; the test runs on a synthetic Plane 2 fixture, and the real reading is taken on CI's `bst-examples` `11-serial-giant` auto run (giant at max-jobs 2 on a 4-core runner) when that artifact is available.

## Out of Scope

UX-1007 (`MAXJOBS`/`MAX_JOBS` spellings) and UX-1008 (a consumer with no
width promise); both still read `unknown_kind` here.

## Acceptance Test

`bga analyze --plane2` on the Graviton `11-serial-giant` auto capture
prints `giant.bst` as `drew` with peak 16 against `max-jobs` 8.

Amended (Decision): the Graviton capture is not kept, so the test runs
on a synthetic Plane 2 fixture (`giant.bst` peak 16 against `max-jobs`
8); the real reading is taken on CI's `bst-examples` `11-serial-giant`
auto run (giant at max-jobs 2 on a 4-core runner) when that artifact is
available.

## Outcome

Gap measured - `compute_jobserver_block` on the test's synthetic fixture
(`giant.bst` joined, peak 16, `max_jobs` 8), base `b8072cd7`:

```text
{"joined": "yes", "tokens_held_p50": null, "tokens_held_max": null}
```

`joined: yes` for the draw and the offer alike; `bga/report/text.py`
printed no jobserver row (0 matches for `compute_jobserver|Jobserver:`).

Close measured - the same call, this commit:

```text
{"joined": "yes", "peak_work_concurrency": 16, "max_jobs": 8, "verdict": "drew",
 "tokens_held_p50": null, "tokens_held_max": null, "admission_wait_us": null}
```

`_render_jobserver_section` on the same fixture:

```text
Jobserver:
  element                          joined       peak/max-jobs  verdict            tokens held admission wait
  giant.bst                        yes                   16/8  drew                         -              -
  admitted.bst                     yes                    1/8  offered, not drawn           -          2.50s
  level.bst                        yes                    8/8  offered, not drawn           -              -
  pinned.bst                       pinned                 3/1  pinned                       -              -
```

`pytest tests/unit/test_the_report_says_which_elements_drew.py`: 5 passed.
Touching selector (192 files, `-n 2`): 4320 passed, 50 skipped after
`docs/guides/cli.md` named the two new keys and the surface moved
584 -> 586 keys (3 red in `test_the_documents_keep_up_with_the_contracts.py`
before). No golden fixture carries a `jobserver` block; none moved.

| Mutation (`bga/correlate.py::jobserver_verdict`) | Reddened | Count |
|---|---|---|
| `return "drew"` for every joined element (verdict from `joined` alone) | `offered_not_drawn`, `admission_token_alone`, `terminal_prints_the_row` | 3 failed, 2 passed |
| `if joined not in ("yes", "pinned")` (pinned falls through to the peak test) | `pinned_never_drew_whatever_its_peak` | 1 failed, 4 passed |
| reverted from copy | - | 5 passed |
