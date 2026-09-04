# UX-652: the currency guard resolves to a day, and a day holds three rounds

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-247, UX-604, UX-620 (the three rounds that built and narrowed this guard) | **Found by:** architecture review 16 | **Serves:** a reader deciding whether to trust `architecture.md` | **Topic:** docs

## Motivation

`test_the_verification_log_is_true.py` asks whether the architecture
document's newest Verification Log entry is stale. Its comparison is
`stale(claimed, last) == claimed < last` — two `datetime.date`s. When
`UX-247` filed it the drift it caught was **five days** wide, so a day
was resolution enough. It is not now:

```console
$ python3 - <<'PY'
import sys; sys.path.insert(0, "tests/unit")
import test_the_verification_log_is_true as v
claimed, item, _ = v._claimed()
print("claimed:", claimed, "credits:", item)
print("_last_commit():", v._last_commit())
print("stale():", v.stale(claimed, v._last_commit()))
PY
claimed: 2026-09-04 credits: UX-629
_last_commit(): 2026-09-04
stale(): False
```

Green. Measured against what actually landed on that one day, with the
guard's own exclusion applied:

```console
$ python3 - <<'PY'
import subprocess, sys
sys.path.insert(0, "tests/unit")
import test_the_verification_log_is_true as v
day = str(v._claimed()[0])
rows = [ln for ln in subprocess.run(
    ["git", "log", "--date=short", "--format=%ad %H", "--",
     "docs/design/architecture.md"],
    capture_output=True, text=True).stdout.splitlines()
    if ln.startswith(day)]
subs = [ln for ln in rows if not v._only_a_derived_figure_moved(ln.split()[1])]
print(f"commits touching the document on {day}: {len(rows)}")
print(f"of which substantive (not excused by only_the_count_moved): {len(subs)}")
PY
commits touching the document on 2026-09-04: 26
of which substantive (not excused by only_the_count_moved): 9
```

Three of the nine are *after* the commit the newest entry credits
(`9beda27`, `UX-629`), and one of them is `UX-641`, which changed the
contract table's headline id from `analyze/v5` to `analyze/v6`, added a
superseded `analyze/v5` row, and moved "The last nine" to "The last
ten". The entry a reader is given as the document's currency record
describes a table that has since been rewritten, and the guard cannot
say so, because both dates are `2026-09-04`.

Review 14 found this guard's window too wide (`UX-604`); review 15
found its exclusion needed measuring (`UX-620`) and closed by saying
*"item 5's own command no longer answers item 5's question."* This is
the third round on the same instrument and the first that names the
resolution as the reason.

The rate is the argument, not the incident: this repository lands three
rounds in a day, and a comparison whose unit is a day cannot see two of
them.

## Required Fix

The comparison is made in the unit the tree moves in — the **commit**,
not the date. The entry already names the item it credits
(`(after \`UX-NNN\`)`), and that item's closing commit is resolvable,
so "is the newest entry behind the document?" becomes "did a
substantive commit touch this document after the one this entry
credits?", with `only_the_count_moved` unchanged as the exclusion.

Where the credited item cannot be resolved to a commit, the guard
declines and says so, the way `_last_commit` already declines at a
graft boundary — a clone that cannot answer must not be reported as
answering. `test_a_guard_that_reads_history_declares_its_depth.py`
(`UX-637`) is the standing rule for that.

## Out of Scope

- The date on the entry. It stays: a reader wants it, and it is not
  what the comparison should turn on.
- `only_the_count_moved` and its width, measured and held by
  `TestTheExclusionIsNarrow` — this row changes what is compared, not
  what is excused.
- The judgement half `UX-247` declined. What was re-grounded, and
  against what, still cannot be checked mechanically.

## Acceptance Test

With the newest entry crediting `UX-629` and `UX-641`'s commit after it
in this document's history, the guard is **red**, naming the item and
the commits that landed after it. Adding an entry that credits the
newest substantive commit turns it green. Mutation: excusing a
substantive commit reddens `TestTheExclusionIsNarrow`.

## Outcome (round 89, 2026-09-04) — 🟢 Done

