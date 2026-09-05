# UX-710: a ledger row is derived from the transcript, not typed

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-525 (the transcript reader), UX-666 (the ledger) | **Serves:** the session that types a row from the harness's usage line and gets the tokens right and the wall wrong, or the reverse | **Topic:** docs | **Area:** tools | **Shape:** bounded

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

## Outcome

**The gap, measured.** No `--ledger` flag; `--list`/`--root` only
globbed `subagents/*.jsonl`, so `tasks/*.output` (this harness's own
transcripts) were invisible. `--list --root
/tmp/claude-0/…/0cafe15a…` also crashed on 51 non-JSONL
`tasks/*.output` files (bash-tool stdout, not transcripts) before the
fix.

**The close, measured.** The transcript whose tool-call count (76) and
wall (11.4 m) match round 94's typed row
(`subagents/agent-abce6db681bf713cf.jsonl`) prints:

```text
| 94 | researcher | sonnet | the stages as documented, the ledger by model | 139k | 76 | 11.4 m | done | a batch commit closes many ids |
```

139k derived
against 145k typed, the same kind of gap the Motivation names for
round 93 (58.5k vs 62k). `--list --root` on a synthetic `tasks/x1.output`
whose first line names `UX-999` now finds it.

**Mutations.**

| mutation | reddened | count |
|---|---|---|
| `_agent_and_model` returns a hardcoded `"claude-sonnet-5"` | `test_the_model_column_is_the_records_model`, `test_a_different_model_prints_a_different_word` | 2 failed, 2 passed |
| swap the `model`/`agent` cells in `ledger_row`'s format string | `test_the_row_has_nine_cells_in_header_order` | 1 failed, 3 passed |
| drop the `JSONDecodeError`/non-dict guard in `implementer_transcripts` | `test_the_transcript_is_named_and_the_plain_text_is_not` | 1 failed, 4 passed |

**Deviation.** The tokens column carries the tool's fresh figure, which reads low by the last response's output that no later turn re-enters (139k against the harness's 145k for round 94's researcher); the ledger's header says so from this round on.
