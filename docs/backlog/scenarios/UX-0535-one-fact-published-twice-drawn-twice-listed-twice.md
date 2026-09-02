# UX-535: one fact published twice, drawn twice, listed twice

**Priority:** Medium | **Status:** 🟡 In Progress | **Depends on:** UX-288 (the one-population rule), UX-285 (the grouping that moved without merging) | **Serves:** anyone reading the run's identity, or the rail | **Topic:** viewer

## Motivation

The duplication census over the cold export (35 tables, 338 distinct
text blocks, 12.8 % repeated characters — under §5a's 21 %) found
the repeats that are not citations:

```text
run_instance.producer == producer         True   (analyzer.py:160-162, schemas.py:2494)
rail "Producer"                            2 entries, 2 hrefs
rail "Latent heavies"                      2 entries — a section, and an `elements` preset
graph_summary vs graph_metrics             3 facts, the same sentence, both sections
```

`UX-390` is verified closed (`attribution_hints` has no section).
These three are the remainder: a payload key published under two
paths, and a rail that lists a section and a preset under one label.

## Required Fix

`producer` is published once (`run_instance.producer` stays, the
top-level copy goes — a removal, so the analyze contract bumps under
`UX-190`); `graph_summary`'s three shared facts render in one of the
two sections; rail labels are unique — a preset entry says "preset"
or carries the count.

## Out of Scope

- Selections drawn both as a section and as an `elements` preset —
  `UX-289`/`UX-338`'s design; only the rail label collides.

## Acceptance Test

Payload-level duplicate scan (the census's method) finds zero exact
duplicates; rail labels unique. Mutation: republish `producer` —
the contract guard reds.

## Outcome (round 80, 2026-09-02) — 🟡 one of three, and the other two are a decision

### The gap, measured

The rail's labels off the rendered page, both committed fixtures:

```text
fixture       rail entries   labels on more than one href
golden                  59   Latent heavies  #latent_heavies
                             Latent heavies  #elements~v.elements=Latent%20heavies
macro_micro             83   the same one
```

The payload half, on `golden` + `producer.add` on its run-context —
what a real capture writes — scanning for one object under two paths:

```text
exact duplicate objects: 3
   350 chars  ['run_instance.producer', 'producer']
   140 chars  ['elements.blast_radius.{extra,app}.bst']
   118 chars  ['elements.criticality_probability.{base,lib,app}.bst']
```

Only the first is one *fact* twice; the other two are equal values for
different elements, which is data. And the two graph sections, read off
the page — three facts, same value **and same sentence**, in both:

```text
fact                graph_summary            graph_metrics          value
element count       "Total elements?"        "Num elements?"            4
critical path len   "Critical path length?"  "Critical path length?"    3
max parallelism     "Max parallelism?"       "Max parallelism?"         2
```

### After

`viewEntries` labels a preset entry with the option's own text, which
already carries the count: `Latent heavies (1)` against the section's
`Latent heavies`. Zero collisions of 59 and 83 entries.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| P1 | `link.textContent = name` — the bare name restored | `…no_label_points_two_ways`, 2 (both fixtures) |
| P2 | the drive reports `entries: 0` | `…rail_was_actually_read`, 2 — so an empty rail cannot pass P1's clause |

### Deviation from the Required Fix — two thirds not done, and why

**`producer`: the Required Fix names the wrong copy, measured.** It says
the top-level copy goes and `run_instance.producer` stays. But
`run_instance.producer` is read by **nothing** (`grep -rn` over `bga/`,
`tools/`, `tests/`, `*.js`) and is **absent from both committed
fixtures** — neither run-context carries a stamp. The top-level copy is
read by four: `bga compare`'s contract-movement refusal
(`data["producer"]["contracts"]`), `store_aggregate`, `ingest/loader`
and the page's rail and chapter. Removing it as written takes the
contract refusal with it and breaks `ANALYZE_FULL_KEYS`' "present on
every full report". The dedup that costs nothing is the reverse one —
which also removes the *rail's* second "Producer" entry, that entry
being `run_instance.producer` rendering.

Either direction is a removal, so either bumps `analyze/v4` → `v5`:
**121 references** across `docs/guides/cli.md` (11), `bga/schemas.py`
(7), the spec's Part 32 registry (4), `architecture.md` (4), ~15 guards
and two committed fixture payloads. That is a contract decision and a
merge-wide edit, not a track's call, so it is left with the measurement
rather than done in the direction the file names.

**`graph_summary`: which section keeps the fact is the same kind of
decision** — and `Total elements?` / `Num elements?` are one fact under
two labels, so "render in one of the two" must also pick the label.
Left open. Neither is blocked on work, only on a choice.

```text
make test-touching  →  300 passed, 2 skipped in 170.80s
pytest tests/unit/test_the_rail_takes_a_step.py  →  12 passed in 19.64s
make lint           →  All checks passed!
```
