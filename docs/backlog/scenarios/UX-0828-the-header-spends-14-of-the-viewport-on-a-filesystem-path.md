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
