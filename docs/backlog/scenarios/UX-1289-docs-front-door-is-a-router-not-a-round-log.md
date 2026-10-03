# UX-1289: `docs/README.md` is a one-screen router by job, and the round log moves under `audits/`

**Priority:** High | **Status:** 🟢 Done | **Depends on:** none | **Found by:** the owner's docs audit request (2026-10-02, "stale or incomplete, or quite messy"); audit finding 3-4 | **Serves:** R1, R4, R5, R8 | **Topic:** docs | **Area:** unassigned | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_the_docs_index_is_a_router.py`; `tests/unit/test_the_round_history_names_every_audit.py` (retargeted at `docs/audits/README.md`)

## Motivation

`docs/README.md` (388 lines) is the front door, and about 60% of it is
a list of ~130 audit-round links (lines 195-330) plus five audits
filed as "case studies". The "commands to know first" (lines 24-42)
repeat README.md's quick start and `cli.md`, interleaved with UX ids.
The doc map is duplicated in `README.md:284-293`. A newcomer scrolls
past the round log before reaching anything they can act on.

## Required Fix

`docs/README.md` becomes one screen: an "I want to..." table by job
(try it, optimise a real project, run a pilot in CI, share a capture,
read the report, look up a command or a contract), each row one link.
The round list and the audit-only "case studies" move to
`docs/audits/README.md` (linking `round-register.md`, which already
derives the list). README.md's doc map links the router instead of
repeating it. Hand-typed contract counts in `docs/README.md:94-109`
are derived from `bga.contracts` by a guard or dropped.

## Out of Scope

Rewriting the guides themselves (UX-1290, UX-1291).

## Acceptance Test

`docs/README.md` ≤ 80 lines; every row links an existing file; no
round link left in it; the link guard green; `docs/audits/README.md`
holds every round link the old page held (a set comparison pasted).

## Outcome (2026-10-02) — 🟢 Done

**Premise:** held - 388 lines, 120 of the 135 audit links round links.

### The gap, measured

```text
$ wc -l docs/README.md                                    388
links into audits/ (resolved, one https)                  135   rounds 120 (incl. guard-census-round-64,
                                                                 planted-defect-walk-round-72)
README.md:282-293   a 5-row doc map beside docs/README.md's own
docs/README.md:94-109  "Twenty-eight", "last eighteen", "eleven", "other ten" - each
                       already held by a guard (test_every_emitted_contract_is_answerable.py x2,
                       test_a_counted_figure_is_derived.py x2) against bga.contracts
```

### After

```text
$ wc -l docs/README.md docs/audits/README.md docs/guides/json-contracts.md
   49 docs/README.md            18-row "I want to..." table, one link each, + the glossary
  159 docs/audits/README.md     named audits, the round run, the six audit case studies
   79 docs/guides/json-contracts.md   "What it emits" + "What it reads", moved verbatim
set comparison, old docs/README.md audits links vs docs/audits/README.md links (resolved):
  old 135, new holds 135, old-not-in-new []     round links left in the index: []
$ pytest tests/unit/test_the_docs_index_is_a_router.py + the 14 retargeted/doc guards
2 failed, 408 passed - both `guides/pilot.md`, the parallel track's file (kept, per the brief)
```

README.md's doc map is one sentence linking the router (343 -> 337 lines,
annotated). The four contract counts moved with their table; their
guards now read `json-contracts.md`.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| A1 | a link to `audits/round-3.md` appended to the index | `test_the_index_links_no_round`, 1 failed |
| A2 | the index padded to 82 lines | `test_the_index_is_one_screen`, 1 failed |
| A3 | the share-a-capture row gains a second link | `test_every_job_is_one_row_with_one_link`, 1 failed |
| A4 | the contract row repointed at `cli.md` | `test_every_job_is_one_row_with_one_link`, 1 failed |
| A5 | `round-150.md` dropped from `audits/README.md` | `test_every_round_document_is_linked_from_the_readme`, 1 failed |
| A6 | `sweep/v1` row dropped from `json-contracts.md` | count-matches-inventory + schema-reachable, 2 failed |

### Deviation from the Required Fix

The contract and input tables had to leave the index to fit 80 lines;
they went to `guides/json-contracts.md`, the page `UX-1290` names, kept
minimal (a 5-line header and the two sections verbatim) so `UX-1290`
appends `cli.md`'s chapter to it. The planes table and the
commands paragraph were dropped (README.md and `cli.md` hold both);
the subcommand names moved into the command row. Undeclared surfaces:
`.claude/agents/closer.md`, `.claude/skills/retro/SKILL.md` and the
fixing guide's close step 6 named `docs/README.md` as the round-link home.
