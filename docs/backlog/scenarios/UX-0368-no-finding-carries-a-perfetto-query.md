# UX-368: no finding carries a Perfetto query

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-229 (why bga believes what it believes), UX-312 (the canned question library), UX-348 (the handoff) | **Serves:** anyone who reads a finding and wants to see it in the trace | **Topic:** viewer

## Motivation

The tool's distinguishing claim is that it hands a build to Perfetto
with both planes on one clock. The report states findings. The two are
not connected:

```text
macro_micro: 11 findings
finding keys: copy_text, detail, elements, evidence, id, indent, severity, title
findings carrying trace_query: 0 / 11
```

`trace_query` exists — `provenance` records carry it, and `UX-312`
built a library of thirteen queries. But the library sits in its own
section, addressed to nobody in particular, and a reader who has just
been told *"4 element(s) are 71.9% of the 43.2s critical path"* is given
no query that shows those four in the trace.

So the handoff is a section a reader visits, rather than the next step
of the finding they are reading. The queries are general; the finding is
specific; nothing joins them, even though every finding already names
its `elements`.

## Required Fix

Every finding that names elements carries the query that shows them.

- A `trace_query` on the finding, resolved against the same library
  `UX-312` published, with the finding's own elements substituted — see
  `UX-369`, which is about the substitution being hard-coded today.
- Rendered where the finding is, not only where the library is: the
  finding's fold gains "see this in the timeline", the way `UX-204`
  gave each finding a button that knows why.
- Findings that name no element (`confidence`, `efficiency-score`) carry
  none, and the absence is stated rather than drawn empty — `UX-321`'s
  rule.

The mapping is the deliverable: **every finding id to the query that
shows it**, published in the contract so the page does not derive it.

## Falsification

Assert over the payload: every finding carrying a non-empty `elements`
carries a `trace_query`, and the query names those elements. Today that
is 0 of 11, which is the finding.

The other direction, so the fix cannot be a decoration: the query a
finding carries has to differ between findings that name different
elements. One query pasted onto eleven findings passes a "has a query"
clause and helps nobody.

## Out of Scope

Running the query. The page hands over to Perfetto and does not execute
SQL — `UX-296` and the viewer/Perfetto boundary. This item ends at
handing the reader the right query for the finding in front of them.
