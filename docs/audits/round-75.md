# Round 75 — the workflow block, then the round-73 tail

Input: `UX-500`..`UX-506`, the workflow items round 74 filed, then the
seven rows round 73 left open (`UX-489`..`UX-496`, less the two it
closed). The block is taken first because every item in it pays for
itself inside this round: three of the seven describe taxes round 73
paid by hand, and the log of that round is the measurement.

## Decomposition

Derived per the `decompose` skill. One row per item; the four shared
files (`README.md`, `closed.md`, `tiers.py`, `ci_reference.json`) are
the orchestrator's, at the end, and no track touches them.

| item | surfaces | guards (input classes) | track |
|---|---|---|---|
| `UX-503` | `tools/dev_tier_drift.py` (absent → record) · `.github/workflows/ci.yml` · `verify` skill (§3.10) | `test_a_slow_file_says_which_file.py` (absent · present-and-slower · present-and-gone) · `test_the_candidate_reaches_a_log.py` | first, alone — `dev_tier_drift.py` is also `UX-502`'s largest file |
| `UX-501` | `tools/dev_close_task.py` (`--write`) · `decompose` skill §3 | `test_docs_links_and_commands.py` (counts) · `test_the_loop_stays_fast.py` | parallel with `UX-503`, `UX-505` |
| `UX-505` | `docs/contributing/rules.md` (new) · `docs/contributing/fixing-guide.md` (header) · `CLAUDE.md` | `test_docs_links_and_commands.py` (card ≤ 80 lines · every card rule has a guide anchor) | parallel |
| `UX-506` | `tools/dev_close_task.py` (`--outcome`) · `tools/dev_process_bands.py` | `test_the_process_is_measured.py` (before/after counts on the committed record) | **serial after `UX-501`** — same file |
| `UX-502` | 8 grandfathered dev tools' docstrings | `test_the_register_is_terse.py` (`GRANDFATHERED` empty) · each tool's own guard | **serial after `UX-503`** — same file |
| `UX-504` | `.claude/agents/implementer.md` (new) · agents guard | `test_the_agent_configuration_holds.py` (reporting agents cannot edit · implementer may · names the four shared files) | parallel |
| `UX-500` | `docs/audits/round-75.md` (this file) | none — it is a measurement, not a mechanism | spans the round; cannot close in one |

**gap:** `UX-500` needs three rounds per regime and this is round one of
Regime B. It records this round's figures and stays open; the row says
so rather than being closed on one sample.

**gate:** one PR, opened before the first commit (`UX-426`, `verify`
§7), so every push collects a CI run instead of the batch collecting
one. `make test` once per batch of independent items, and — until
`UX-500` decides otherwise — also before any item is marked done.

## Regime B, round 1 — the figures `UX-500` asks for

_Filled as the round runs._

| | |
|---|---|
| suite runs | |
| gate wall clock | |
| defects the batch gate caught that `test-touching` missed | |
| commits per task | |
