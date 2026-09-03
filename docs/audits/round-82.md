# Audit round 82: the documents, read against the tool they describe

Run on 2026-09-03, after the sibling's rounds 78-81 closed the backlog
to zero open rows at `UX-562`. The brief: the tool has moved a long
way from where its documents were written — review every document
against the implementation and make the ground firm before the next
improvements are built on it. Method: five read-only researchers,
one per document group, each reading a document in line ranges and
checking every claim against the code by running something —
`grep`, the guard the claim names, the command the guide prints — and
returning conclusions with `path:line` evidence. Two were cut off by
the session limit and re-run. Nothing was edited; everything found is
a filing.

## The verdict, in one table

| group | documents | true where guarded | drifted where not |
|---|---|---|---|
| specification | `specification.md` (2,899 lines) | Parts 3-16, 18-22, 24-26, 28, 30-36 on every sampled claim, every numeric constant equal; Part 32 row-for-row; nine of thirteen invariants named by a guard (135 passed) | Parts 23 and 27 in the spec and nowhere else; Part 8.2's `UNKNOWN` holder structurally unreachable; Part 29 wired to `None` with the store's series unused; I6 with no guard and no code, I10 with no guard; Parts 37-40 describing a shape the tree left |
| architecture | `architecture.md`, `ingestion-pipeline.md`, `trace-dictionary.md`, `capture-workflow.md` | CLI table, 23-row contract inventory, 23 viewer rows, the trace dictionary's 37 keys / 3 scopes / 6 counters / 2 flow kinds | a 2026-08 count at line 3 (75 → 560), two files named that do not exist, the capture workflow three steps and eight files behind its own yml, ingestion facts on `bst` 2.7.0 with one now false, "by construction" unamended after the join that made it true |
| user guides | `README.md`, `docs/README.md`, `CHANGELOG.md`, `cli.md`, `real-project.md`, `ci-comment.md`, `what-the-viewer-answers.md` | the 30-second start byte-identical, 63 of 63 flags exist, every exit code but one, the CHANGELOG's contract state | invalid arguments exit 2 (the table says 1, and 2 is ingestion's), a documented `\| head` prints a traceback, the question count stated three ways, the committed example's own next step refuses with exit 6, five verbatim blocks neither dated nor fresh |
| design | `directions.md`, `roles.md`, `styleguide.md` | every direction's decomposition 🟢; the styleguide enforced by 31 guard files (539 passed); the §1a hint vocabulary both ways; R6 pinned as the unserved role | two direction tails unfiled and silent, a tag item with zero tags, no status per direction; the roles table denying `store-aggregate/v1`; §7's ledger saying seven guarded sections have no guard; the round history missing rounds and linking two rows to a file that is not theirs |
| process | `CLAUDE.md`, `rules.md`, `fixing-guide.md`, `style-guide.md`, `release-guide.md`, six skills, three agents, three hooks, `ci.yml` | CI matches every document that describes it; the card's 8 rule-holding guards; the register (66 of 66 Outcomes under the cap, median 77) | thirteen stale numbers, all in unguarded prose; the card's guard column counted not read (1 wrong name, 3 adjacent, 2 "—" with enforcement); the premise detector reading 0 % against a round that reports seven |

The pattern is the same in every group, and it is the finding of the
round: **a sentence a guard reads is true; a sentence no guard reads
has drifted at the rate the tool moves.** The documents are not badly
maintained — the guarded halves are exact to the digit — but the
tool changed faster than prose can, and the unguarded prose is now
the map of where the tool used to be.

## What that means for the ground

Three things follow, and the filings are shaped by them:

1. **Counts and versions are derived or dated, never typed.** The
   `UX-549` shape (a figure the guard derives) and the `UX-511` shape
   (a block labelled with its date and cuts) already exist; the
   filings extend them to the places they missed — the process
   layer, the architecture document's prose, the guides' verbatim
   blocks, the question count.
2. **A guard column is read, not counted.** The rules card names
   twelve guards and the card guard checks that eight cells are
   filled; markers in the guards make the column a fact.
3. **The maps walk the tree they map.** The context map cannot see
   below `tools/` or inside `bga/viewer/`; the capture-workflow
   document has a yml it never reads; the link guard sees links and
   not backticked names.

## Per group

### Specification

