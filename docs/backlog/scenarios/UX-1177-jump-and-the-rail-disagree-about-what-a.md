# UX-1177: Jump and the rail disagree about what a level fold and a preset are, after UX-1173

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-157 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_jump_finds_what_the_rail_lists.py`

## Motivation

Page: the round-157 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `73af3af3`, Chromium 1440x900 and 390x844.

Jump says `Nothing matches` for "level 3", "Level", "critical", "Critical path" and "leaves" while the rail lists "Elements · Level 3", "Critical path (10)" and "Leaves (13)"; "wide" and "mod008" hit. A rail press on "Elements · Level 3" lands (hash `#parallelism--elements-level-3`, top 60 px at 1440, 80 px at 390) with `details.open` false, and the reader sees "Elements · 1 level, 14 rows", identical on all 8 level folds (12 of 27 fold ids are in the rail and all land closed; `resource_blast--blast-elements` with 90 rows and the run_instance folds too). The fold's select is named "Rows shown: Levels 1 Elements" (to Levels 8) and, in `resource_blast`, "Rows shown: Rows Direct elements". Typing a partial uid that matches several elements into the Ask box changes nothing.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Jump finds every rail entry it lists, including level folds and element presets; a rail press on a fold opens it; a level fold names its level; the select's name reads as a phrase; a partial uid matching several elements says how many it matched.

## Decision

The row takes the conflict between `UX-1025` (a fold's label names its content and count, and a fold inside a labelled cell adds nothing) and a level in the fold's own summary: the summary carries the level ("Elements · Level 3, 14 rows"), so a fold read alone (rail, accessibility tree, Jump) says which level it is, and the cell beside it repeats the level on purpose. `UX-1025`'s guard and `UX-1163`'s said-once rule are amended by one sentence each: a name that stands alone in the rail or the tree may repeat its cell's label.

The round-158 architect's route (arch158/C.md), pasted:

```text
Route:     `jumpTargets` adds every rail entry the rail lists (level folds, element presets) from the same label authority as the rail (`sectionLabel`/`subsections`); a fold's anchor reveal opens the `details`; `mapTable` passes the parent row's key into `folded`'s label, so a level fold reads "Elements · Level 3, 14 rows" (the recorded Decision, with the UX-1025/UX-1163 sentences amended); the Top-N select's name is built as a phrase from the table's name; a partial uid in Ask that matches several says "N elements match".
Rejected:  a second index for Jump - two lists that drift (UX-648 made the rail the one label authority); relabel the rail to match Jump - hides the folds a reader can reach.
Files:     bga/viewer/nav.js (`jumpTargets`, `subsections`/`viewEntries` if they need to export the fold entries); bga/viewer/chapters.js (`revealAndLand`: open the target `details`); bga/viewer/structured.js (`mapTable` -> `folded` label; `interrogable` select `aria-label` ~965); bga/viewer/questions.js (`elementPicker` partial-uid count); docs/design/styleguide.md (UX-1025's and UX-1163's one sentence each); tests/unit/test_jump_finds_what_the_rail_lists.py (new); the UX-1025/UX-1163 guards, one clause each; tests/tiers.py.
Guard:     test_jump_finds_what_the_rail_lists.py - on the two-plane page every rail entry text is a Jump hit ("level 3", "critical", "leaves"); a rail press on a level fold leaves `details.open` true; the 8 level folds read 8 distinct summaries; the select reads "Rows shown: Level 1 elements"; a partial uid shared by several elements shows its count.
Mutation:  drop the fold entries from `jumpTargets`; the guard reds.
Class:     product
Split:     C6, second, after UX-1176 in the same worktree.
Question:  none
```

Taken in the track: Jump reads the rail's own sub-entry links (the rail
is the label authority, so a hit is the entry's text and pressing it
presses the entry); the row goes into the fold's `.map-name` in
`buildTable`, where the row's first cell and its header are at hand,
the way `nav.js`'s `rowOf` already names the rail entry. The summary
keeps `UX-318`'s depth sentence after the name, so it reads
"Elements · Level 3 · 1 level, 14 rows" rather than the Decision's
"Elements · Level 3, 14 rows": §6e.13 asks a nested fold for its depth.
The `UX-1025`/`UX-1163` amendments are the two styleguide sentences;
the clause lives in this row's guard, on the two-plane page whose eight
level folds are the case. Only a name two rows' folds share takes the
row, as `rowOf` already decided: a unique fold keeps its name and its
id (Out of Scope), measured on macro_micro's `restructuring--edges`.

