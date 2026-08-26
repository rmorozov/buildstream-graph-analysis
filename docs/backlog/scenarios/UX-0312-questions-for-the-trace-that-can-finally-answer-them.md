# UX-312: questions for the trace that can finally answer them

**Priority:** Medium | **Status:** 🟡 In Progress | **Depends on:** UX-308, UX-309, UX-310, UX-311 (the vocabulary it queries), UX-210 (the library's last upgrade) | **Serves:** R1, R2 | **Topic:** viewer

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

## Progress (2026-08-26): the first clause, closed

🟡 **The debt this slate stands on is half paid; the body is not
started.**

**Done: the `trace_processor` round-trip.** `UX-298` recorded that it
was not installed and that no package for it existed in the
environment. That was true of `get.perfetto.dev`, which this
environment's network policy refuses at CONNECT - and not true of the
artifact host, which it allows:

```text
commondatastorage.googleapis.com/perfetto-luci-artifacts/
  v49.0/linux-amd64/trace_processor_shell
```

Perfetto v49.0-33a4fd078 (Trace Processor RPC API 14) loaded
`examples/06`'s rendered trace and answered in its own SQL: **826
slices, 836 flows, 538 counter samples peaking at 20** on one
`count`-united track, dependency flows resolving `codegen.bst →
lib-a.bst` and the rest exactly as `graph.json` says, and **every**
annotation key present in `args` as `debug.<key>` and reachable through
`extract_arg` - including a `debug.cmd` of **553 characters behind a
slice name of 120**, which is `UX-308`'s whole argument proven by the
reader rather than asserted by the writer.

`tests/unit/test_the_real_reader_agrees.py` is that round-trip as a
guard: twelve clauses, run when `trace_processor_shell` is present
(`BGA_TRACE_PROCESSOR` or `PATH`) and skipped when it is not. The
binary is neither vendored - 11 MB in a repository that declines a
protobuf dependency would be a strange addition - nor downloaded by the
suite, because a guard that reaches the network fails for reasons
unrelated to the code; the docstring says where to get one. Falsified:
truncating the `cmd` annotation to the name's length reddens the argv
clause.

It also had a finding of its own. `incomplete_reason` is the one
contract key a *finished* run never emits, so the coverage clause takes
the union over two traces - one finished, one interrupted - rather than
pretending a single capture carries the whole vocabulary.

**Still open: the one-time `ui.perfetto.dev` open.** The same network
policy refuses that host. It cannot be done from here, and saying
otherwise would be claiming a thing not done.

**Not started: this item's own body.** The trace dictionary in one
documented place, and the canned question library grown to the
arg/flow/counter questions the vocabulary now makes possible. Two of
those questions were *run* against the real reader while proving the
round-trip - time by element kind, and the failed processes - so they
are known to be answerable; they are not yet in the library, and the
emitted-equals-documented-equals-queried guard is not yet written.