The core holds to the constant: quantization (Part 3, round-half-up
at 50,000 µs in four sites), the task key (Part 5), the tie-break
tuple (Part 7), the phase enum's eight names (Part 10), the leaf and
blast thresholds 200 / 0.1 (Parts 24-26), the confidence gates 0.95
/ 0.98 (Part 33), determinism at n = 100 (Part 35), and each 36.x
test has its named file. Part 32 is the one Part with a mechanical
guard and it holds row for row — 23 ids, 3 inputs, the 32.6 layout
against a real capture. What drifted needs a human, because it sits
outside Part 32: Part 8.2's `UNKNOWN`/`ambiguous` holder is a state
the code cannot reach (`'ambiguous': False` "structurally always",
so 33.4's term is a constant zero — `UX-563`); Parts 23 and 27 are
listed as `signals` keys and exist nowhere else, with no record of a
decision (`UX-564`); Part 29 passes `historical_durations = None`
unconditionally while the store now holds the series it needs
(`UX-565`); Parts 37-40 describe a report and a tree that were never
built that way, and line 1714 counts "all three" contracts where
there are eight (`UX-566`). Of the thirteen invariants nine are named
by a guard; I6 (occupancy within capacity) has no guard and no code,
I10 (segment adjacency) no guard, I7 is I4 restated, I13 is held by
behaviour under another name (`UX-567`). A census of `Part N` across
the tests names none for 2, 6, 17, 20, 22, 23, 25-29, 34, 37-40 —
Part 28 is implemented and simply unnamed — so the spec has no index
of which Part a guard holds (`UX-568`).

### Architecture and the pipeline documents

The guarded skeleton of `architecture.md` is exact: the CLI table,
the contract inventory (23 ids, 8 printable, 9 superseded, 3 read),
the viewer's 23 rows, the log's date. Around it: line 3 still says
"75 scenarios" against 560; the reading order names
`optimization-walkthrough-06.md` and `design-directions.md`, neither
of which exists, and the link guard sees markdown links only; the
planes' entry-point files are named nowhere; `tools/native_trace/`'s
four members and `dev_run.sh` are in neither map because the
context-map guard globs `tools/*.py` once (`UX-569`, `UX-573`).
`capture-workflow.md` says the warm step is `bst build` where the
yml runs `artifact pull`, says "weekly and nothing else" where the
yml has two crons and the doc's own later line admits the monthly
one, and lists 13 of the 21 files the job uploads (`UX-570`).
`ingestion-pipeline.md` confirms its facts on `bst` 2.7.0 thirteen
times on a machine running 2.8.0, and two facts are now false on
their own terms (`UX-571`). The trace dictionary matches the emitter
exactly — 37 keys, 3 scopes, 6 counters, 2 flow kinds — and still
says "by construction" of a peak that `UX-406`'s join now constructs
(`UX-572`).

### The user guides

The front door holds: the README's 92-line block is byte-identical
to a fresh run, all six demo commands exit 0, 63 of 63 quoted flags
exist, the CHANGELOG names every contract bump since 0.3.0. The
table of exit codes is right in every row but one — `bga analyze
--bogus` exits 2, which the table gives to ingestion (`UX-574`). The
guide's own `| head -2` prints a `BrokenPipeError` traceback and
exits 2 on every JSON emitter (`UX-575`). The question count is
seventeen, sixteen and thirteen in three sentences (`UX-576`). The
committed example store's own advised `bga compare @prev @last`
refuses with exit 6 because the pair is cold + incremental — the
refusal is right and the advice is wrong (`UX-577`). Five verbatim
blocks drifted without a label (`UX-578`), and the docs guard checks
command words, never flags (`UX-579`).

### Design

Every direction's decomposition landed, and the declines that were
argued are stated out loud — the stat-card dashboard, the drawer
twice, remote execution "deliberately unfiled". What has no
vocabulary is the tail that is neither: D8's explain-path for
compare and D9's queue seam, capacity model and cost translation have
no filing and no decline (0 files for their key phrases); D10's item
5 is "a tag" and `git tag` lists none; D11's table says four
`bga:distribution` sites where the schema has one. A direction has a
Serves line and no Status line (`UX-581`). `roles.md` still says
"nothing aggregates across builds" of R5 and "nothing speaks about
variance" of R7, two rounds after `store-aggregate/v1` shipped
min/median/p95/max/MAD per host class (`UX-580`). The styleguide is
still the law — 31 guard files, 539 passed — and its own §7 ledger
says "none with a guard yet" of seven sections guarded since rounds
59-70 (`UX-582`). The round-history table has no row for round 81,
links rows 25 and 26 to `round-24.md`, and misses two named walks
(`UX-583`).

### The process layer

CI matches every document that describes it. The register holds: 66
of 66 Outcomes since `UX-497` fit the cap, median 77 lines. What
drifted is thirteen numbers in unguarded prose — `analyze/v2` in
§3.7 against v5, a small tier at 11 s that runs 22 s, "421 task
files" in the researcher agent (`UX-471` removed the same figure
from `CLAUDE.md` only), "380 files", "fourteen questions", "twelve
contracts", a 34 KB guide at 38 KB (`UX-584`). The rules card's guard
column: of twelve named guards eight assert their rule, three assert
adjacent tooling, one names a file with no such clause; the card
guard checks that eight cells are filled (`UX-585`). And the process
bands tool reads "premise false" as a regex and finds 0 % in a round
whose title says seven (`UX-586`).

## Filed

Twenty-four, in five groups. Specification: `UX-563`..`UX-568`.
Architecture and pipeline documents: `UX-569` (the prose its guards
do not read), `UX-570` (the capture workflow document), `UX-571` (the
ingestion facts' `bst` version), `UX-572` ("by construction"),
`UX-573` (the context map cannot see below `tools/` or inside
`bga/viewer/`). User guides: `UX-574` (invalid arguments exit 2),
`UX-575` (a documented pipe tracebacks), `UX-576` (the question
count), `UX-577` (the example's own next step refuses), `UX-578`
(verbatim blocks neither dated nor fresh), `UX-579` (the docs guard
reads words, not commands). Design: `UX-580`..`UX-583`. Process:
`UX-584` (thirteen stale figures), `UX-585` (the card's guard column),
`UX-586` (the premise detector). And one skill, landed in this round:
`review` — the checklist as commands, so the next review of this
kind starts from the unguarded sentences rather than from line 1.

## Standing

Verified and not filed: the README's 30-second start byte-identical
to a fresh run; 63 of 63 documented flags; the CHANGELOG's contract
state and every bump since 0.3.0; CI matching every document that
describes it; the trace dictionary exact to the emitter; the
register holding at a median 77 lines. This review lands as Review
13 in the architecture-review log at 560 closed rows, 23 since
Review 12. The round's own cost: seven researcher runs (two re-run
after a session-limit cut), ~665k tokens between them.