**Premise held, and the figures moved under it.** Re-measured at
`933de24`, the Motivation's own commands: `claimed 2026-09-04 credits
UX-629`, `_last_commit() 2026-09-04`, `stale() False`. The day census
is **27 commits, 10 substantive** now, not 26/9 — `cb0c31e` (review 16)
landed after the row was filed.

### What the entry crediting `UX-629` was wrong about

```console
$ python3 -c "from bga import contracts; print(len(contracts.ids()),
      len(contracts.superseded()), len(contracts.unprintable()))"
25 10 16
```

The entry says **24 emitted ids, 9 of them superseded**, 15 unprintable.
`UX-641` published `analyze/v6` and superseded `analyze/v5` on the same
day, after `9beda27`. Three stale figures the date comparison read as
current.

### The Acceptance Test

Red first, on the state the item was filed against, naming the item and
the commits:

```text
E   AssertionError: the Verification Log's newest entry is dated 2026-09-04
E   and credits UX-629 (9beda27); 4 substantive commit(s) have changed
E   architecture.md since:
E     cb0c31e Architecture review 16, and the six rows it filed
E     ffb7ac3 Merge branch 'worktree-agent-aa009447aa99dfd85' into …
E     6235fc9 UX-641: a level names its members, not the row number
E     e6400a1 Merge UX-628, UX-629: the contract prose goes down to the key…
1 failed, 13 passed in 0.53s
```

Green once the entry crediting `UX-652` is added **and this commit
exists** — the anchor resolves to it and the skip goes with it:

```text
$ python3 -m pytest tests/unit/test_the_verification_log_is_true.py -q -rs
tests/unit/test_the_verification_log_is_true.py ..................
18 passed in 0.43s

$ python3 -c "…; print(item, v._closing_commit(item), v._landed_after(a))"
credits UX-652 -> this commit | landed after: [] | stale: False
```

Before it, the same run is `17 passed, 1 skipped` on `NO_HISTORY`: the
entry credits an item whose commit is not written yet.

### Mutations verified red and reverted (6)

| # | mutation | reddened | run |
|---|---|---|---|
| M1 | `stale()` → `return False` | `…_the_filed_reproduction_is_stale` | 1 failed 16 passed 1 skipped |
| M2 | `_landed_after` range `<anchor>..HEAD` → `<anchor>` | `…_reproduction_is_stale`, `…_newest_change_leaves_nothing_after_it` | 2 failed 15 passed 1 skipped |
| M3 | `closing_commit` → `matched[0]`, the newest match | `…_the_oldest_match_wins`, `…_resolves_to_the_commit_that_closed_it` | 2 failed 15 passed 1 skipped |
| M4 | the subject pattern loses its prefix and its `:` | `…_the_id_first_is_the_close`, `…_a_longer_id_is_not_this_one` | 2 failed 15 passed 1 skipped |
| M5 | M4 plus `.match` → `.search` | `…_a_merge_naming_two_items_closes_neither`, `…_a_longer_id_is_not_this_one` | 2 failed 15 passed 1 skipped |
| M6 | `_only_a_derived_figure_moved` → `True` for every commit | `…_the_clause_below_has_commits_to_compare`, `…_reproduction_is_stale` | 2 failed 15 passed 1 skipped |

M3 is the one worth reading: `matched[0]` reddens against **real**
history as well as the fixture, so a later commit naming the id does
walk the anchor forward if nothing holds it.

### Deviation from the Required Fix

- **The decline reuses `NO_HISTORY`** rather than coining a reason.
  `UX-449`'s census incident is a second wording for one absence, and
  a clone that cannot resolve the credited item's commit has the same
  absence a graft boundary has. No `KNOWN_SKIP_REASONS` entry moved.
- **The decline fires while the entry is being written**, because the
  commit it credits does not exist yet — so this file skips once on the
  author's machine and asserts on every run after. Measured above.
- `_last_commit()` is gone; nothing else called it. The exclusion,
  `only_the_count_moved` and `TestTheExclusionIsNarrow` are untouched,
  as Out of Scope asks.
- Not closed here: `README.md` is the orchestrator's this round.