## Out of Scope

The level numbering `UX-1173` fixed; the fold ids.

## Acceptance Test

On the two-plane page Jump finds "level 3", "critical" and "leaves"; a rail press on a level fold leaves it open; the 8 level folds read 8 different summaries; the select's name is "Rows shown: Level 1 elements"; a partial uid shared by several elements shows a count. Mutation: restore one defect, and the guard reds.

## Outcome

**The gap, measured.** The guard against `e4373afe` (`UX-1176`, before this change): `6 failed in 2.63s`. Two-plane page (114 elements) at 1440:

```text
rail entries not a Jump hit     'What should I run next?', 'Direct elements', 'Blast elements', 'All elements (114)', 'Critical path (10)', 'Leaves (13)', ...
typed                           {'level 3': [], 'critical': [], 'leaves': []}
rail press on Elements · Level 3   details.open False
level fold summaries            8 x 'Elements · 1 level, 14 rows'  (1 distinct)
select name                     'Rows shown: Levels 1 Elements'
Ask "mod00"                     the resting note, unchanged
```

**The close, measured.** `PYTEST_XDIST= python3 -m pytest tests/unit/test_jump_finds_what_the_rail_lists.py -q`: `6 passed`. Every rail sub-entry and preset is a hit under its own text; "level 3" finds "Elements · Level 3"; the fold opens on a rail press; the summaries read `Elements · Level 1 · 1 level, 14 rows` … `Level 8`; the select reads "Rows shown: Level 1 elements" (and "Rows direct elements", "Run instance producer contracts"); "mod00" reads `80 elements match "mod00"; the box offers the first 8, and the queries still ask about layer00/mod002.bst.`. Fold ids unmoved: `test_a_rail_click_lands_on_its_section.py` still measures `restructuring--edges`/`--projection`. Volume guard reading, `UX-1176` → this: macro_micro unmoved (38,307 px, 13,068 words, 792 controls, 6,815 nodes); xl_both words 12,701 → 12,761 (the twenty level folds' "· Level N"), height 43,933, controls 1,007, nodes 7,488 unmoved. Page half (macro_micro) 149,066 → 149,606 B (+540).

| mutation | reddened | run |
|---|---|---|
| M1 rail entries left out of `jumpTargets` | every rail entry a hit; typed words | 2 failed, 4 passed |
| M2 `revealAndLand` opens no `details` | a rail press opens the fold | 1 failed, 5 passed |
| M3 no fold takes its row (`> 1e9`) | each level fold names its level | 1 failed, 5 passed |
| M4 select name back to titled parts | the select reads as a phrase | 1 failed, 5 passed |
| M5 no partial count (`hits > 1e9`) | a partial uid says how many | 1 failed, 5 passed |
| reverted | — | 6 passed |
| M6 (round-158 residue) Jump's `revealAndLand(node, "smooth")` back | a jump lands on its target | 1 failed, 6 passed |
| M7 `revealAndLand` lands once, no re-land after `content-visibility` renders | a jump lands on its target | 1 failed, 6 passed |
| M8 no filter-in for a binary past the bound | a jump lands on its target | 1 failed, 6 passed |
| M9 the `[data-binary]` scroll margin deleted | a jump lands on its target (row under the header, top 0) | 1 failed, 6 passed |

Re-based: none. Styleguide: §3d's `UX-1163` item and §6e.13's row gain one sentence each, the row naming both guard files.

**Residue (round 158, walk N9).** Jump landed off target: a smooth scroll, one landing against `content-visibility`'s estimate, and the first `[data-binary]` node whether mounted or not. The guard against `474f4eb3` (`UX-1179`'s card landing in): `1 failed, 6 passed`, `binary_cost`'s last mounted row `constant-340` at top -743 against a 60 px margin on the heavy-binary page. Now the landing is instant and lands again until the node holds its margin (at most 4 times), a binary past the bound is filtered in (`binary:<name>`), and a binary row takes the anchors' scroll margin. The new clause presses an element, a mounted binary and an unmounted one on `pages.heavy_binary_run`, each from rest, and reads the landed top against the section's scroll margin: `7 passed in 10.16s`. On the 1,202-element pages: `layer16/mod006` 60, `layer12/mod058` 59, heavy `lognormal-308` 60, `lognormal-003` (unmounted) 60.
