# UX-710: a ledger row is derived from the transcript, not typed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-525 (the transcript reader), UX-666 (the ledger) | **Serves:** the session that types a row from the harness's usage line and gets the tokens right and the wall wrong, or the reverse | **Topic:** docs | **Shape:** bounded

## Motivation

Every row in `docs/audits/agent-runs.md` was typed from the
notification's usage line; round 93's researcher row says 62k and the
transcript's own sum says 58.5k. The transcript carries the agent
name, the model, the wall, the responses, the tool calls and the
fresh tokens; only the task, the outcome and the friction are the
session's to write.

## Required Fix

`tools/dev_track_cost.py --ledger <transcript> --task "…" --outcome "…"
--friction "…"` prints the row in the ledger's column order, with the
model read from the transcript's records and the tokens as the tool
already defines them; `--root` finds this harness's transcripts (the
`tasks/*.output` files, which `--list` does not see today).

## Out of Scope

- Appending to the ledger — the row is pasted where the round puts
  it; a tool that edits an audit document is a second author.

## Acceptance Test

`--ledger` on round 94's researcher transcript prints
`| 94 | researcher | sonnet | … | 145k | 76 | 11.4 m | complete | … |`
with the tokens from the sum; mutation: the model column read from
the frontmatter instead of the records — a transcript on another
model prints the wrong word and the guard reddens.
