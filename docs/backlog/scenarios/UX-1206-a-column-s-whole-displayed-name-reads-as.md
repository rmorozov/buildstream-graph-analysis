# UX-1206: a column's whole displayed name reads as that column, and a clause not applied says the column is a share

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_key_column_matches_exactly.py` (`test_a_column_s_whole_displayed_name_reads_as_that_column`, `test_a_clause_not_applied_filters_nothing`, `test_a_bare_threshold_on_a_share_says_it_is_a_share`, `test_a_clause_s_stray_name_words_are_said_back`, `test_a_spaced_unit_is_one_value`, `test_a_spaced_unit_no_column_reads_is_quoted_whole`)

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Walk N9 (`UX-1195`): task table `wall-clock share > 2s` gives "none of 1,202 match" with no unread sentence, while `share > 2s` gives 3 rows. Elements `blast radius > 10min` gives "none of 1,202 match" AND "radius > 10min: no column here is called radius ..., so it is not applied" - not applied, yet nothing matches. Leaves view `is potentially deferrable:yes` gives "none of 150 match" (`deferrable:yes` gives 149). Guard passed: `test_a_key_column_matches_exactly.py` (single-word names only). Verifier A: on a payload without `task_durations_us`, the not-applied sentence does not say the column is a share.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A clause whose key is a column's whole displayed name, of any number of words, reads as that column; a clause reported not applied filters nothing; on a payload without durations the not-applied sentence names the column a share.

## Out of Scope

Single-word keys (`UX-1195`, closed); op on the elements table.

## Acceptance Test

The three quoted queries return 3, the blast-radius rows, and 149; the stripped payload's sentence says share; a case per query in `test_a_key_column_matches_exactly.py`. Mutation: restore the defect, and the guard reds.

## Decision

Round 160's architect (group A, track T-A), pasted. Two departures, measured on the real change: the two clause
passes became one `matchAll` over both clause kinds, so "the run of words since the last clause" is one cursor and
an exact clause's leftover words cannot leak into the threshold pass; and the share sentence does not say "try
> 10%" - the share column is declared `duration_us`, so `> 10%` is no threshold there (`parseThreshold` has no
`%` in `UNITS.duration_us`) - it says "name it, as in “wall-clock share > 2s”", the query that reads it.

```text
Route:     parseQuery reads a column's whole displayed name first: a pre-pass rewrites any multi-word name (title or th label, longest first, words joined by space/-/_) that stands before `:` or an operator into its slug; an unread named clause takes the run of words before it since the last clause, so nothing of it is left as substring text; `min` joins UNITS.duration_us; a bare threshold with no non-share quantity column returns `share: <key>` in its unread entry and the sentence says "<Wall-clock share> is a share, not a duration - try > 10%".
Rejected:  a multi-word name group in the two clause regexes (both grow the same alternation twice, and the residue bug stays); dropping the substring residue only when it is one word (`is potentially` is two).
Files:     bga/viewer/tables.js columnNames (return display phrases), parseQuery (pre-pass, residue into unread, share in unread), UNITS (min); bga/viewer/structured.js interrogable (the input listener's not-applied sentence, ~1008-1011); tests/unit/test_a_key_column_matches_exactly.py (_WALK_QUERIES + 3 clauses, stripped-payload fixture: walk report minus task_durations_us, exported).
Guard:     test_a_key_column_matches_exactly.py: "wall-clock share > 2s" matched == "share > 2s" matched (132 on the --runs 2 walk, not the task's 3; assert against the payload count); "blast radius > 10min" on a view whose head says Blast radius gives its >10 min rows, else is unread and the badge reads "25 of 1,202" (today "none of 1,202 match"); "is potentially deferrable:yes" == "deferrable:yes" on the Leaves view (149); stripped page's sentence contains "share".
Mutation:  drop the pre-pass -> wall-clock clause matched 0, red; return `lead` without the residue -> blast clause "none of 1,202 match", red; drop the share branch -> stripped sentence lacks "share", red.
Class:     product
Split:     one track, T-A first commit (UX-1214 follows in the same track: both write interrogable and the clause matcher).
Question:  none
```

Measured today (walk, `q.py`): "wall-clock share > 2s" none of 1,202; "share > 2s" 25 of 132 matched; "blast radius > 10min" none of 1,202 + "radius ... not applied"; "radius > 10m" 25 of 1,202. The elements table's heads on the walk carry no Blast radius column, so the Acceptance's "blast-radius rows" holds only on a view that draws one - the implementer reads which.
Budget: 0 at rest (the sentence mounts on typing). Code half +628 B.

## Outcome

The gap measured, at `ec816233`, the 1,202-element two-plane page (`pages.two_plane_run --layers 20 --width 60`,
`--runs 2`), Chromium 1440x900, badge / Copy / not-applied sentence (`q.py` in the track's scratch dir):

```text
wall-clock share > 2s  @tasks          none of 1,202 match | Copy 0 matched rows | -
share > 2s             @tasks          25 of 132 matched   | Copy 132 matched rows | -
blast radius > 10min   @elements       none of 1,202 match | "radius > 10min": no column here is called "radius" ...
is potentially deferrable:yes @Leaves  none of 150 match   | Copy 0 matched rows | -
deferrable:yes         @Leaves         25 of 149 matched   | Copy 149 matched rows | -
```

The close measured, same page and script:

```text
wall-clock share > 2s  @tasks          25 of 132 matched   | Copy 132 matched rows | -
blast radius > 10min   @elements       25 of 1,202         | "blast radius > 10min": no column here is called "blast radius" ...
is potentially deferrable:yes @Leaves  25 of 149 matched   | Copy 149 matched rows | -
> 2s on the payload without task_durations_us: "> 2s" is not applied: Wall-clock share is a share, not a
  duration - name it, as in "wall-clock share > 2s".
```

The quoted "3" is 132 here: the walk page is `--runs 2`; the guard asserts against the payload's count. No view of
the element table draws a Blast radius column, so the blast clause is said back and filters nothing (25 of 1,202,
the Top 25 bound). Page half on the walk run 156,769 -> 157,181 B (+412; the architect's prototype +628).
Volume at rest unmoved (the sentence mounts on typing): `test_the_page_has_a_volume_budget.py` green in the
174-passed run of the ten files naming the parser.

| mutation (`bga/viewer/tables.js`) | reddened | run printed |
|---|---|---|
| no whole-name pre-pass (`=> whole`) | `test_a_column_s_whole_displayed_name_reads_as_that_column` | 1 failed, 14 passed |
| an unread clause's words stay substring text | `test_a_clause_not_applied_filters_nothing` | 1 failed, 14 passed |
| no share branch (`share: null`) | `test_a_bare_threshold_on_a_share_says_it_is_a_share` | 1 failed, 14 passed |
| no `min` unit | `test_a_column_s_whole_displayed_name_reads_as_that_column` | 1 failed, 14 passed |
| reverted | | 15 passed |

Follow-up: `is a leaf:yes` read `leaf:yes` and left `is a` as row text - none of 1,202 match, no sentence. Words of
the clause's column's own name (a word no other column owns) before it are said back with it: `25 of 1,202` and "no
column here is called “is a leaf”"; `layer1 leaf:yes` still 79. `test_a_clause_s_stray_name_words_are_said_back`:
the said-back branch off, or any word taken as the column's, reds it (1 failed each). Page half +164 B.
Follow-up (walk findings P1, N7), same page, `test_a_key_column_matches_exactly.py`, badge / matched / sentence.
Gap (clause pattern's bound `\S*`, mutation run): `> 1 min` on the share-only payload said "“> 1” is not applied ...
as in “wall-clock share > 1”", the stray `min` a text filter. Close:

```text
elements "> 5 ms" = "> 5ms"     25 of 1,200 matched | wall-clock "> 2 s" = "> 2s"   25 of 1,000 matched
"> 0.05 min" = "> 3s"           25 of 851 matched   | binary_cost "cpu > 1 s" = "cpu > 1s"  25 of 39 matched
older payload "> 1 min"         "“> 1 min” is not applied: Wall-clock share is a share, not a duration ..."
```

| mutation (`bga/viewer/tables.js`) | reddened | run printed |
|---|---|---|
| bound is `\S*` again (no spaced unit) | `test_a_spaced_unit_is_one_value`, `test_a_spaced_unit_no_column_reads_is_quoted_whole` | 2 failed, 15 passed |
| reverted | | 17 passed |

Deviation: P1 ("> 60 s" returns 1,200 rows) is pre-existing, found by the round-160 walk on the round-159 export;
N7 (the share-only note quotes "> 1") is this round's, from UX-1206's `min` unit. The 1,202 walk page holds no
element over 60 s, so "> 60 s" reads none, equal to "> 60s".
