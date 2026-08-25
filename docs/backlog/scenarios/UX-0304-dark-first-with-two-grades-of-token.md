# UX-304: dark first, with two grades of token

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-212 (the non-color channels that make print free), styleguide §4-5 | **Serves:** R1 — the user asked for it by name | **Topic:** viewer

## Motivation

The user is a dark-theme reader and the page is designed light-first
with a dark media override. Round 41 measured the override: **three
of the four dark tokens sit above the mark-lightness band** —
text-grade colors doing fill work in every bar, band and dot — and
in light mode **amber↔green fails CVD separation** (ΔE 3.6 protan)
for adjacent marks. The palette was never validated because there
was no rule saying it must be; styleguide §4-5 now says both.

## Required Fix

Dark becomes the design surface: `:root` carries the dark tokens,
light becomes the override, and a print stylesheet renders light on
white (the export is printed — dark-first, not dark-only, the
challenge recorded in §5). Tokens split into text-grade and
mark-grade, each validated against its surface (the round-41
validator transcripts are the baseline; the values and their
validation results are recorded in `style.css` comments so the next
token change knows the procedure). Status tones keep their
mandatory non-color channel everywhere (§4.3) — which is what makes
the amber/green finding survivable rather than blocking.

## Out of Scope

- A theme toggle UI — the OS preference decides, as today (a toggle
  is a later filing if the field asks).
- Recoloring any semantic (good stays green etc.); values change,
  jobs do not.

## Acceptance Test

`:root` holds the dark set and the light override holds every token
`:root` does (set equality, guard); mark-grade tokens on their
surfaces sit inside the lightness band and meet 3:1 (values pinned
in the guard with the validation recorded); no hex literal outside
`style.css` (grep guard, mutation: an inline hex reddens); printing
the export (print CSS media) yields the light tokens; every
status-tone use retains a non-color sibling (booted check from
UX-212, now page-wide).
