# UX-652: the currency guard resolves to a day, and a day holds three rounds

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-247, UX-604, UX-620 (the three rounds that built and narrowed this guard) | **Found by:** architecture review 16 | **Serves:** a reader deciding whether to trust `architecture.md` | **Topic:** docs

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
