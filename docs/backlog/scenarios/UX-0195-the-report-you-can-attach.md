# UX-195: the report you can attach

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-193 (the page this exports), UX-115 (the CI journey this joins)

## Motivation

Direction 7's second delivery mode: the same page, as a file.
`bga view --export report.html` inlines the run's JSON into the
static page and writes one self-contained artifact — no port, no
server, no network. Three scenarios earn it:

- **CI**: the pipeline that posts the UX-115 comment also attaches
  the full visual report as an artifact — the comment is the
  headline, the export is the detail, and neither needs a viewer
  deployment.
- **Remote debugging**: "send me your report" becomes one file — the
  same motion the diagnosability rounds built for failure evidence,
  now for analysis.
- **The archive**: a snapshot pruned later still has its rendered
  report if the export was kept — cheap institutional memory.

## Required Fix

1. `--export PATH` on `bga view`: same page code, payloads inlined
   (a `<script type="application/json">` block per payload; the page
   reads inline-first, fetch-second — one code path decides). The
   Perfetto button still works from `file://` (the handshake is
   opener-based, no server involved); when the trace would bloat the
   file past a stated budget, it is left out with the button saying
   what to run instead — recorded, not silent.
2. Size discipline: the export's budget stated (page + payloads;
   measure on the golden run and the 1,202-element synthetic — the
   JSON dwarfs the page or the page has failed Direction 7).
3. CI wiring: `ci-comment.md` gains the artifact step beside the
   comment step, marked optional; the workflow uploads it when the
   compare ran.

## Out of Scope

- Hosting exports anywhere (they are files; where they go is the
  pipeline's business).
- Multi-run bundles (one run, one file; compare's export carries its
  pair inline like the compare JSON does).

## Acceptance Test

`bga view --export r.html @last` writes a file that opens with zero
network access (asserted: no external fetches in the page source, all
payload script blocks present) and renders the same data the served
mode does (the UX-193 parse harness, pointed at the file). The
export of the synthetic run stays under the stated budget or the
budget note explains. The CI docs lines pass the docs-commands test.
