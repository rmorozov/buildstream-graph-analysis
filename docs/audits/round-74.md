# Audit round 74: the workflow, measured — and given a register

Run on 2026-09-01, after the sibling's rounds 65-73 (163 commits,
`UX-411`..`UX-496`, architecture reviews 7-10, three rounds of
self-audit and two of process work — `UX-424`'s tokenising hook,
`UX-426`'s CI loop, the researcher and verifier agents). The brief:
deduce the agents' workflow from what the repository holds, and
brainstorm how to make it faster and lighter — the slow-down as tests
grow, decomposition into parallel tracks, test analysis as a practice,
a lightweight lifecycle for a project this size, context economy, and
the sibling's register.

## The workflow, as the repository states it

Deduced from `CLAUDE.md`, three hooks, four skills, two agents, eleven
dev tools, eight CI jobs and the fixing guide's eight streams:

```text
entry     CLAUDE.md (3.3 KB, ≤ 80 lines, guarded) → fixing guide (34 KB, "read this first")
pick      README row → task file → cited line ranges only
loop      edit → make test-touching (4 s) → falsify each new guard → make test → lint
close     Outcome (skeleton from dev_close_task) → --move → two markers, two counts
gates     hooks: no bulk add (tokenised), no unconditional skip, ruff on the edited file
          CI: pull_request + main only (UX-426); drift gate on CI's own clock (UX-420/442/447)
helpers   researcher (read widely, return conclusions) · verifier (fresh window, report only)
streams   design · audit · feature · fix · documentation · refactor · review · release
```

It is a serious process, and its instruments are honest about their
own limits (`UX-426` refuses to promote an unmeasured loop). What it
does not have is a step *before* the first edit, a budget on what a
session reads and writes, and a unit of work larger than one item.

## What it costs, measured

```text
make test, this container, -n auto, bst tier on   5,635 passed · 81 skipped · 328 s (5m30s)
  as documented: CLAUDE.md 4m45s · verify skill and guide 3m15s      both stale
read before the task file: CLAUDE.md + guide + 3 skills             60,328 B
task file, UX-0440..0496                        median 8,452 B · max 19,169 B
Outcome section, same range                     median 114 lines · max 284
module docstrings, tools/dev_*.py + hooks       8 of 11 over 25 lines; max 85
tools/dev_tier_drift.py                         206 comment lines over 46 of code
since round 64: tests +20,972 · backlog docs +19,777 · code +8,196 lines
commits per closed task, rounds 66-73           51 × 1 · 16 × 2 · 9 × 3 · 1 × 4
housekeeping commits (CI reference, re-tier, index)   19 of 162 (12 %)
```

Two readings. **The gate is per item and the suite is 5.5 minutes**,
so 77 closed items imply at least 77 suite runs; nobody has measured
whether the runs between the first and the last of a batch find
anything `test-touching` plus the item's own mutations did not. And
**the register is the context cost**: tests and task files grew five
times faster than code, every byte of it read again by every later
session, and no document states a budget.

## What this round changed

Three items implemented and closed, in one commit each:

- **`UX-497` — the register is a budget.** `CLAUDE.md` gains a
  Register section (docstring ≤ 25 lines, Outcome ≤ 80 lines, a
  comment is one line of why, a commit body ≤ 8 lines) at exactly the
  80-line guard, and `test_the_register_is_terse.py` holds the tree
  to it with a grandfather table that may only shrink. Five
  mutations, five reds.
- **`UX-498` — `decompose`.** The step before the first edit:
  surfaces derived by four commands, the partition table (six input
  dimensions with the item that bit on each boundary — the test
  analysis practice the round-64 plan named), tracks that are
  parallel iff surfaces are disjoint with the four shared files named,
  and the batch gate as an addition until `UX-500` measures.
- **`UX-499` — `orient`.** Ten one-command lookups below the context
  map, and the line between a lookup and a researcher sweep.

Plus the suite-time drift corrected in three documents.

## The lifecycle, sized for this project

Not a new process — the existing streams with a unit of work between
"item" and "round", and the hand-maintained parts derived:

1. **Intake** — a filing (unchanged).
2. **Decompose** — surfaces, partition, tracks, gate (`decompose`).
3. **Tracks** — parallel worktrees per disjoint surface set; an
   implementer agent per track (`UX-504`), the orchestrator owning
   the shared files.
4. **Inner loop** — `test-touching` + falsify per item (unchanged).
5. **Batch gate** — one PR opened first, one merge, one suite
   (`UX-500` measures whether it may replace the per-item suite).
6. **Close** — indexes derived (`UX-501`), a new test file recording
   itself in the CI reference (`UX-503`), an Outcome that fits the
   register (`UX-506`).
7. **Read** — the rules card (`UX-505`) as the first read; the guide
   for the rule about to be broken; the skills on demand.

The context economy follows from the same list: what is loaded every
session shrinks (card + `CLAUDE.md`), what is read per task shrinks
(register), and what is read per question shrinks (`orient`, the
researcher).

## The magic words

The durable version is the Register section, loaded every session.
The sentence to say to a session that has not read it: *"Write in
the register: one sentence of why per comment, history in the task
file not the code, docstrings under 25 lines, Outcomes under 80.
Numbers, not narrative."* The guard is what makes it stick.

## Filed

`UX-497`..`UX-499` closed; `UX-500` (the batch gate, measured — High),
`UX-501` (the index derived — High), `UX-502` (the comment that tells
the story — Medium), `UX-503` (a new test file records itself — High),
`UX-504` (an implementer agent, worktree only — Medium), `UX-505` (the
rules card — High), `UX-506` (the Outcome skeleton — Medium).

## Standing

This round ran the suite twice — once to measure it, once as its own
batch gate over three closed items — which is the regime `UX-500`
proposes to measure, on a sample of one. The nine items the sibling
left open (`UX-489`..`UX-496`, `UX-92`, `UX-96`) are untouched.
