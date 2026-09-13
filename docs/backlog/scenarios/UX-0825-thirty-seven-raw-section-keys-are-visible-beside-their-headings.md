# UX-825: thirty-seven raw section keys are visible beside their headings

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-669 (a citation is a question, not a key) | **Found by:** round 115, the design review | **Serves:** every reader opening a section | **Topic:** viewer | **Area:** bga-viewer | **Shape:** bounded

## Motivation

`format.js:353` appends `span.section-key.muted` — the payload key —
next to every section's `h2`. §4a says a description lives behind a
closing door; this key has no door:

```text
scale export   span.section-key computed display != none   37 of 47
walk capture   47 of 47 with every section open
h2 text        "How are blast radii spread across this graph?" + "blast_radius_distribution"
```

The key is contract vocabulary (§4b); the reader sees it at 13 px on
every open section.

## Required Fix

In `bga/viewer/format.js` the key moves onto the JSON toggle's `title` and `aria-label`
("Show the JSON behind blast_radius_distribution") and out of the
heading line. `data-section` keeps carrying it for the guards.

## Decomposition

Input classes: every section kind the golden export renders (60),
a section with no payload key (page-built, `UX-650`'s thirteen), and the
served page's store section; the journey is any rail landing.

## Out of Scope

- The JSON toggle itself — `UX-352`'s door stays.
- The rail's entries, which use the question — `UX-640`.

## Acceptance Test

`span.section-key` absent from the DOM; every `button.json-toggle`
carries the key in `title`; the §4g guard's key line goes green.
