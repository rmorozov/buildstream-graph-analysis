# UX-1351: the run ledger prices a run, at its model's version and card

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Blocks:** UX-1040 | **Found by:** the Haiku 5.5 workflow review, 2026-10-10 — Ruslan in the project thread, 15:45 ("yes, yes, yes" to the trial, this row and two roles) | **Serves:** every model decision the ledger is read for | **Topic:** guards | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_the_ledger_prices_a_run.py`

## Motivation

`docs/audits/agent-runs.md` records fresh tokens (input plus cache
creation) and the model family. That is not a bill, and it cannot
compare models:

- cache reads are left out, and they are most of a long agent's price;
- Haiku 5.5 bills a response whose prompt passes 100K tokens at five
  times its short rate, which a token count cannot show;
- `sonnet` pools Sonnet 5 with 5.5 (`_model_short`);
- an advisor's consult is billed inside the executor's response, at the
  advisor's model.

UX-1040's trial adopts a model by cost per merged, unheld row. On this
column that cost would be a proxy.

## Required Fix

`dev_track_cost.py` prices each response at its own `message.model`
from Claude Code's billing table: input, output, five-minute and
one-hour cache writes, cache reads, Haiku's long-prompt card, and
advisor iterations at their own model. A model with no row in the
table is unknown, never zero. `--ledger` writes the model's version
(`sonnet-5-5`) and a `cost` cell after `wall`. Every existing row gets
`—` in the new cell. The ledger's readers (`dev_process_bands.py`,
`dev_retro.py`) take both widths. A row only widened by this change is
not a new run to the retro.

## Out of Scope

Re-pricing historical rows: their transcripts are gone. The round
documents' `## Agents` tables.

## Acceptance Test

The 2026-10-10 probe transcripts price to Claude Code's own `costUSD`
for them, to the cent. The guard's mutations each redden it.

## Outcome (2026-10-10) — 🟢 Done

**Premise:** held. The rates are Claude Code 2.1.296's own table
(`pricing:"tier_2_10_cache_read_0_10"` for Sonnet 5.5, `haiku_55` with
`long_prompt: {above_prompt_tokens: 1e5}`), not the claude-api skill's,
which still gave Sonnet 5.5 reads at $0.20.

### The gap, measured

The probe's Sonnet verifier: the ledger's quantity read 28k; the bill
was $0.1636, of which $0.0218 was 217,892 cache reads it never counts
and $0.1108 one-hour writes it counts at no rate.

### After

```text
$ python3 tools/dev_track_cost.py <probe: sonnet verifier> | tail -1
priced: $0.16          # Claude Code costUSD 0.1636
$ python3 tools/dev_track_cost.py <probe: haiku verifier> | tail -1
priced: $0.02          # costUSD 0.0168 (0.0167 less a 0.0001 title call outside the transcript)
$ python3 tools/dev_track_cost.py <probe: sonnet + Fable advisor> | tail -1
priced: $0.64          # costUSD 0.00507 + 0.1079 + 0.5252 (the consult)
$ pytest -q -p no:xdist tests/unit/test_the_ledger_prices_a_run.py \
    tests/unit/test_the_ledger_row_is_the_transcript_s.py
18 passed
```

Every one of the 844 rows reads `—` for cost. The retro drops an added
row whose nine cells a removed row in the window already had.

### Mutations verified red and reverted (7)

| # | mutation | reddened |
|---|---|---|
| A1 | Haiku's long card never selected | `test_a_prompt_over_100k_is_five_times` |
| A2 | Sonnet 5.5 reads at $0.20 | `test_sonnet_5_5_reads_at_ten_cents`, the row's `$2.20` |
| A3 | advisor iterations skipped | `test_the_consult_is_priced_at_the_advisors_model` |
| A4 | the retro's removed-row set unused | `test_widening_every_row_adds_no_retro_finding` |
| A5 | `ledger_runs` never reads cost | `test_a_ten_cell_row_is_costed_and_a_nine_cell_row_is_not` |
| A6 | one-hour writes priced as five-minute | two, incl. `test_a_five_minute_write_is_cheaper_than_an_hour` |
| A7 | the model cell back to the family | three, incl. `test_the_model_column_is_the_records_model` |
