# UX-1370: a merged track is verified whatever agent type ran it, and for every row it names

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the workflow review of 2026-11-01 (project thread "Review and optimize the agentic workflow"), reading round 175's ledger rows | **Serves:** every round's tracks, and the rule that a verifier reads them before they merge | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_merged_track_names_its_verifier.py`

## Motivation

Round 175 merged ten rows from four tracks with no verifier row, and
main stayed green. The guard counts a row only when its agent cell is
`implementer` and its outcome says `merged`. Round 175's sessions could
not launch the repo's agents (a project-thread session starts above the
repository, so `.claude/agents` does not load), ran `general-purpose`
agents briefed as implementers, wrote "complete", and named two or three
rows per track while the guard paired only the first id.

## Decomposition

Input classes: an `implementer` agent row; a `general-purpose` row whose
task cell opens `implementer`; a reverted or rejected track; a track
naming several ids; a round before and from the widening.

## Required Fix

From round 176, a track is any row whose agent is `implementer` or whose
task cell opens `implementer`; it is merged unless its outcome says
reverted, not merged, rejected or abandoned; and every id it names needs
a same-round verifier row. Rounds 104-175 keep the old reading.

## Out of Scope

Verifying round 175's rows after the fact, and re-reading rounds 104-175
under the wider rule; both are counted below for the owner. Making the
repo's agents load in a thread session is `UX-1371`.

## Acceptance Test

The wider reading on a synthetic ledger reports exactly the unpaired id
of a two-id `general-purpose` track, and not a reverted track or a
round-175 row; the real ledger stays green. Mutation: drop each clause;
its test reds.

## Outcome (2026-11-01)

Gap measured on `d9b25851` against `docs/audits/agent-runs.md` (scratch
script: every row from round 104 whose agent is `implementer` or whose
task cell opens `implementer`, ids paired against same-round verifiers):

```text
(agent, outcome says merged, an id unpaired)    rows
('general-purpose', False, True)                   4   <- round 175, nine ids
('implementer',     False, False)                 98
('implementer',     False, True)                 103   <- rounds 142-166: "see round-NNN", "complete", "VERIFIED"
('implementer',     True,  False)                203
```

The guard read 203 of 408 track rows. The 103 unread `implementer` rows
are history and stay under the old reading: their verifiers are recorded
in round documents, not in this ledger, so a wider reading would red on
bookkeeping rather than on missing verification. Round 175 is the one
round with no verifier anywhere.

Close: `python3 -m pytest -q tests/unit/test_a_merged_track_names_its_verifier.py`
reads `3 passed`. Mutations, with `PYTHONDONTWRITEBYTECODE=1` (a
same-size edit in the same second reuses a stale `.pyc`):

| mutation | red |
|---|---|
| a track is only an `implementer`-agent row | 1 failed, 2 passed |
| only the first id is paired | 1 failed, 2 passed |
| a reverted track counts as merged | 1 failed, 2 passed |
| the widening starts at 175 | 2 failed, 1 passed (the real ledger's round 175: nine ids) |
