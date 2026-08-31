# UX-448: the element-scoped pivot has no finding to arrive from

**Priority:** Low | **Status:** 🟢 Done | **Found by:** round 70, scoping `UX-433` against `UX-368`'s rule | **Serves:** the reader who has picked an element and wants to know what it is made of | **Topic:** viewer

## Motivation

`UX-433` built the pivot — cpu, wall and peak RSS per **program**, on
the key `debug.exe` it added — and drafted two questions:

| question | scope |
|---|---|
| `cost-by-executable` | the whole build |
| `executables-in-element` | one sandbox |

The first shipped. The second did not, and the reason is `UX-368`'s
rule: *a question no finding points at is a question nobody arrives
at.* `bga/provenance.py`'s `TRACE_QUERIES` maps a claim to the query
that opens it; there are **22 claims and 20 already carry one**, and
neither spare (`cache-hit-ratio`, `confidence`) is about what an element
ran. `test_every_library_query_is_reachable_from_a_finding` is the
guard, and it is right.

So the query was dropped rather than added unreachable, and
`test_the_element_scoped_twin_is_not_in_the_library` holds it dropped
until this item.

`latent-heavies` is the closest claim — elements whose commands are
heavy though the element looks light — and it already points at
`element-commands`, which lists the *invocations*. The two are the same
reader question at two grains, which is the shape of the decision this
item has to make.

## Required Fix

Decide, and build one of:

- **A claim the element pivot answers**, if the report should make one —
  "this element's time is one program" is a real finding and the
  analyzer has the data (`plane2.by_binary`, published since `UX-370`).
  Then the question lands behind it.
- **Or a second query per claim**, if `latent-heavies` should offer both
  grains. That changes `TRACE_QUERIES`'s shape from one-to-one and the
  page's control with it, which is why it is a decision rather than a
  line.

Whichever: the SQL is written and measured — it is in `UX-433`'s
Outcome — so this item is the decision plus the wiring, not the query.

## Out of Scope

- **`debug.exe`** and the build-wide pivot: `UX-433`, closed.
- **Relaxing the reachability guard**: it caught this correctly, and a
  library of questions nobody can arrive at is exactly what `UX-368`
  built it to stop.

## Acceptance Test

The element-scoped pivot is in the library and
`test_every_library_query_is_reachable_from_a_finding` is green without
being weakened; `test_the_element_scoped_twin_is_not_in_the_library` is
deleted in the same commit, with its reason recorded here.

## Outcome (round 71, 2026-08-31) — 🟢 Done

### The decision, and the measurement that made it

The item offered two shapes. **The first was falsified rather than
weighed**, which is why this is the shorter half of the write-up.

*A claim the element pivot answers* — "this element's time is one
program" — is a real sentence and the analyzer has the data. Run
against every capture in the tree, the top program's share of an
element's measured CPU:

```console
$ python3 -c "
import json,glob
for p in sorted(glob.glob('**/plane2.json', recursive=True)):
    for el, v in (json.load(open(p)).get('binary_cost') or {}).items():
        r = (v or {}).get('by_cpu') or []
        if r: print(f'{el:16s} {r[0][\"binary\"]:10s} {r[0][\"cpu_share\"]:.3f}')"
app.bst          cc1plus    0.706
codegen.bst      cc1plus    0.888
core.bst         cc1plus    0.845
lib-a.bst        cc1plus    0.777
lib-b.bst        cc1plus    0.780
lib-c.bst        cc1plus    0.774
lib-d.bst        cc1plus    0.774
lib-e.bst        cc1plus    0.782
lib-f.bst        cc1plus    0.776
storm.bst        cat        1.000
```

**Ten elements of ten, 0.71 to 1.00.** Including `storm.bst`, which is
the process-storm example — the element built specifically to be the
*opposite* of a compiler. A finding that fires on every element in
every capture is not a finding, it is a fact about builds, and any
threshold that made it fire selectively would be a number chosen to
produce the answer. So the claim was not built.

That leaves the second shape: **a second query per claim**, and
`latent-heavies` is the claim that carries it.

### What that changed, and the shape it took

`TRACE_QUERIES` is `{claim: (query, ...)}` — a tuple **uniformly**,
including on the nineteen claims that read at one grain. A dict where
nineteen values are strings and one is a sequence is a shape the next
reader indexes wrongly; `queries_for()` is the accessor, and
`TRACE_QUERIES[claim][0]` is what the Investigate button opens.

Published as two keys, not one:

- `trace_query` — unchanged, the first, on every finding and record.
  Every existing consumer keeps reading exactly what it read.
- `trace_queries` — the whole list, **omitted where there is one**.
  On nineteen claims of twenty it would restate the field beside it,
  and its absence is the fact "this claim has one grain" (`UX-249`).

The page draws **one button and two pastes**, not two buttons. The
handoff opens one trace into one tab whichever question the reader
came with, so a second button would send the same trace twice; the
second *question* is the thing that actually differs. Measured on the
served page, which is the only place that can answer it:

```console
$ # bga view on tests/fixtures/with_timeline, read through Chromium
[{"query":"cost-by-executable","pastes":["cost-by-executable"]},
 ... seven more, one paste each ...
 {"query":"element-commands",
  "pastes":["element-commands","executables-in-element"]},
 {"query":"cpu-versus-wall","pastes":["cpu-versus-wall"]}]
console: []   csp: []
```

Ten investigate boxes, one paste each except the one claim that reads
at two grains. `UX-450` is why this was checked in a browser and not
in the export: the export flattens every module into one scope, so it
cannot tell a module move from a working page.

### The query, run at the grain it claims

`ROWS` in `test_the_build_pivots_by_program.py` gives `a.bst` two `cc`
invocations and one `ld`, which is what tells a pivot from a listing:

