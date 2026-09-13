# UX-828: the header spends 14% of the viewport on a filesystem path

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-668 (the picker in the identity line), UX-285 (identity is reference) | **Found by:** round 115, the design review | **Serves:** every reader, on every load | **Topic:** viewer | **Area:** bga-viewer | **Shape:** bounded

## Motivation

Measured at 1440×900 on both pages this round:

```text
header        128.5 px, position: sticky, pinned after scrollTo(0, 2000)   = 14.3% of 900
line 2        the run's absolute path, 149 chars, wrapping to two lines
contents      title · path · "measured by bga 0.4.1 — analysed here by bga 0.4.1" · the picker
not in it     run navigation and the Perfetto handoff (both in the rail); a footer exists with two links
```

The picker is the one control the header holds that a reader uses
(§4 rule 7); the path is `run_instance`'s fact, drawn first and
largest.

## Required Fix

§3i (landed this round), in `bga/viewer/app.js` and `tools/bga_view.py`: the header is at most 72 px sticky, holds a
wordmark on the left, the run's alias and start instant, and the picker
centred; the path moves to `run_instance` (`UX-285`'s reference chapter)
and onto the title's `title` attribute; the version line joins the
footer. Run navigation and the handoff stay in the rail as
disclosures — collapsed is their resting state (§6d).

## Decomposition

Input classes: a served page (run picker present), an export (no
picker), a run under a 149-char path and one under a 20-char path; the
journey is the landing in the answer key, whose first screen this
changes.

## Out of Scope

- A logo image — a wordmark is text; §6b's dependency rule.
- Moving the run picker out of the rail — it is where `UX-667` put it.

## Acceptance Test

`header.getBoundingClientRect().height <= 72` at 1440 and 1024 wide;
the absolute path absent from the header's text and present in
`run_instance`; the §3i guard red on the path line reintroduced.

## Outcome

**Gap measured**, golden export, 1440x900 and 1024x768, `scrollTo(0,
2000)` first:

```text
1440x900   header_px 108   sticky   text starts "mixed_task_kinds\n\n/tmp/.../snapshot/mixed_task_kinds\n\nmeasured by bga 0.4.1 — analysed here by bga 0.4.1 I am ..."
1024x768   header_px 108   (same text)
```

**Close measured**, same export, after the fix:

```text
$ python3 -m pytest tests/unit/test_the_header_keeps_its_budget.py -q
........                                                                [100%]
8 passed in 3.13s
```

macro_micro, 1440x900: `header_px 45`, text `"bga \n\nrun — 2026-08-21
17:01:28 UTC\n\n \n\nI am \nanyone\n..."` (alias + start instant, no
path); `wordmark.title` = the run's absolute path;
`[data-section="run_instance"]` includes `Run dir <path>`; footer
carries `measured by bga 0.4.1 — analysed here by bga 0.4.1`.

| mutation | result |
|---|---|
| `stampIdentity` appends the path back onto `#run-name`'s text (the header's identity line) | `test_the_path_is_absent_from_the_header_text` reds on both fixtures; `test_the_height_is_within_budget_at_both_widths` reds too (macro_micro/1024: 76px, over the wrapped path) — 3 of 8 red |

Reverted from the pre-mutation copy (not `git checkout`), re-run green
(8 passed).

`--head` (`style.css`) was re-derived from the new, much smaller
header — 7rem→3.25rem wide, 9.5rem→4.5rem narrow — which
`test_a_rail_click_lands_on_its_section.py`'s pasted `BAND` (117,123)
also needed re-measuring: new landing 59-60px, band moved to (57,63).

`PAGE_BUDGET_B` (`test_the_report_you_can_attach.py`) moved 322,000 →
325,000 (+1,453 B, all source, measured with the diff toggled in one
worktree either side); the `macro_micro` committed-export row moved
515,000 → 516,453 for the same delta.

`BGA_SKIP_SELECTOR=1` on the commit: the one red guard left is
`test_every_browser_guard_is_listed`, which needs the new guard's row
in `tests/tiers.py` - the orchestrator's file per this track's rules,
not this commit's to add.
