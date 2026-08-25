# UX-299: a handoff that does not carry the trace in its hands

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-198 (the transport it re-thresholds), UX-298 (the artifact), UX-195 (the export rule it amends) | **Serves:** R1 | **Topic:** viewer

## Motivation

The tab-to-tab handoff fetches the whole trace into the report
page's memory, posts it to Perfetto's window, and was measured
right at 25 KB — and it is the same design at 1.5 GB, where the
browser tab meets the same OOM the server did. The `?url=` deep
link already exists as the fallback (`UX-198`); at scale the roles
invert: Perfetto fetching the trace itself — streaming, no copy
through the page — is the only transport that works. The export
has the same cliff: a `data:` URL inlining gigabytes is not an
attachment anyone can open.

Measured shape today: the server gzips the merged timeline **in
RAM** and holds the blob for its whole lifetime
(`tools/bga_view.py:325-326`, `:747`); no handler reads a `Range`
header; and the handoff (`bga/viewer/perfetto.js:153-174`) fetches
the whole trace into an `ArrayBuffer`, `postMessage`s it (a
structured-clone copy), and Perfetto decompresses it — three-plus
copies of the trace in browser memory before the first pixel.

## Required Fix

A size threshold (argued in the code, from the postMessage copy
cost) above which the deep link is the primary control and the
tab-to-tab post is not offered; below it, today's behavior stands.
The server serves the trace with the headers streaming needs
(length, gzip encoding as `UX-194` established). Above the same
threshold `--export` stops inlining the trace: the exported page
says the trace's size, and carries the `bga view --perfetto`
command and the deep-link recipe instead — the blast-box honesty
pattern. Both thresholds are one constant with one explanation.

## Out of Scope

- Range/partial-content support unless Perfetto's fetch is shown
  to need it (record the check either way).
- Any change below the threshold — the UX-198 behavior is verified
  and right at small sizes; this item is the large-size inversion
  only.

## Acceptance Test

With a generated trace above the threshold: the report page offers
the deep link, no fetch of the trace occurs from the page's own
JS (asserted via the DOM-shim fetch audit), and the export
contains no `data:` trace but does contain the command; below the
threshold both behave exactly as the UX-198 guards already assert
(those guards unchanged and green). Mutation: posting the
over-threshold trace tab-to-tab reddens.
