# UX-1193: the element preset and the latent-heavies section use one population or two names

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_one_name_one_population.py`

## Motivation

Finding: 12 of the review.

The preset "Latent heavies (1180)" is `observed_critical == false`, while the section "What is big and off the chain?" says "Nothing to report". Breaks §6e.2.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

One name, one population: the preset reads the section's population, or the two take different names.

## Decision

Class: product.

Architect (round 158, group C):

```text
Route:     the "Latent heavies" preset takes `from: "latent_heavies"` instead of `where observed_critical == false`, so its population is the section's by construction; an empty list drops the preset (`applyPreset` returns null).
Rejected:  rename the preset only - the preset's `question` is the section's title word for word, so two populations would still share one question; filter by duration floor in the page - a second membership rule beside `compute_latent_heavies` (Direction 7: presets filter published fields, never compute).
Files:     bga/schemas.py (`_ELEMENT_PRESETS`, the Latent heavies entry, ~1992-1996); tests/unit/test_one_name_one_population.py (new); tests/tiers.py (small, static).
Guard:     test_one_name_one_population.py - every preset whose `question` equals a section title in the schema's section-title map (schemas.py:5209) reads `from` that section's key (static, no browser).
Mutation:  restore `"where": {"column": "observed_critical", "equals": False}` in the preset; the guard reds.
Class:     product
Split:     one track, first in C1 (UX-1187 then writes the same list).
Question:  none
```

Budgets: bytes 0 (schema, not the page half); controls -1 or -2 on a run with no latent heavies (the preset's option and rail link go); height 0; words -3.
Overlap: writes `_ELEMENT_PRESETS` with UX-1187 - same track, 1193 first. UX-1184 (B) retitles columns from the declared field; if it edits preset column titles in schemas.py it must merge after C1.

Taken, with one change: the guard also reads the page. Chromium counts each preset option and its section's rows on `golden`, `macro_micro` and the 1,202-element run. A static check alone would pass on a `from` that resolves to another list, and it would not state the page's number.

## Out of Scope

What counts as latent-heavy.

## Acceptance Test

`tests/unit/test_one_name_one_population.py`: on the 1,202-element page, a preset and a section sharing a name count the same elements. Mutation: restore the preset's `observed_critical == false`; the guard reds.

## Outcome

### The gap, measured

```text
base 78d7be67, two_plane_run --layers 20 --width 60 (1,202 elements), Chromium 1440x900:
  preset option "Latent heavies (1180)"  (where observed_critical == false)
  section latent_heavies: 0 rows ("Nothing to report"; analyze json latent_heavies = [])
macro_micro: preset 1, section 1 (codegen.bst), equal by coincidence
```

### The close, measured

```text
"Latent heavies" reads from: latent_heavies (no sort; the list is published in its order)
1,202: preset not offered (applyPreset returns null on an empty selection), section 0
macro_micro 1 = 1, golden: pairs Critical path, Choke points, Latent heavies all equal
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_one_name_one_population.py -q
5 passed in 5.56s
volume, opened, 1440x900 (base -> after):
  xl_both  controls 886 -> 885, words 12,320 -> 12,318, nodes 6,847 -> 6,844, height 42,037 -> 42,037
  1,202    controls 902 -> 901; macro_micro, golden, heavy unmoved; page_bytes 144,202 unmoved
```

### Mutations verified red and reverted (1)

| # | mutation (bga/schemas.py) | reddened |
|---|---|---|
| M1 | restore `"where": {"column": "observed_critical", "equals": False}` | `test_a_named_section_is_what_its_preset_reads`, `test_a_preset_counts_what_its_section_publishes[1202]` (`('Latent heavies', 1180, 0)`), 2 failed |

Reverted from the saved copy: 5 passed.
