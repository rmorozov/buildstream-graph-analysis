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

## Regime A, round 1 — the figures `UX-500` asks for

**Not Regime B.** The plan above said the batch gate would be *in
addition* until `UX-500` decides, and that is what happened: `make
test` ran before every item, which is fixing guide §3 as written. So
these are Regime A's numbers and the B column is still empty after this
round — stated here rather than relabelled, because a regime nobody ran
is not a regime measured.

| | round 75 |
|---|---|
| items closed | 7 (`UX-501`..`UX-506`, `UX-508`) |
| suite runs | 15 |
| gate wall clock | ~80 min (15 × 316-407s at `-n auto`) |
| commits per task | 1.0 |
| defects the per-item suite caught | 5 |
| **of those, ones `test-touching` would not have run** | **2** |

The last row is the number `UX-500` says decides, measured rather than
argued — `dev_touching.select` run over each commit's own diff, asking
whether the guard that caught the defect is in the set it would have
chosen:

```text
item     the guard that caught it                        test-touching?
UX-503   test_the_register_is_terse.py                   NO
UX-501   test_docs_links_and_commands.py                 yes
UX-501   test_the_agent_configuration_holds.py           yes
UX-505   test_a_guard_reads_only_what_a_clone_has.py     yes
UX-502   tests/conftest.py (UX-449's skip census)        NO
```

**Two of five would have reached the batch gate with the item already
marked 🟢** — an Outcome over the register's cap, and a skip reason the
census has never seen. Both are cheap to fix and neither is a product
defect; what they cost under Regime B is re-opening a closed row.

Three of the five *were* in `test-touching`'s set and were still found
by `make test`, which is a finding about this session rather than about
the regimes: `make test-touching` was run **before** the final edit —
the close, the Outcome, the row move — so the cheap gate never saw the
change that broke them. Regime B would not fix that; running the
selector after the last edit would.

One round of three. `UX-500` stays open.
