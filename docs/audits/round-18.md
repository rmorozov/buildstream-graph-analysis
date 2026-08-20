# Audit round 18: the source axis, and a clean audit's tail

Run on 2026-08-20, same retained environment as rounds 10-17. Two
inputs: the sibling's landings for round 17 (UX-163..UX-168 in two
commits, plus two self-filed items — UX-169, a memory-representation
fix whose log corrects its own predecessor's figures, and UX-170, the
noise band's n=5 failure, filed 🔴 against real fdsdk data). And a new
user request that opens an axis: *blast analysis doesn't consider
element kind — and in the monorepo case, one repo populates many
elements' sources; the report should answer "this repo was touched:
how many recipes rebuild?"*

## Round 17's landings, verified — and every number reproduced

The review re-ran the measured claims rather than reading them, and
the target class (claims outrunning commits, the round-15/17 finds)
came back **clean**: the 204 MB analysis peak reproduced to the
megabyte with a byte-identical report digest matching the one printed
in UX-169's log; UX-170's band escape reproduced verbatim
(`IMPROVED -25.0%`, band `2762.79s .. 4048.77s`) from the five
retained fdsdk captures; the middle same-commit pairs all return
`NO SIGNIFICANT CHANGE`, as filed.

Live, on real captures:

- **UX-163** 🟢 with one real defect *under* it — all three interrupt
  windows behave: pre-build SIGINT says "Nothing was captured and
  nothing was left behind" (exit 130); mid-build salvages both planes;
  post-build prints the walk-forward naming `build.log` and the exact
  `bga extract` line — which was pasted verbatim and produced a
  working `run/` that analyzes as unfinished. The defect: the 300s
  grace **cannot deliver its stated benefit**, because on interrupt
  the read loop exits and nothing drains the child's stdout again —
  bst's closing Pipeline Summary never reaches the log however fast
  bst complies, and a full pipe buffer blocks the stopping bst into
  the escalation. Demonstrated with a SIGINT-trapping fake bst; filed
  as **UX-175** with the discarded stopped-vs-killed return value and
  the `bga extract --interrupted` gap.
- **UX-164** 🟢 — the hint is built from the pair actually compared
  and the three-way counts flow from the queue summary through the
  violation to both renderers without re-derivation. Caveats to
  **UX-176/177**: the paste-and-go property is untested prose (and
  one guard is a vacuous source-grep), and the `@stamp` fallback hint
  is unpasteable when a same-second sibling makes the full stamp a
  strict prefix — `resolve_snapshot` has no exact-match win.
- **UX-165** 🟢 — ten strings repaired (the file says seven and nine
  in different places); the fragment guard is honest in its docstring
  and overstated in the log (it skips seven punctuation marks,
  including the comma). **UX-176**.
- **UX-166** 🟢 — `buildstream2.conf` first, shared scalar reader,
  relative argv skipped. One narrower residual corner: bst selects
  the config *file* by existence, bga falls through on missing *key*.
  **UX-177**.
- **UX-167** 🟢 — keep-set verified live on the round-17 store (the
  newest healthy run survives two unhealthy aliases; the husk is
  deleted and counted separately); the phantom `baseline` key removed
  with no dangling references; the review re-ran the mutation and it
  reddens as claimed.
- **UX-168** 🟢 — the census double-parse fix (5.0s of 5.9s was
  PyYAML), the store-size memo, all six one-liners; and the log's
  "the memory headline does not land" deviation section is exactly
  what the convention asks for — it filed UX-169 rather than claiming
  the bound.
- **UX-169** 🟢 — the representation fix holds: pairing consumes,
  drains per slot, and the opens parser streams with parity guards;
  204 MB against 344 MB pre-fix at the same scale, digest-identical.
  The Motivation's "three copies" story is imprecise about the third
  (the report *is* the records list) — an annotation, **UX-176**.
- **UX-170** stays 🔴, correctly — and its documentation pass has one
  word wrong (`real-project.md` calls the band's escapee the
  "slowest" run; 2712.39s is the fastest).

Suites on the committed range: **2050 passed** (2018 unit + 32
top-level), `make lint` and `lint-docs` clean, status table and file
markers agree for all of 163..170.

## The new axis: blast analysis by shared source (Direction 6)

The user's request, argued in full as
[Direction 6](../design/directions.md) and decomposed into four
filings. The mechanism that makes it worth a direction rather than a
feature: BuildStream keys a `git` source on its **ref** — `directory:`
narrows what is staged, not what is keyed, so twenty elements sourcing
one url all rebuild on any commit to that repository — while a
`local` source keys on **content**, giving per-directory blast. The
same monorepo consumed two ways differs by an order of magnitude, the
`.bst` files encode which way, and everything needed is already on
disk: `read_element_yaml` parses sources (census), `graph.json`
carries `element_kind` and typed edges, the run directory carries
measured durations.

- **UX-171** (High): the source inventory and the resource blast
  table — resource → direct elements → closure, counts by kind,
  measured cost, keying clause; the monorepo headline in Key
  Findings.
- **UX-172**: `bga blast TARGET` — the question pointed the
  developer's way (url / path / element), with the file-level answer
  for local sources.
- **UX-173**: kind-awareness in the *existing* blast surfaces — the
  user's first sentence taken literally; `graph.json` has carried
  `element_kind` all along and a blast of 84 where 39 are stacks is
  not a blast of 84. Building-vs-assembling split plus cost-weighted
  ranking.
- **UX-174**: the monorepo patterns page — semantics first, then the
  number that makes the choice.

A Plane 3 extension (historical rebuild frequency per resource) is
named in the direction and deliberately not filed until the inventory
exists to join against.

## Standing

The MVP verdict (round 12) stands; the big-project axis is nearly
closed (UX-175 is its last real defect, and it is one drain loop);
the audit class itself has visibly tightened — this round's review
reproduced every measured number exactly and found no claim that
outran its commit, only guards weaker than their prose. The new work
is Direction 6. Priority for the sibling: **UX-175 first** (it breaks
the exact scenario the last two rounds hardened), then **UX-171** (the
axis-opener; 172/173/174 build on its inventory), then UX-170 (the
band at n=5 — now the oldest open High-adjacent correctness item),
with UX-176/177 as the tail.
