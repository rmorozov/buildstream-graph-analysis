# UX-938: an acceptance clause can name a reading that no environment in this project ever takes, and nothing says so until the round that owes it

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-762 | **Blocks:** — | **Found by:** round 137 — `UX-925`'s clause asked for every example figure to be re-derived, and the container that closed it has neither `bst` nor `bwrap`, so the clause could not have been paid by the session it was written for | **Serves:** every clause that asks for a reading, and every round that reports one unpaid | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** test_a_derived_figure_is_printed_not_committed.py · inferred r149

## Motivation

`CLAUDE.md`'s first convention is that every claim is a pasted
measurement. An Acceptance Test is where a row states which
measurement will settle it, and this repository is careful about the
*content* of those clauses. It says nothing about whether anyone can
take the reading.

`UX-925`'s clause read:

> The examples build and capture on the pinned toolchain, and every
> example figure the documents carry is re-derived with the deviation
> recorded, because a different compiler is a different program.

That is a good sentence and it was unpayable when it was written. A
session container has no `bst`, no `bwrap` and no `buildstream`
distribution at all — measured, not remembered:

```text
$ which bst bwrap buildstream        (no output, exit 1)
$ python -c "importlib.util.find_spec('buildstream')"   False
$ pip show buildstream               Package(s) not found
```

So the round closed with the clause named as a deviation and a
substitute reading in its place. That is the honest outcome and it is
not the defect. **The defect is that nothing in the repository knew**:
`dev_close_task.py --check` reads ten properties and none of them asks
whether a clause is takeable, so a clause naming an impossible reading
is indistinguishable from one naming a reading somebody simply has not
taken yet. The first reader to find out is the round that owes it,
which is the last moment it is cheap to change.

This is the shape the repository keeps filing from the other side.
`UX-914` was about a sysroot nobody declared; `UX-930` about a flag
whose failure was silent; fixing guide §5 is about an instrument that
reads a proxy for the thing it names. Here the instrument is the
clause itself, and its proxy is *plausibility*.

## Required Fix

Two halves, and the second is worth nothing without the first.

**The convention.** A clause names the environment whose reading
settles it, where that is not the development container — `runner`,
or a machine only the owner has (`UX-895`'s 16-core host is the
standing example). A clause that names an environment nobody in the
project has is filed as unpayable with the reason, rather than written
and discovered later. The vocabulary already exists in
`UX-571`'s exercised line, which names one version per environment.

**The retrieval.** Where the environment is the runner, the witness is
reachable and only its retrieval is awkward. The `bst-examples` job
already installs `bwrap` and the `bst` extras, runs
`examples/stage_runtimes.sh` and `examples/stage_cpp_toolchain.sh`,
and calls `bga doctor` — so the staged sysroot is real there and the
figures are derivable. What a session cannot do is read them
afterwards. Measured on this repository today:

```text
GET /repos/<o>/<r>/check-runs/<id>/annotations   200, annotation_level "notice"
artifact download, caches API, run-logs archive  403 through the proxy
jobs API log tail                                capped at 5,000 lines
```

So a short `::notice::` line under the step, emitted under `always()`
so a red step still reports, is the one channel that carries a figure
out of a job and back to a session. One line, naming the figure and
the fixture that produced it.

## Out of Scope

Paying `UX-925`'s own clause — that is the worked example, not the
subject, and it lands when the notice exists. Re-auditing every closed
row's Acceptance Test for takeability; the convention applies from
this row on, the way `UX-497` dated the Outcome cap. The BuildStream
version bump and the `always()` fix on the tier-gate step, which are
other threads' `ci.yml` work: if this row's step rides an already-open
`ci.yml` change it is its own commit citing this row, never folded
into another task's.

## Acceptance Test

`dev_close_task.py --check` gains a property: every open row's
Acceptance Test either takes its reading in the development container
or names the environment that does, and a row naming neither reds.

The notice is emitted by the `bst-examples` job and carries a figure
a session can read back:

```text
$ curl .../check-runs/<id>/annotations | jq '.[].message'
"examples/05: gcc 14.3.0 pinned, <N> elements, <T>s"
```

Three mutations, each applied, reddened, reverted:

- a new open row whose clause names a reading no environment takes —
  `--check` reds, naming the row. Today it reports 0 problems over 10
  properties with such a row present;
