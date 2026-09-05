# Audit round 90: the process, given a ledger — and the page, looked at

Run on 2026-09-05, after the sibling's rounds 83-89 (`UX-563`..
`UX-662`; the round-82 review slate closed, the track mechanics
hardened, architecture review 16). Two halves, in the order the user
set: first the process — context, the design-review workflow, what
an outsider walk costs, whether the loop learns from its own runs —
then a design review of `bga view` on a capture with every plane.

## The process, four questions

**Context and models.** Every subagent ran on the session's model
because nothing said otherwise — the agents' frontmatter carried no
`model:` and the guard enumerates no allowed set, so the line was
always legal and never written. Landed: `model: sonnet` on the two
reporters, the implementer inheriting, one advisory line in
`CLAUDE.md` (`UX-P1`). Context limits per agent do not exist in the
harness; the lever is the *shape* of what comes back, and two skills
now fix it (`UX-P4`).

**The design-review workflow.** Rounds 44, 63 and 77 judged the page
from descriptions. The `design-review` skill makes it a protocol:
one capture with every plane, seven fixed screenshots read by a
subagent that can see them (the pictures never enter the
orchestrating session), measure → judge against the styleguide § and
a short list of craft questions → propose as a rule with its guard.
Its first run is the second half of this round.

**The walk, cheaper.** Five rounds wrote the walk prompt from
scratch; round 77's control walk cost 336k tokens, most of it
re-deriving the page's census. The `walk` skill fixes the protocol
and the ≤ 80-line report; `UX-P2` makes the census a dev tool a
walker reads in two kilobytes — and a guard, so a control class or a
folding table lands declared.

**The loop, learning from its runs.** `tools/dev_track_cost.py` reads
the harness's own run records and prints them; it was used once, in
round 80, and nothing persisted a row. `docs/audits/agent-runs.md`
opens with the twelve runs this session can account for — and they
already say what the next round should know: a researcher that reads
a document whole costs 100-180k, a walker that drives every control
336k, and two session-limit cuts cost a re-run each. `UX-P3` makes
the row a habit (every agent ends with a friction line; the tool
appends) and gives the process-bands tool a runs band.

## The page, looked at

The `design-review` skill's first run: a fresh cold capture of
example 06 with the hook and the spine (816 processes, 9 elements
joined, Plane 3 reading 123 kept logs), a second warm snapshot so the
store holds two runs, the page exported and served, seven
screenshots read by the reviewer before anything was measured.

**Navigation.** The rail is 82 entries under eight uppercase
captions, three visual levels and no disclosure; sixteen entries are
visible without scrolling the rail; the scrollspy marks the current
section and never reveals it (mark at 1,305 px in an 804 px box,
`scrollTop` 0); the element list is a scrollbox inside the scrolling
rail; 302 px of apparatus sit above the first entry and the stepper
wraps to three two-line buttons once "↑ Top" appears. The user's
outline is the right object and `UX-271`'s refusal does not cover it
— that refused a payload tree; this is the chapter grouping made
foldable. Filed as styleguide §3h, the rail as a source list
(`UX-667`).

**The reader.** The select sits inside the decision box, 759 px from
the table that explains the roles; switching it promotes and folds
sections (7,484 → 21,049 px for the local optimizer) and promotion
draws nothing — `[data-promoted]` has border 0 and a transparent
background; only the folding shows it. The user's header placement
is right (§4a); five role hues are not — §4.1 forbids a categorical
series, §4.2 allows one accent, and "my content is findable" is a
shape question. Filed as §4 rule 7: the select and its question in
the header, a left rule on promoted sections, chips muted under
"anyone", zero new colors (`UX-668`).

**Next steps.** Rendered twice: the decision panel's ordered list,
and a `next_steps` section as a Why | Run | From table whose Run
cell wraps a command over three lines and whose From column shows
raw keys. The table is §1's mapping followed too literally — the
array is an ordered reason + command + citation, which no other
payload list is. Filed as §1e, a runbook is a shape: rendered once,
`follows_from` as a link labelled with the section's question
(`UX-669`).

**Readability.** Eighteen distinct computed font sizes; the h3 at
17.55 px above its h2 at 16.8; prose lines of 122-133 characters;
contrast passing everywhere (the warn tone at 4.47 on the muted
background is the one boundary case). Three sentences quoted that a
reader re-reads — the verdict with "chain-bound" three times, a
257-character card sentence with five numbers, a provenance sentence
with nested dashes and a raw `>=`. Filed as §4f, the type scale
(`UX-674`).

**Controls.** 863 controls in 184 label-normalised classes, each
driven once. Working as labelled: Prev/Next, Collapse/Expand all,
the reader select, sort, filter, threshold, Top-N and All rows —
`UX-532`'s nested-row defect holds fixed on folded cells — Expand to
table focus and back, 211 `?` doors, four copy classes, Investigate
in Perfetto, Why #n, the blast Ask, the fix checkbox, the run picker,
the questions page. Not as labelled: the first rail click into a
folded chapter lands 687 px above its section (`UX-670`); a preset
sub-entry applies its view without going there and the jump box
leaves the URL anchor stale (`UX-671`); a blocked pop-up's refusal
sentence and direct link never render and the exception is uncaught
(`UX-672`); sixteen tables offer a Top 10 they cannot fill
(`UX-673`).

## Filed

Twelve. Process: `UX-663` (reporters on `sonnet`, closed), `UX-664`
(the walk and design-review skills, closed), `UX-665` (the page
census as a tool — High), `UX-666` (the run ledger's habit and a runs
band — High). Design: `UX-667` (the rail is a source list — High),
`UX-668` (a reader is a shape, not a hue — High), `UX-669` (a runbook
is a shape — High), `UX-670` (the rail click that overshoots — High),
`UX-671` (the rail acts on the view, not the URL — Medium), `UX-672`
(the blocked pop-up's refusal — Medium), `UX-673` (Top 10 on a
three-row table — Medium), `UX-674` (the type scale — Medium).

## Agents

| agent | model | task | tokens | tool calls | wall | friction |
|---|---|---|---|---|---|---|
| researcher | main | the process and design delta since round 82 | 81k | 34 | 3 m | — |
| general-purpose | main | the design review on an all-planes page | 229k | 62 | 24 m | two real captures; three census re-runs after navigations killed the driver; `pkill -f` matched its own shell; a full-page capture blank under content-visibility |

Both launched before `UX-663` landed, so both ran on the session's
model; the ledger's next rows are the first under the advisory.

## Standing

Verified and not filed: the two-plane capture recipe in the `measure`
skill works as written (816 processes); `UX-532` holds on tables
with folded cells; the run picker, table focus and the `?` doors all
revert cleanly; the export and the served page differ only where
they should (no picker, no store section, no stray separator). The
architecture document's scenario count is re-derived by the close
tool and moved with this round's rows.
