# UX-304: dark first, with two grades of token

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-212 (the non-color channels that make print free), styleguide §4-5 | **Serves:** R1 — the user asked for it by name | **Topic:** viewer

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

## Outcome

🟢 **Done.** Dark is the base, fills stopped wearing text colors, and
the validator is in the repository rather than in a transcript.

**The instrument first.** `tests/palette.py`: WCAG relative luminance
and contrast, CIE L\*, ΔE2000, and the Viénot/Brettel/Mollon dichromat
projection — all from the standards, no dependency, so it runs in the
same interpreter as every other guard. Round 41's finding existed only
as prose; a token change had a claim and no way to re-run it.

**The band, which was a number in a transcript and is a rule now:**

```text
text-grade   >= 4.5:1 against its own surface        (WCAG 1.4.3)
mark-grade   >=   3:1 against its own surface        (WCAG 1.4.11)
             and L* inside the band for that surface:
                 dark   45..70        light   35..60
```

The floor keeps a fill visible; the ceiling keeps it from reading as
text, which is the failure that was measured. Run over the **old**
dark values it returns exactly round 41's finding — `warn` 70.7,
`good` 76.0, `accent` 72.8 over the ceiling, `bad` 59.6 inside — and
that reproduction is a guard clause, so the band cannot later become a
range that forbids nothing.

**What changed, and what deliberately did not:**

```text
dark    --warn-mark   #d9a441 70.7  ->  #c5922f 63.9   6.49:1
        --bad-mark    #e06c6c 59.6  ->  #db6868 58.0   5.34:1
        --good-mark   #6fcf8a 76.0  ->  #4dae6b 64.1   6.53:1
        --accent-mark #8ab4f8 72.8  ->  #6c97d9 61.9   6.09:1
light   all four                        unchanged, already in band
```

The light set needed nothing, which is the argument for validating
**per surface** rather than flipping one palette into the other: the
light values had been looked at once and the dark ones never. No
text-grade value moved in either theme, and no semantic moved — good
is still green.

**Dark-first, not dark-only.** `:root` is dark; the override is
`@media (prefers-color-scheme: light)`, which also matches a reader
who expressed **no** preference — so the base moved and the default
did not, and an unset browser gets the page it got before. `@media
print` renders the light tokens on white and drops the rail: the
export is attached, opened on machines nobody chose, and printed, and
a dark page prints as a black rectangle or as nothing.

**One real §4.3 violation, found by writing the guard.** The
unparsed-threshold input's entire signal was a red border. It now goes
`border-style: dashed` — a shape — and carries `aria-invalid` and a
title saying what it could not read. Everything else already had a
channel: the verdict's heading names its state, a finding carries
`data-severity` and prints it in the badge, a delta carries its sign,
a trend point carries `UX-212`'s marker from the schema.

**Why §4.3 is a rule rather than a hue problem**, measured on this
palette as ΔE2000 between adjacent status hues:

```text
light   warn/good  protan 6.5      dark   good/accent tritan 2.4
        bad/good   deutan 8.2             bad/good    deutan 9.5
        warn/bad   tritan 2.3             warn/bad    tritan 4.1
```

No ordering of four status hues clears every dichromacy, so no choice
of values fixes this and a status tone never travels alone. (Round 41's
prose quotes ΔE 3.6 for the light amber/green pair; its model and
metric are unrecorded and this reads 6.5. Same finding, and the number
here is the one the repository can reproduce — recorded rather than
quietly replaced.)

**The falsification round**, against the committed tree:

```text
P1   a dark mark climbs back out of the band       2 clauses red
P2   a mark drops under 3:1                        1 red
P3   `:root` goes back to light                    8 red
P4   the light override loses a token              3 red
P5   print disagrees with light                    2 red
P6   a fill goes back to a text token              1 red
P7   a hex literal appears in a module             1 red
P8   a new toned rule names no channel             1 red
P9   the unparsed filter loses its dashed border   1 red
P10  the delta loses its sign                      1 red
P11  a finding stops printing its severity         1 red
```

**Cost.** The export grew 984 B — stylesheet 17,995 → 18,663 — to
281,278 B (golden) and 320,457 B (macro_micro), both inside the bounds
`UX-302` restated; the page is 183,990 B against its 186,000 budget.

**Out of scope, held.** No theme toggle — the OS preference decides,
as before. No semantic recolored.