- the `::notice::` step's command replaced by one printing an empty
  string — the guard must red. **This is the mutation that matters:**
  a witness reporting nothing is this row's own defect one level
  down, and a guard that only asserts the annotation *exists* passes
  it;
- `if: always()` removed from the step — a job that reds before the
  step still has to report, or the notice is only ever a witness for
  the runs that needed no witness.

The first mutation is the one that discriminates against the cheap
fix: a convention written only in `CLAUDE.md`, with no property
reading it, passes every sentence above and changes nothing.

## Decision

The `architect`, round 149, at `c324f250`.

```text
Route:     the convention half: a header field `**Reading:** container | runner:<ci job> |
           owner:<machine> | unpayable:<reason>` and a ninth --check property, reading_problems():
           an open row at UX-938 or later with no field, a `runner:<job>` not under ci.yml `jobs:`,
           or `unpayable:` with no reason reds. The retrieval half is paid already: bst-examples'
           "UX-941 structural figures as notices" step runs `if: always()`; no ci.yml change
Rejected:  the convention in prose only - nothing reads it, the row's own mutation
           scanning Acceptance text for bst/bwrap/runner - a plausibility proxy
           a new ::notice:: step - duplicates UX-941's
           a grandfather set - a committed list; backfill the headers instead
Files:     tools/dev_close_task.py; docs/contributing/rules.md (one row); the header of each open
           row at UX-938 or later; tests/unit/test_a_clause_names_where_its_reading_is_taken.py (new)
Guard:     the new file on a tmp --scenarios copy: a planted open row with no Reading reds naming
           its id; runner:no-such-job reds; unpayable: with no reason reds; a row below UX-938
           passes; the real tree reports 0
Mutation:  reading_problems returns [] -> planted row reds; drop the jobs lookup -> no-such-job
           reds. Mutations 2 and 3 (empty notice, always() removed) redden
           test_the_examples_clock_is_a_spread.py::TestTheNoticeStep; apply once, paste the red
Class:     bookkeeping (cap lifted for r149)
Split:     one track, parallel with UX-1041
Question:  none
```

## Outcome (round 149) — 🟢 Done

**Premise:** held — `--check` read eight properties and none asked
whether a clause's reading was takeable; an unpayable clause and a
paid one were indistinguishable.

### The gap, measured

```text
$ python3 tools/dev_close_task.py --check
  ...
0 problem(s) over 8 propert(y/ies), 1023 backlog row(s)
```

A planted open row naming a reading no environment takes passed clean.

### After

```text
$ python3 tools/dev_close_task.py --check
  ok    every open row at UX-938 or later names where its Acceptance
        Test's reading is taken
0 problem(s) over 9 propert(y/ies), 1023 backlog row(s)
```

`reading_problems()` is the ninth property. Every open row at UX-938 or
later got a `**Reading:**` header field (22 rows; `UX-1010`/`UX-1014`
`owner:CodSpeed Graviton` (`UX-1014`: and an x86 16-core host), `UX-975`/`UX-1013` `runner:bst-examples`,
the rest `container`). The retrieval half was already paid by
`UX-941`'s `if: always()` notice step - no `ci.yml` change here.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| A1 | `reading_problems` returns `[]` early | 3 planted clauses (no field, bad runner, empty unpayable) |
| A2 | the `runner:` job-membership check replaced with `if False:` | the bad-runner clause only |

### Deviation from the Required Fix

`rules.md`'s new row pushed the card to 81 lines against `UX-497`'s
80-line cap; the floating sentence below the proxy-rule row duplicated
`fixing-guide.md` §5 verbatim, so it was dropped rather than the new
row. `ci_jobs()` reads a fixed `CI_YML` path rather than the
monkeypatchable `REPO`, since `UX-935`'s synthetic-repo test has no
`.github` of its own. `test_a_derived_figure_is_printed_not_committed.py`'s UX-9801-9805
fixture rows gained `**Reading:** container`, or the new property broke
that item's own green `--check`.

```text
$ make lint          exit 0
$ python3 tools/dev_close_task.py --check   0 problem(s) over 9 propert(y/ies)
$ python3 tools/dev_sizes.py --check        sizes ok: 151 file(s) measured
```
