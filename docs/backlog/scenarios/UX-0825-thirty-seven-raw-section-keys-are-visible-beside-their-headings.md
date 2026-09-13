# UX-825: thirty-seven raw section keys are visible beside their headings

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-669 (a citation is a question, not a key) | **Found by:** round 115, the design review | **Serves:** every reader opening a section | **Topic:** viewer | **Area:** bga-viewer | **Shape:** bounded

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

## Outcome

**Gap measured**, golden export (`tests/pages.export_uri`,
`tests/fixtures/golden/mixed_task_kinds`), `span.section-key`
`getComputedStyle(...).display`:

```text
spans: 33   visible: 33   sections: 47
button.json-toggle with a title: 0 of 35
```

(round 115's 37/47 was on a different export; 33/47 is this round's
own tree.)

**Close measured**, same fixture, after the fix:

```text
spans: 0   sections: 47
button.json-toggle with a title: 35 of 35
every title/aria-label contains its own data-json-toggle key
```

`tests/unit/test_the_json_toggle_carries_the_key.py` (new) holds both
clauses on the golden export.

**Mutations verified red and reverted (2):**

| mutation | file | reddened | count |
|---|---|---|---|
| restored `span.section-key.muted` in `sectionHead` | `bga/viewer/format.js` | `test_no_section_key_span_is_in_the_dom` (`spans: 33`) | 1 |
| `SHOWN_TITLE` dropped the key (`"...this section"`) | `bga/viewer/rawjson.js` | `test_every_toggle_carries_its_key` (35 toggles missing their key) | 1 |

Both reverted from the scratchpad copy; `test_the_json_toggle_carries_the_key.py`
green after each revert. Neither mutation touched a second guard.

**Deviation.** HOLD for two rows that are the orchestrator's — the guard's tier (`tests/tiers.py`, 2.0 s, medium) and §7's row for §4g naming it — and one wording change at merge: the toggle's accessible name now starts with its visible label ("view as JSON — <key>"), the verifier's label-in-name note.
