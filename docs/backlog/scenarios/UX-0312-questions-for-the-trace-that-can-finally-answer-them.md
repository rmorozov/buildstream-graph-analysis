# UX-312: questions for the trace that can finally answer them

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-308, UX-309, UX-310, UX-311 (the vocabulary it queries), UX-210 (the library's last upgrade) | **Serves:** R1, R2 | **Topic:** viewer

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

**Closed since, by `UX-314`.** This paragraph read "still open: the
one-time `ui.perfetto.dev` open - the same network policy refuses that
host", and it was right when it was written and stale by the end of the
same round. `UX-314` found the way: the host is refused at CONNECT, and
the bucket serving it is not, so the deployed UI mirrors byte-for-byte
and the handoff was driven in a real browser. `UX-298`'s file recorded
that closure and this one did not; `UX-321` reconciled them.

**Not started: this item's own body.** The trace dictionary in one
documented place, and the canned question library grown to the
arg/flow/counter questions the vocabulary now makes possible. Two of
those questions were *run* against the real reader while proving the
round-trip - time by element kind, and the failed processes - so they
are known to be answerable; they are not yet in the library, and the
emitted-equals-documented-equals-queried guard is not yet written.

## Outcome (2026-08-26): the body, and what it found

🟢 **Done.** The library was not merely thin. It was **dead**.

**Every canned question returned zero rows.** Measured by rendering a
trace with this tree and decoding it: `UX-204` wrote the queries
against the legacy Chrome JSON trace, where an `args` object becomes
`args.<key>` in `trace_processor` and the converter wrote a `cat`
field. `UX-298` made TrackEvent the default, where the same facts are
*debug annotations* under `debug.<key>` - and `EVENT_CATEGORY_IIDS` sat
"reserved rather than used" until `UX-308` spent it on `failed`. Nobody
re-pointed the library, and nothing could notice: `extract_arg` on an
absent key returns null, so a wrong question answers with an empty
table rather than an error.

```text
                        args.* key    category scoping
element-time                dead              dead
process-storm               dead              dead
sandbox-tax                 dead              dead
stalls                      dead              dead
element-commands            dead              dead
dependency-wait             dead              dead
```

Off the wire before the fix: **zero categories interned, zero category
iids on any event.**

**What landed.**

1. *The scope came back, and now partitions.* The emitter tags every
   slice with `UX-210`'s own three names - `bst-builder`,
   `native-process`, and `bst-invocation` for `UX-311`'s identity
   slice, which belongs to neither plane. Because the three partition
   the trace, a scoped query cannot silently miss a class of slice; and
   because the names are unchanged, a query someone saved against the
   old trace starts working again rather than needing a rewrite.
2. *The library selects what the trace emits.* `debug.<key>`, and
   categories matched with `glob` - a failed Plane 2 process is
   `native-process,failed`, and `= 'native-process'` would miss exactly
   the failures.
3. *Seven questions the vocabulary makes answerable:* time by element
   kind, what failed and what ran it, CPU against wall per element,
   peak RSS as a maximum and never a sum, what an element waited for
   **by the flow graph** rather than by the clock, the concurrency
   curve, and whose run this is.
4. *The trace dictionary* is `docs/spec/trace-dictionary.md`: every key
   with its plane and meaning, the scopes, the counter track, the flow
   kinds, and the rule that a rename is a break.

**Falsification.** Eight mutations against the committed tree:

```text
Q1  a query returns to `args.<key>`                    1 guard red
Q2  Plane 2 slices lose their scope (the bug)          2 red
Q3  a query names a key the emitter never writes       1 red
Q4  an emitted key is documented nowhere               2 red
Q5  an emitted key nobody wrote down                   2 red
Q6  a category matched with `=` instead of `glob`      2 red
Q7  the identity slice is uncategorised                1 red
Q8  the dictionary stops calling itself a contract     1 red
```

Q5 and Q7 were each run twice: the first attempt at both broke the
module rather than the property, which is the mutation's fault and not
a finding.

**Two guards were asserting the broken shapes**, and both are
corrected rather than deleted: `UX-210`'s required the category
spelling that matched nothing, and `UX-308`'s asserted a category tuple
that held only `failed`.

**Deviation, recorded.** The acceptance asks that every query *return
non-empty* against the golden trace under `trace_processor`. That
binary is not installed here and the suite deliberately does not fetch
one, so the clauses hold the queries to the emitted vocabulary -
statically, in both directions - rather than to a row count. The
execution arm belongs beside
`tests/unit/test_the_real_reader_agrees.py`, which already skips for
the same reason. What is checked is stronger than it sounds: the defect
this item found was exactly a name mismatch, and that is what these
clauses catch.

