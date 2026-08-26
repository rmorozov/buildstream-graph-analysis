# UX-312: questions for the trace that can finally answer them

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-308, UX-309, UX-310, UX-311 (the vocabulary it queries), UX-210 (the library's last upgrade) | **Serves:** R1, R2 | **Topic:** viewer

## Motivation

The canned library was track-scoped by `UX-210` and has been
querying names and timestamps ever since, because that was all the
trace carried. Once `UX-308`..`UX-311` land, the questions people
actually ask become one `extract_arg` away, and the library should
ask them: time by element kind; failed processes and what ran
them; CPU-time versus wall-time per element (the sandbox-tax
cross-check, from annotations instead of containment joins);
critical-path-only views; cache outcomes split; "what did this
element wait for", answered by flows instead of timestamp
proximity. The trace dictionary — the annotation key contract —
needs its one documented home, or the keys drift and every query
built on them breaks silently.

## Required Fix

First, the debt this slate stands on: `UX-298`'s two recorded
deviations close here — the `trace_processor` round-trip enters CI
(the vocabulary needs the real reader, not only the in-repo
decoder), and the one-time ui.perfetto.dev open happens and is
recorded with what was seen. Then:

The trace dictionary documented in one place (the styleguide's
sibling for the trace: key names, types, planes, stability rule —
a rename is a break, the UX-190 discipline applied to annotation
keys); the question library grows the arg/flow/counter questions
above, each with its `why` naming the plane and vocabulary it
reads; a guard holds emitted-keys == documented-keys == queried
keys' existence (a question referencing an unemitted key reddens;
an emitted key nobody documents reddens).

## Out of Scope

- A query runner in the page (unchanged position).
- Questions requiring data no plane captures — a question the trace
  cannot answer honestly is a capture gap first, and capture gaps
  get their own argued filings.

## Acceptance Test

Every library query parses and returns non-empty on the golden
two-plane trace (the `UX-210` static guard extended to execution
where `trace_processor` is available); the dictionary guard
reddens both ways (mutation: emit an undocumented key; query a
missing one); the CPU-vs-wall question's answer for the sampled
element equals the published join's figures.
