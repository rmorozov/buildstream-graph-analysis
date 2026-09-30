# UX-1172: text residue after UX-1166

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-156 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer, bga/structural, bga/cli.py | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_key_path_stays_where_it_is_copied.py`

## Motivation

Page: the round-156 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `b58ffeb4`, Chromium 1440x900 and 390x844.

`bga/structural/serialization_points.py:89` writes " - variables: notparallel: True - " into the macro_micro `#serialization_point_risks` Hint (a raw YAML key and two spaced hyphens; the same shape sits in `bga/utilisation/envelope.py:183` and `bga/cache_effectiveness.py:387`). `bga/findings.py:1622` starts the "Work them in this order" detail with four spaces and "- the last of those leaves 68.8% ..." (the guard's regex wants a word before the hyphen). Copy finding buttons carry "->" in aria-label and title ("... 2.1 min -> 54.5 s"). `#document_shape` says "with [] for a list step" and no [] is on the page. The Perfetto question prose shows raw `**flows**` asterisks. `cli.py:168` prints "{x:.2f}s" with no space. Markdown copy carries unit-less microseconds ("| layer07/mod000.bst | 279000 |" where the table shows 279 ms). `#critical-path-drawn` chain names break inside the token ("layer03/mod" / "009.bst", `.path-name` `overflow-wrap: anywhere`).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

No spaced hyphen dash, raw YAML key, leading bullet, ASCII arrow or raw asterisk in reader text; names carry the arrow glyph; the "[]" clause is dropped; the CLI prints a spaced unit; Markdown copy carries a unit; a chain name breaks at its separators, not inside a token.

## Decision

Fix each string at its source: `bga/structural/serialization_points.py`, `bga/utilisation/envelope.py`, `bga/cache_effectiveness.py` lose the spaced hyphens and the raw YAML key; `bga/findings.py`'s horizon detail loses its bullet; `bga/viewer/questions.js` its `**`; `bga/schemas.py` the `[]` clause; `bga/cli.py` spaces its unit. A name built from a finding title goes through one `spoken()` in `bga/viewer/format.js` (`->` to `→`), used by `say` and the two `sections.js` names. `rowsMarkdown` suffixes a raw-unit column's title with its unit, e.g. "(µs)". `.path-name` gets a `<wbr>` after each `/`, so no CSS changes. Guard: `tests/unit/test_a_key_path_stays_where_it_is_copied.py`, which already boots the three pages at 1440 and 390, now also reads block text and accessible names for a spaced hyphen, a leading "- ", "->", "**", "[]" and a raw YAML key, and checks every wrapped chain name for a break inside a token. Two Node/Python tests hold the Markdown unit and the CLI's "1.50 s". Mutation: put back one string per class, and the guard goes red.

## Out of Scope

The schema descriptions `UX-1159` fixed; the JSON copy's field names.

## Acceptance Test

At 1440 and 390 on the three pages no reader text or accessible name holds a spaced hyphen, a leading "- ", "->", "**" or a bare key path, and `bga` prints "1.50 s". Guard: `test_a_reader_sees_labels_not_keys.py` extended to names and bullets. Mutation: restore one string, and the guard reds.

## Outcome

**Gap measured**: on the base (`83f10ca8`), every door open, the three pages at 1440 and 390, each block's whole `innerText` outside a copy surface plus every visible element's `aria-label` and `title`. Hits per class, summed over the two widths:

```text
                 spaced " - "  leading "- "  "->" in a name  "**"  "[]"
golden                0             2              4           2     7
macro_micro           2             2              4           2     7
two_plane             0             0              2           2     7
raw YAML key  macro_micro #serialization_point_risks "1 job - variables: notparallel: True - while"
cli.py:168    "{x:.2f}s"  ·  Markdown copy header "| Duration |" over raw µs cells
chain names   two_plane @1440: layer00/mod004.bst, layer01/mod005.bst, layer03/mod009.bst, ... wrap inside the token
```

The UX-1166 guard missed the serialization hint: it trims each text node, so a spaced hyphen before a `<code>` child is "job -" with no space after it.

**Close measured**: the same survey on this commit shows 0 in every class on all three pages at both widths. Of its 30 loose `\w+: \w+: ` hits, all are a control's name followed by a finding title with a colon ("Copy finding: Confidence: 87.5% (high)"). `_add_cpu_floor` now prints "1.50 s,", the Markdown header reads "| Duration (µs) |", and no `.path-name` wraps anywhere but after a `/`. Exported page, `tools.bga_view --export`: golden 322,704 -> 322,733 B (+29), macro_micro 383,696 -> 383,702 B (+6).

**Mutation table**: each mutation was reverted from a copy, `PYTHONDONTWRITEBYTECODE=1`, and the file then ran green (17 passed):

| mutation | reddened | the run printed |
|---|---|---|
| serialization hint back to "- {cause} -" | `test_no_block_or_name_holds_ascii_residue[macro_micro]` | 1 failed, 2 passed |
| horizon detail back to "    - the last" | `…ascii_residue[golden,macro_micro]` | 2 failed, 1 passed |
| `say` drops `spoken(of)` | `…ascii_residue[all three]` | 3 failed |
| `questions.js` "**flows**" restored | `…ascii_residue[all three]` | 3 failed |
| `deepest_path` "with `[]` for a list step" restored | `…ascii_residue[all three]` | 3 failed |
| `pathBox` without `<wbr>` | `test_a_chain_name_wraps_at_a_separator[two_plane]` | 1 failed, 2 passed |
| `rowsMarkdown` without the unit suffix | `test_markdown_copy_names_a_raw_unit` | 1 failed |
| `cli.py` back to "{x:.2f}s" | `test_the_cli_spaces_its_unit` | 1 failed |

The chain-name test asserts that two_plane at 390 wraps at least one name, so a page with no wraps cannot pass it vacuously.
