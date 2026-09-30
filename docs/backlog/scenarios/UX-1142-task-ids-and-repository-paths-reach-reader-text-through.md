# UX-1142: task ids and repository paths reach reader text through descriptions and notes

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings H3 | **Serves:** R1, R8 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_reader_never_sees_the_register.py` (widened)

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §H3).

13 visible nodes carry `UX-NNN`: 7 Perfetto question notes ("`UX-310`'s counter track"), `#provenance` ("UX-683's discovery half"), the capacity recommendation's Cores busy description ("(`UX-861`; see `clamped_from`)"), `#peak_memory`, and `#plane2_coverage`'s disclaimer naming `docs/backlog/scenarios/UX-0011-...md`. UX-824's guard does not read descriptions or notes.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Decision

- Strip the ids and paths where the strings are written: the Perfetto question notes (`bga/viewer/questions.js`), the provenance sentences (`bga/provenance.py`), every schema `description` in `bga/schemas.py`, the Plane 2 report notes and the static-binary disclaimer the tracer writes (`tools/bst_native_build_tracer.py`) and the committed `macro_micro/plane2.json` copies of those notes. Terminal-only text (CLI help, the text report) is not reader text on the page and is left.
- Guard: `UX-824`'s `tests/unit/test_a_reader_never_sees_the_register.py` widens its opener to every `?` door clicked, every `details` open and every folded chapter/section lifted, and adds the two-plane 8x14 page; item 1 reads every visible text node for `UX-\d+` and `docs/`. A second, static clause walks every schema `description` for the same two patterns.
- Mutation: restore one question note's `UX-310` (page clause reds), restore one schema description's `UX-861` (static clause reds).

## Required Fix

Producer strings drop task ids and repository paths; the UX-824 guard reads every visible text node with every `?` door open.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: zero `UX-\d+` and zero `docs/` substrings in visible text with every door open, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome

### The gap, measured

Every door open (`tests.pages.OPEN_EVERY_DOOR_JS`), visible text nodes
holding `UX-\d+` or `docs/`, at 1440x900; and every `description` in
`schemas.schema(name)` for all 11 documents:

```text
two-plane 8x14 (114 el)  15 nodes  7 Perfetto notes, 2 provenance, capacity Cores busy,
                                   element_join_coverage, cpu_time x2, peak_memory, disclaimer
golden                    8 nodes
macro_micro              15 nodes
schema descriptions      36 of them name a task id or `docs/`
```

The old guard read `innerText` with fewer doors open and saw 0 on
golden and scale.

### The close, measured

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_reader_never_sees_the_register.py -q
18 passed in 6.27s
```

Same probe after: 0 / 0 / 0 nodes; 0 schema descriptions.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| B1 | a Perfetto note says "`UX-310`'s counter track" again, and one schema description "`UX-861`: the CPU figure" | item 1 on golden, scale, two-plane (innerText and visible-node clauses) and `test_no_schema_description_names_a_task_or_a_path`, 6 failed |
| B2 | the tracer's disclaimer names `docs/backlog/scenarios/UX-0011.md` again | `test_item_1_on_the_two_plane_page`, 1 failed |

Re-based: `test_native_cpu_time.py`, `test_the_monolith_retires.py` and
`test_builders_and_pool_are_recommended_from_a_capture.py` assert the
notes' new wording
(e.g. "predates CPU accounting", was "before UX-45"). The committed
`macro_micro/plane2.json` notes are edited by hand to the tracer's new
strings (a real capture cannot be regenerated); the two committed
analyses by `tools/dev_refresh_analysis.py --write`. The two-plane page
runs item 1 only: items 4 and the synonym clause red there on text
other rows own (a `Schema plane2/v3` cell; "build" in 4 headings).

