# UX-1151: the Plane 2 sections do not lead with their answer

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings M8 | **Serves:** R2, R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_plane_2_sections_lead_with_their_answer.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §M8).

`#plane2_coverage` has 18 pairs and no lead sentence, "Processes 114" beside "Process count 114", and "Max concurrency 4" against `#utilisation`'s "Max observed concurrency 1". `#binary_cost` hides its one binary in a muted line, sorts by default on calls (every value 1) and has two columns labelled "Cpu". `#peak_memory` is a note with no figure. "Plane1"/"Plane2" beside "Plane 2".

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

Each Plane 2 section opens with its answer; binary_cost sorts by CPU and names its share column; one spelling of Plane 2.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: each Plane 2 section's first block is a sentence, and no section draws two pairs with the same value and near-identical labels, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Decision

- **Leads.** `render()` in `bga/viewer/sections.js` gives `plane2_coverage`, `binary_cost`, `peak_memory` and `element_join_coverage` a first block `p.section-answer`, one sentence read off published fields (a sum or max over a published column, as a chapter `answer()` already does). `peak_memory`'s figure is the largest `element_join[].peak_rss_bytes`.
- **Repeats.** `plane2_coverage` draws no `processes` pair when it equals `process_count` (which `test_no_key_is_terminal_only_in_silence.py` requires drawn); the lead states the one number.
- **Two concurrencies, two names.** They are two measures: `plane2_coverage.max_concurrency` is processes alive at once, `utilisation.max_observed_concurrency` tasks running together. Each property takes JSON Schema's own `title` annotation in `bga/schemas.py` ("Peak processes at once", "Peak tasks at once"), which `renderPairs` shows in place of the key; styleguide §1a says so.
- **binary_cost.** A column `statedOnce` removed as uniform offers no Top-N preset, so the opening bound ranks by the first varying quantity (`cpu_us`); `COLUMNS` titles `cpu_us` "CPU" and `cpu_share` "Share of CPU".
- **Spelling.** `title()` in `format.js` spells `plane1`/`plane2` "Plane 1"/"Plane 2" and `cpu` "CPU".
- **Guard.** `tests/unit/test_the_plane_2_sections_lead_with_their_answer.py`, booted on the two-plane page (`pages.two_plane_run`, `--layers 8 --width 14`), `golden` and `macro_micro`. **Mutations:** drop the lead; draw `processes` again; drop a schema `title`; offer presets over removed columns; drop the share column's title; drop the Plane spelling rule.

## Outcome

### Before

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_plane_2_sections_lead_with_their_answer.py -q
12 failed, 5 passed, 4 skipped
two_plane    plane2_coverage first block DL.pairs; Processes / Process count 114
             'Max concurrency' vs 'Max observed concurrency'
             binary_cost presets offered ['calls','cpu_us','cpu_share'], drawn ['element','cpu_us']
             heads ['Element','Cpu'], "Share of CPU" absent; spelling ['Cpu','Plane1','Plane2']
macro_micro  plane2_coverage first block DL.pairs; Processes / Process count 813
             heads ['Element','Binary','Calls','Cpu','Cpu']
golden       spelling ['Cpu','Plane2']
```

### After

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_plane_2_sections_lead_with_their_answer.py -q
17 passed, 4 skipped
plane2_coverage        Plane 2 saw 114 processes, at most 4 alive at once over 2.1 min; the files they opened were not recorded.
binary_cost            One binary, cc, ran in 114 elements: 114 calls, 66.0 s of CPU.
peak_memory            No single process exceeded 255.1 MiB; the largest ran in layer00/mod011.bst.
element_join_coverage  The two planes agree on all 114 elements.
labels                 Peak processes at once 4 · Peak tasks at once 1
```

The 71 test files naming the touched modules, single process: 1 failed, 1086 passed, 46 skipped; the one is the deviation below, re-run green after it.

### Mutations verified red and reverted (8)

| # | mutation | reddened |
|---|---|---|
| A1 | no `leadWith` call | sentence and repeat clauses, 4 failed |
| A2 | `processes` pair drawn again | repeat clause, 2 failed |
| A3 | drop one schema `title` | nothing: the two labels still differ — not a finding's shape |
| A3b | `renderPairs` ignores `title` | concurrency clause, 2 failed |
| A4 | presets over columns `statedOnce` removed | ranking clause, 1 failed |
| A5 | `cpu_share` untitled | share clause, 2 failed |
| A6 | no Plane spelling rule | spelling clause, 3 failed |
| A7 | no CPU spelling rule | spelling clause, 3 failed |

Deviation: `test_no_key_is_terminal_only_in_silence.py` requires `process_count` drawn, so the repeat drops `processes` rather than `process_count`. `docs/design/rendered-strings.json` re-written (`dev_rendered_strings.py --write`): `th` "CPU" and "Share of CPU" in, "Cpu" and the option "Top # by length" (a uniform column's preset) out. Size ledger: `bga/schemas.py` 6922 -> 6930 lines (`dev_sizes.py --adopt --force`). Not done, outside the Required Fix: "Schema plane2/v3 · Records embedded false" producer words (§4g.4).

Merged-tree fix: the guard's f-string skip reasons became module constants, declared in tests/conftest.py.
