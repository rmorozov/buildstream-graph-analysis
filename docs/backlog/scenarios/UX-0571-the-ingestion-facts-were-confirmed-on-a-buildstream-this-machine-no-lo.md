# UX-571: the ingestion facts were confirmed on a BuildStream this machine no longer has

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-88 (the last correction to this document) | **Serves:** whoever meets a `bst` output line the parser does not | **Topic:** docs

## Motivation

`docs/spec/ingestion-pipeline.md` is a 2026-08-14 log of "empirically
confirmed facts against real `bst` 2.7.0" — thirteen mentions of
that version. This machine runs 2.8.0 (`bst --version`), the
extract guard gates on `which bst` and passed here, and no document
records that the facts were exercised on 2.8.0 at all. Two facts are
also wrong on their own terms:

```text
F9   "%{kind} … not read by any analysis consumer yet"
     grep -rl element_kind bga/ → analyzer.py blast.py findings.py floors/cold.py cache_effectiveness.py sources.py
F11  "Query cache … currently dropped entirely"
     the document's own §546: "P4-14 is done … Pipeline Overhead block"; test_pipeline_overhead.py exists
```

Eighteen test files cite this document as provenance; none reads it.

## Required Fix

The version the facts were last exercised against comes from the
guard, not the prose: `test_bst_extract_run.py` prints the `bst`
version it ran under and the document's header cites "last exercised
on" that output, dated. F9 and F11 corrected in place, the way `UX-88`
corrected F5 (the old sentence kept, one line naming what changed).

## Out of Scope

- Re-deriving every fact on 2.8.0 by hand — the extract guards are
  the derivation; the item records which version they ran under.

## Acceptance Test

The header carries the version and date the guard printed; mutation:
restore "not read by any analysis consumer" — a grep-backed clause
(the six consumers, derived) reds.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Premise:** falsified — this machine has `bst` 2.7.0, not the 2.8.0 the
Motivation asserts, so the facts were never confirmed on a BuildStream
that is gone; they were confirmed on the one still here, and had simply
never been re-run.

```text
$ which bst && python3 -c "import subprocess;print(subprocess.run(['bst','--version'],capture_output=True,text=True).stdout.strip())"
/usr/local/bin/bst
2.7.0
$ python3 -m pytest tests/unit/test_bst_extract_run.py -q -k real_end_to_end
1 passed, 21 deselected in 1.49s
```

Second premise falsified: the Motivation's `grep -rl element_kind bga/`
lists `floors/cold.py`, which is a **false positive** — its match is
`by_element_kind_phase`, a pool keyed on `span.task_key.task_kind`, not
on `Element.element_kind`. It is not a consumer. The six fact 9 names
are `analyzer.py`, `blast.py`, `cache_effectiveness.py`, `findings.py`,
`sources.py`, `structural/consolidation.py`; the guard's read pattern
rejects `by_element_kind_phase` by word boundary, which is what M4
proves.

The version is the guard's now: `test_bst_extract_run.py::bst_version()`
shells `bst --version`, and both facts headings carry **Last exercised
on `bst` 2.7.0, 2026-09-03**. Facts 9 and 11 keep their old claim as a
quotation and name what superseded it, `UX-88`'s shape for fact 5.

**Acceptance Test**

```text
$ python3 -m pytest tests/unit/test_the_ingestion_facts_name_the_bst_they_ran_on.py -q
8 passed in 0.58s
$ grep -n 'Last exercised on' docs/spec/ingestion-pipeline.md
99:**Last exercised on `bst` 2.7.0, 2026-09-03.** That version is read from
196:**Last exercised on `bst` 2.7.0, 2026-09-03.** That version is read from
$ python3 -m pytest tests/ -m bst -q
37 passed, 10 skipped, 6399 deselected in 89.38s
```

**Mutations verified red and reverted (9):**

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | drop one heading's `Last exercised on` line | `..._headings_say_which_bst...` — "2 facts headings, 1 'Last exercised on' lines" | 1 failed, 7 deselected |
| M2 | doc says 2.8.0, binary says 2.7.0 | `..._documented_version_is_the_one_the_binary_reports` | 1 failed, 7 deselected |
| M3 | fact 9 restores "not read by any analysis consumer" unquoted | `..._fact_9_no_longer_claims_element_kind_is_unread` | 1 failed, 7 deselected |
| M3b | fact 9 drops "stopped being true" | `..._fact_9_names_what_superseded_its_old_claim` | 1 failed, 7 deselected |
| M4 | fact 9 names `bga/floors/cold.py` | `..._every_module_fact_9_names_really_reads_element_kind` | 1 failed, 7 deselected |
| M5 | fact 11 restores "dropped by the ingestion pipeline entirely" unquoted | `..._fact_11_no_longer_claims_query_cache_is_dropped_entirely` | 1 failed, 7 deselected |
| M5b | fact 11 drops "stopped being true" | `..._fact_11_names_what_superseded_its_old_claim` | 1 failed, 7 deselected |
| M6 | fact 11 names a guard file that does not exist | `..._fact_11_names_the_pipeline_overhead_that_replaced_it` | 1 failed, 7 deselected |
| M7 | `bst_version()` returns None instead of reading the binary | `..._the_bst_version_these_facts_ran_under_is_printed` | 1 failed, 22 deselected |

**A guard that did not discriminate.** The first fact-9 and fact-11
guards asserted the phrase's absence *and* "stopped being true" in one
test, so the acceptance mutation reddened them on the wrong clause.
Split into M3/M3b and M5/M5b: each mutation now reddens one claim.

**Deviation.** `.github/workflows/ci.yml` is a surface the Decomposition
did not declare: two new `@pytest.mark.bst` tests move the pinned tier
count, and `test_docs_links_and_commands.py::test_the_pinned_bst_tier_count...`
fails until both the `grep` and the `echo` copies move 45 → 47. Verified
against a real run (37 passed + 10 non-bst skips = 47).

**Committed with `BGA_SKIP_SELECTOR=1`** (`UX-561`'s documented escape).
`make test-touching` is red on two guards that are red at the base
`c6ccb6b` too and that this track may not touch:
`test_every_declared_skip_reason_is_known` (`UX-588` left
`'the floor has moved to 3.10; PEP 604 is allowed'` undeclared) and
`test_every_table_row_has_its_header_cell_count`
(`docs/backlog/scenarios/README.md:11`, a merge hotspot). Everything
else is green: 1,025 passed, 9 skipped.

**Not done.** The skip reason does not name the version it could not
check: a new reason string fails `conftest.KNOWN_SKIP_REASONS` on a
bst-less runner, so it reuses the declared literal, which points at the
document where the version and date now live. `bst` was present here,
so the branch never fired.
