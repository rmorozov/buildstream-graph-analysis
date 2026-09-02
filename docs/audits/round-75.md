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
Regime A — the regime this round actually ran, per the correction under
the figures below. It records this round's figures and stays open; the
row says so rather than being closed on one sample.

**gate:** one PR, opened before the first commit (`UX-426`, `verify`
§7), so every push collects a CI run instead of the batch collecting
one. `make test` once per batch of independent items, and — until
`UX-500` decides otherwise — also before any item is marked done.

## Decomposition — the round-73 tail

Same derivation, same four shared files. `tests/tiers.py` is in
`dev_touching.EVERYTHING`, so a track that edits it selects all 398 test
files — one more reason it is the orchestrator's.

| item | surfaces | guards (input classes) | track |
|---|---|---|---|
| `UX-491` | `tools/dev_tier_drift.py` (where the summary is printed) · `.github/workflows/ci.yml` | `test_the_candidate_reaches_a_log.py` · `test_a_slow_file_says_which_file.py` (reader: log tail only · artifact available) | **gate track, first** — it is the instrument `UX-495` reads |
| `UX-495` | none yet; a measurement. Readers are `tests/tiers.py` (shared) and `CI_DRIFT_FACTOR` | `test_the_tiers_are_a_partition.py` (host: CI only, §7 — no local instrument at `-n auto` on 4 cores) | **gate track, after `UX-491`** |
| `UX-496` | `tools/dev_tier_drift.py` (reference shape) · `tests/ci_reference.json` (shared) · `.github/workflows/ci.yml` | `test_a_slow_file_says_which_file.py` (entry: one sample · N samples · a range) · `test_a_candidate_is_confirmed_alone.py` | **gate track, after `UX-495`** — the range it sizes against is what `UX-495` measures |
| `UX-489` | `tests/unit/test_the_journey_has_an_answer_key.py` | itself (margin: leader beyond spread · leader inside spread) | parallel — one file, no other item names it |
| `UX-490` | `tests/unit/test_a_guard_reads_only_what_a_clone_has.py` | itself (path: relative-tracked · relative-untracked · absolute-untracked-exists · absolute-absent · `tmp_path`-derived · escaped) | parallel |
| `UX-492` | `README.md` | `test_the_readme_block_is_the_real_output.py` · `test_the_front_door_is_current.py` · `test_docs_examples.py` | parallel |
| `UX-493` | `docs/backlog/scenarios/UX-0479-*.md` · `tools/dev_close_task.py` (a mechanical §3.6 check) | `test_docs_links_and_commands.py` · `test_the_loop_stays_fast.py` | parallel — `dev_close_task.py` is free again once the block above lands |

**gap — `UX-492`'s real-run class has no host.** Re-running the
freedesktop-sdk capture needs a 3614-second build this container cannot
perform and CI will not either; that leaves "say which release produced
it", which the Required Fix already admits. Recorded here so the choice
is a measurement of what is available, not a preference.

**gap — `UX-495` is CI-only** (fixing guide §7). Four local cores at
`-n auto` are not the runner's, so the spread has to be read off runs,
not reproduced. `UX-491` exists so those runs can be read at all.

**gate:** the same PR. Four items are parallel and three are one serial
track, so this is the batch where `UX-504`'s `implementer` agent has
something to run — and the end-to-end track measurement its Acceptance
Test is still missing.

## The parallel batch, measured — `UX-504`'s first real use

Three `implementer` tracks (`UX-490`, `UX-492`, `UX-493`) ran at once
in worktrees while this session took the gate track. What it cost, from
the run itself rather than from the design:

| | |
|---|---|
| tracks | 3, one item each |
| agent wall clock | 943s · 996s · 1,174s, overlapping — ~20 min for three items |
| agent tokens | 81k · 123k · 131k |
| merge | 3 cherry-picks, **1 conflicted** (`dev_close_task.py`, `test_the_loop_stays_fast.py`) |
| commits per task | **1.33** — one per track, plus one close commit for all three |
| defects the regime itself produced | **2**, `UX-509` and `UX-510` |

Both new defects are the *worktree*, not the work: `.claude/worktrees/`
is inside the tree the doc lint scans (`UX-509`), and all three copies
started from round 74's last commit while this session was nine commits
on (`UX-510`) — so two tracks were told to read `rules.md` and this
document, and neither existed for them. The one merge conflict is the
same cause: both files had been edited by `UX-501` and `UX-506` inside
those nine commits.

Against that, one track found something no serial pass had: `UX-492`'s
declared guard list named three existing guards and **none of them
reads the section the item is about**. A track that reports its surfaces
against the ones it was given is what surfaced that; the orchestrator
had asserted the coverage from a `dev_touching` selection, which
answers "which guards name this file", not "which guards read this
paragraph".

`UX-500`'s commits-per-task row is therefore two numbers, not one: 1.0
serial, 1.33 parallel. The extra third is the close, which the
`implementer` is deliberately not allowed to write and which the
orchestrator can do for the batch in one commit — the three items touch
`README.md` and `closed.md`, so separating them would mean splitting
hunks of two shared files for no gain.

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

And two defects this round reached `main` past a **green full local
suite**, which is a finding about the gate rather than about the
regimes: the `stale` verdict on a one-sample reference (`cdf912b` →
`UX-508`) and the `NameError` in the branch no local run took
(`ccfa81e` → run 33578729472). Neither `make test` nor any tier can
produce them here — the first needs the runner's clock, the second
needs a reference the local tree does not have. Under either regime the
count of defects only CI can find is **2**, and it is the same 2, so it
does not separate them; it does say the batch gate cannot be *CI* plus
nothing.

One round of three. `UX-500` stays open.
