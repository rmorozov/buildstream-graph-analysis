# Round 116 — the nineteen open rows, in three waves of tracks

Run on 2026-09-13.

Round 115 filed fifteen rows from the owner's twelve considerations and
a design review, and left four older ones open beside them. This round
took every open row: bounded shapes as `implementer` tracks in
worktrees, judgement shapes as the session's own decision written into
a track's brief, three small ones by the session itself, and a
`verifier` behind every track. Nineteen rows were open at the start;
nineteen closed, and a twentieth (`UX-837`) was filed and closed at the
gate.

## What closed

| wave | rows | how |
|---|---|---|
| 1, six tracks at once | `UX-820` `UX-825` `UX-826` `UX-832` `UX-834` `UX-836` | bounded; load 30 on four cores, one selector sweep of 34 m |
| 2, three tracks | `UX-822` `UX-828` `UX-835` | bounded, after wave 1's merges they depended on |
| the session | `UX-819` `UX-823` `UX-827` | judgement, small: `traceUrl` reads the JSON node; `start_offset_us`; the twin draws every mark and the mean |
| 3, six tracks | `UX-817` `UX-818` `UX-824` `UX-829` `UX-830` `UX-831` `UX-833` | judgement, the decision in the brief; `UX-824` resumed after a session limit |

Every track's Outcome carries its gap, close and mutation table; the
Deviation line on each is the session's. The page: the header is
identity only (108 → 45 px), the readers table is gone, the From
column is an offset, the twin draws fifteen marks, the max-jobs advice
is one flat table, every joined field draws a column, the serial
chains are ranked, a custom source kind can be declared, and a guard
reads both exports for the register (`UX-824`, §4g).

## What the verifiers found

Seventeen verifier runs over sixteen tracks; nine returned HOLD. Four
of the nine were the same shape — a guard that could not fail:

- `UX-818`'s guard parsed SQL and proved syntax, not parity with the
  page; a swapped window passed. Two real divergences from
  `renderedSql` (the empty element, an empty `bounds`) were fixed at
  merge with a parity case per question through node.
- `UX-824`'s item 3 read `td` only; the pipe keys it exists to catch
  render in a `dd`.
- `UX-831`'s row-height clause measured a row inside a closed fold:
  zero, under any budget.
- `UX-833`'s nine guards never crossed `bga/cli.py` or the report's
  publish gate; hardcoding the list to `[]` left the suite green.

The other five: a help line that fit (`UX-832`), a wrong selector
(`UX-836`), tier rows that are the orchestrator's (`UX-825`, `UX-822`),
forty citations left (`UX-826`), and `UX-830`'s walk through join
nodes — a diamond gave three near-duplicate chains, on no fixture the
suite had. `UX-831`'s Acceptance Test asked for `data-levels="1"`,
which `shapeOf` cannot read for any array of records; refiled to the
measured 3 with the reason.

## Standing

- `UX-827` moved the 50-element page budget 36,300 → 36,900 px
  (35,900 → 36,822 measured); the styleguide's §3e table follows it.
- Three baseline findings surfaced on the round branch only after the
  tracks' selectors had run against older bases: `start_offset_us`
  undocumented, a pyright optional access, two S105 false positives on
  SQL placeholders. Fixed in one commit at merge.
- The advisory in `CLAUDE.md` re-derived: 302k median for judgement
  rows against bounded's 259k, 60 of 104 runs, four whose own cell
  disagrees.
- `UX-830`'s ranked table moved the page budgets: 36,900 → 38,200 px
  on the 50-element class, 32,000 → 36,500 px on the 4,100 class,
  re-measured on the merged tree (macro_micro 37,743, xl 35,669).

## Review 23

The cadence guard reddened at the gate — 26 closed rows since review
22 — so review 23 ran there, over rounds 114–116's documents: three
filings (`UX-838` to `UX-840`), two of them review 22's shape one turn
further (a guard satisfied by the sentence beside the drifted table or
key), one the README's undated clone figure. The §3e table this round
left one item behind was corrected at filing; the rest stay open.

## Process, measured

- Six tracks at once pushed load to 30+ on four cores; one selector
  sweep took 34 m and one never finished. Wave 3 ran four tracks with
  the verifiers queued behind them, load 2.6–13.
- Every track opened on the default branch's tip, 1–15 commits behind
  the brief's base, and took `--ff-only` as instructed; the check
  cost nothing and caught every one.
- A session limit stopped `UX-824` mid-mutation; resumed by message
  twenty minutes later with the worktree intact.
- Two tracks stashed their own work by accident and recovered by sha.
- Nine merge conflicts across eighteen cherry-picks, every one in the
  four shared files (`UNRESOLVABLE`, the spread, the byte bounds, the
  §7 rows) — resolved by keeping both, never by choosing.
- A track's `dev_baseline.py --write --force` would have swept three
  unrelated findings under its reason; the track folded one entry by
  hand instead.
- The batch gate found seven reds no track's selector had: `xl`'s data
  half (194,536 → 266,945 B, the direct lists 20,047 B gzipped and the
  chains 812), macro_micro's export bytes, `bga/report/_shared.py` wide
  by a test-method substring, three rail guards still landing at the
  old header's 105 px (60 now; one link's centre at 899.9 of 900), and
  `structured.js` at 1,502 lines — `UX-837`, the copy-format preference
  moved to `viewstate.js` behind `dev_js_deps.py --crossings` and
  `--order`, with the architecture map re-grounded.

## Agents

Thirty-four runs — 16 `implementer` (five resumed), 17 `verifier`, 1 `general-purpose` (review 23),
all on `sonnet`; the session took `UX-819`, `UX-823`, `UX-827` and
the `UX-818` parity fix. The rows are in the ledger.

| | |
|---|---|
| implementer | 16 tracks, all merged behind a verifier; 92k–475k tokens; 15–77 m |
| verifier | 17 runs, 9 HOLD then PASS on re-read or at merge; 37k–117k tokens; 4.5–26 m |