```console
$ python3 -m pytest tests/unit/test_the_build_pivots_by_program.py -q
10 passed in 1.42s
```

and on the real fixture, `app.bst` is **70 invocations against 5
programs** — the same collapse `cost-by-executable` makes build-wide,
one level down.

### What the export costs, split by measurement

Both committed bounds moved and the split was measured rather than
apportioned:

```text
                     page      golden data   macro_micro data
  before          286,739 B      101,520 B          156,885 B
  after           289,551 B      101,992 B          157,488 B
                   +2,812 B         +472 B             +603 B
```

The page half is the library entry, `queriesFor`/`investigationsFor`
and the paste loop. The +472 B both exports share is the two
`trace_queries` declarations in the embedded contract; the extra 131 B
on `macro_micro` is the published array itself. Golden has no
`latent-heavies` finding, and the two data figures differing by exactly
the payload is what says the split is measured. `PAGE_BUDGET_B` is
300,000 and is not touched; the two run bounds go to 394,000 and
450,000.

### Mutations verified red and reverted (8)

| # | mutation | reddened |
|---|---|---|
| P1 | `latent-heavies` back to one grain | `test_every_library_query_is_reachable_from_a_finding`, `test_a_finding_the_table_answers_carries_its_query` (2 failed, 36 passed) |
| P2 | the button appends only `pastes[0]` | `test_a_two_grain_claim_pastes_both_and_still_opens_one_tab` (1 failed, 20 passed) |
| P3 | a handoff per grain instead of a paste per grain | the same clause, on the `executables-in-element` handoff (1 failed, 20 passed) |
| P4 | `trace_queries` published on every claim, one-grain included | `test_the_mapping_reaches_the_finding_not_only_the_record[golden]` and `[macro_micro]` (2 failed, 26 passed) |
| P5 | the element pivot groups by the command line, not the program | `test_the_element_scoped_twin_answers_at_the_program_grain` — `'/usr/bin/cc -c f1.c' != '/usr/bin/cc'` (1 failed, 9 passed) |
| P6 | the pivot drops its `debug.element` filter | the same clause, plus `test_an_unfilled_query_shows_the_token` (2 failed, 18 passed) |
| N1 | the guide loses `executables-in-element` from its tables | `test_the_guide_sorts_every_question_the_library_serves`, `test_the_count_in_the_prose_is_the_count_in_the_tables` (2 failed, 8 passed) |
| N2 | the guide's prose count goes back to "thirteen" | `test_the_count_in_the_prose_is_the_count_in_the_tables` (1 failed, 9 passed) |

**Two mutations did not discriminate, and only one of them is a
finding.**

`P5` in its first form appended a column to `group by` and raised
`sqlite3.OperationalError: no such column: s.dur` — a red on the crash
and not on the claim, which is `UX-433`'s own lesson about a mutation
having to be the coherent change a round would actually make. Rewritten
as "group by the command line", it discriminates.

`N3` — scoping the pivot to `*bst-builder*` instead of
`*native-process*` — left `test_each_one_reads_something_only_the_trace_has`
green, and that guard is right: the query still reads `debug.exe` and
`debug.cpu_us`, which are per-process whatever category it globs, so it
still needs the trace. The mutation was not a defect. The coherent
version — rewriting the pivot as a Plane 1 sum over task slices — does
redden it.

### A document three rounds stale, and why nothing said so

`docs/guides/what-the-viewer-answers.md` claimed `bga view` "serves
thirteen questions" and sorted thirteen. The library served **fifteen**
before this item and sixteen after: `graph-levels` (`UX-380`),
`cost-by-executable` (`UX-433`) and now `executables-in-element` never
reached the guide.

The guard on that section read one direction only — every question the
guide *names* is in the library — with the list written as a literal
in the test file. So it could not see a question the library gained.
It now parses both tables out of the guide and asserts the union
against `QUESTIONS` in both directions, plus that the number written
in the prose is the number in the tables (`UX-326`: the tool's own
sentences are contracts, and a number in words is one).

### One guard corrected rather than tidied

`test_the_provenance_names_its_rule.py` reddened on `trace_queries[]`
reaching no rendered node. It is exempt on the same terms
`trace_query` already was, and the exemption is written out rather
than widened silently: a query id belongs beside the timeline, not
inside the reason for a claim, and the reader *does* get both grains —
on the Investigate button, which is what the browser measurement above
shows. `test_the_exemption_is_still_withheld` was extended to cover
both fields, so the second cannot start rendering under an exemption
written for the first.

### Deviation from the Required Fix

- **One.** The Acceptance Test asks for
  `test_the_element_scoped_twin_is_not_in_the_library` to be
  **deleted**. It was **replaced** rather than deleted, by
  `test_the_element_scoped_twin_answers_at_the_program_grain` on the
  same `ROWS`. Deleting it outright would have left the shipped SQL
  with no clause of its own in the file that owns the pivot; the
  absence guard's reason is recorded here and its assertion is gone,
  which is what the item was asking for.
- The first Required Fix bullet ("a claim the element pivot answers")
  was **not** built, on the measurement at the top of this Outcome.

### The suite

```console
$ make lint
All checks passed!

$ python3 tools/dev_js_deps.py --order bga/viewer
(acyclic)

$ make test
5469 passed, 28 skipped, 1 warning in 272.21s (0:04:32)
```

`tests/fixtures/with_timeline/analyze.json` was regenerated in the same
commit — it embeds the published record, so `latent-heavies` gained
`trace_queries` there and `document_shape` moved with it (983 -> 987
leaves). The golden snapshot did **not** move: it carries no
`latent-heavies` finding, which is the same reason its export data grew
by the contract alone.
