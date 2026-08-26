# Audit round 43: the trace speaks the format, not yet the language

Run on 2026-08-26, same retained environment. Two inputs: the
sibling's landing of Direction 15 (UX-296..301) and the visual
contract (UX-302..306) — two rounds, verified below — and the
user's question that names the round: now that the timeline is
Perfetto's own format, are we actually using Perfetto's power?

## The landing, verified

Eleven for eleven, with fourteen mutations run and all fourteen
discriminating. The Direction 15 half: the big-run guard generates
a million-record monolith and the view opens it **zero** times
(39.8 MB of RSS to view its neighbour, against 1,230 MB with the
parse mutated back in — the store-walk tax is gone); `plane2/v2`
writes no record list and the legacy shape stays readable;
`UX-297` stands honestly 🟡 with its streaming clause deferred to
the emitter and the deviation recorded. The wire format is guarded
by an in-repo protobuf decoder against a digest-pinned upstream
fixture — corrupting one field number reddens six clauses. The
handoff's 4 MiB threshold, the export's command-not-data-URL, the
prune keep-set, the sizes stated at capture: all held under
mutation. The visual-contract half: the §1 mapping is code
(`shapes.js`) with the boot JSON-walk red on a single raw `<pre>`
(eight clauses, both pages, all toggle states); dark is the design
surface with the mark-band validated and inline hex a red; the
emphasis walk reds on a second bold in the decision block; strip
and sparkline geometry red when flattened. Suite: **3,713 passed,
0 failed**; lint clean; every marker agrees with its row.

Two findings, neither silent: `UX-296`'s "both ceilings redden" is
hardware-relative — under the reintroduced parse the time ceiling
did *not* fire here (14.5 s against 20); the RSS and open-count
clauses carry all the discrimination. And `UX-298`'s acceptance
left two recorded deviations open — **no `trace_processor`
round-trip exists in CI, and the one-time ui.perfetto.dev open has
not happened** — honestly logged, but load-bearing for this very
round, so `UX-312` absorbs closing both as its first clause.

## The audit: what the trace says, against what bga knows

The inventory was done by reading both sides of the seam. The
emitter (`tools/native_trace/trackevent.py`) and the timeline
writer (`tools/bga_timeline.py`) produce: process and thread
tracks for both planes, slices, instants for processes with no
observed exit, interned names, correct sequence flags. What a
slice *carries* is its name alone — and Plane 2's name is the
command truncated to 120 characters, so the argv tail that
distinguishes two compiler invocations is gone from the trace
entirely.

Against that, what the run directory already holds and the trace
never says: per process — `cpu_us`, `max_rss_kb`,
`children_cpu_us`, `exit_status`, `exec_chain`, hook-or-spine
provenance; per task — element kind, task type, cache outcome;
per run — the dependency graph, critical-path membership, host
class, completeness, the plane-alignment anchor. And the Perfetto
vocabulary built to express each of them, unused: **debug
annotations** (the details panel is empty; `extract_arg` has
nothing to extract), **flows** (the "why did this start now"
arrows a timeline exists for), **counter tracks** (`TYPE_COUNTER`
pinned in round 42 with the comment "reserved rather than used"),
**trace identity** (a trace leaves the machine and forgets whose
build it was, including whether it was interrupted — an honesty
the report enforces and the trace silently lacks), and
**descriptor ordering** (lanes appear in discovery order; the
critical path is nowhere first).

The user asked for low-hanging fruit; this is an orchard. Every
item rides the existing single streaming pass under the existing
RSS ceilings; every fact is already captured; the field numbers
follow the UX-298 read-from-the-protos procedure. Filed as
`UX-308`..`UX-312`, argued as Direction 15's second iteration:
**the artifact is not just Perfetto's format — it is Perfetto's
vocabulary.**

## What was deliberately not proposed

Sampling new data at capture (a counter must come from records
the trace already has — the manifest states the host, it does not
sample it); cross-element Plane 2 flows (no captured relation
exists, and a flow must never invent causation); clock-domain
machinery (the anchor+offset alignment stays, stated rather than
re-engineered); any viewer work (Perfetto is the viewer here —
that is the positioning doing its job).

## Standing

Priority: `UX-297`'s open half and `UX-308` travel together — the
annotations ride the same streaming pass the emitter still owes —
then `UX-309` (the flows are the feature a timeline exists for),
`UX-311`, `UX-310`, and `UX-312` last since it queries what the
others emit and pays `UX-298`'s two debts first. None of it blocks
the field user: the trace they can already open just says more
with each landing. The round's one-sentence verdict for the user's
question: the container is right, the vocabulary is empty, and
everything needed to fill it is already on disk.

## The landing (2026-08-26)

All five items and `UX-297`'s open half, in the order this round
recommended. Every figure below was measured, and every guard was
falsified against a committed tree.

| item | what landed | mutations |
|---|---|---|
| `UX-297` | parsing and pairing are one pass; peak 288.3 → 259.5 MB, 8.2 → 7.1 s, digest identical | 6, all red |
| `UX-308` | ten debug-annotation keys as a contract, plus the `failed` category | 8 red, 1 rejected |
| `UX-309` | dependency and exec-chain flows; zero packet cost at both scales | 6, all red |
| `UX-311` | the `bga: run` identity track, explicit lane order, kinds in labels | 6, all red |
| `UX-310` | one counter series, and two refusals argued rather than omitted | 6 red, 1 rejected |
| `UX-312` | its **first clause only**: `UX-298`'s `trace_processor` debt, paid | 1 red |

**The round's own premise, tested.** `UX-298`'s unpaid
`trace_processor` debt was called load-bearing here, and it was:
everything the four items added sat on a wire format only `bga` had
ever read. The binary turned out to be reachable from the artifact host
even though `get.perfetto.dev` is refused, and Perfetto v49.0 confirmed
all of it - 826 slices, 836 flows, 538 counter samples peaking at 20,
and every annotation key resolving through `extract_arg` as
`debug.<key>`, including a 553-character `debug.cmd` behind a
120-character name. The container is right, the vocabulary is no longer
empty, and the reader agrees.

**Three things the work found that the filings did not predict.**

1. *`exit_status` is a string with a vocabulary, not a number.* The
   first failed-category rule would have marked every process failed.
2. *`UX-310`'s memory series cannot exist.* `max_rss_kb` is a
   per-process lifetime peak; a curve from it sums peaks that never
   coexisted. Refused with a clause rather than omitted, and its two
   surviving bullets turned out to be one question.
3. *Round 43's guards read a gitignored capture.* Every clause the four
   items wrote against `examples/06`'s `.bga` would have passed here
   and failed in CI. `test_a_guard_reads_only_what_a_clone_has.py`
   caught it; the properties now have committed-fixture clauses beside
   them and only the figures stay behind a skip.

**Still open.** `UX-312`'s own body - the trace dictionary and the
canned question library the vocabulary now makes possible - and
`UX-298`'s second deviation, the one-time `ui.perfetto.dev` open, which
this environment's network policy refuses. `UX-313` was filed on the
way past: the record list is the floor `UX-297` left, and whether it
can be windowed is a measurement nobody has taken.
