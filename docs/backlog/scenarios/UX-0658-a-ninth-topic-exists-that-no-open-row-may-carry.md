# UX-658: a ninth topic exists that no open row may carry

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-232 (which made the taxonomy a closed set), UX-507 (which classified the topic-less rows) | **Found by:** round 89, filing UX-657 and being refused a topic the index already prints | **Serves:** anyone filing a row and choosing what to put in its Topic cell | **Topic:** guards

## Motivation

`UX-232` made the topic a **closed set** so the index could be counted.
The set is written down three times, and they no longer agree:

```console
$ python3 - <<'PY'
import re, pathlib, sys
sys.path.insert(0, ".")
from tools import dev_close_task as d
guard = pathlib.Path(
    "tests/unit/test_docs_links_and_commands.py").read_text(encoding="utf-8")
block = guard.split(
    "def test_every_open_row_carries_a_topic_from_the_closed_set",
    1)[1].split("path =", 1)[0]
in_guard = set(re.findall(r'"([a-z-]+)"', block))
declared = {}
for path in sorted(pathlib.Path("docs/backlog/scenarios").glob("UX-*.md")):
    found = re.search(r"\*\*Topic:\*\*\s*([a-z-]+)",
                      path.read_text(encoding="utf-8"))
    if found:
        declared.setdefault(found.group(1), []).append(path.name)
print("the guard's hardcoded set    :", len(in_guard), sorted(in_guard))
print("TOPIC_ORDER in the tool      :", len(d.TOPIC_ORDER))
print("topics the task files declare:", len(declared), sorted(declared))
for topic in sorted(set(declared) - in_guard):
    print(f"  declared, but no open row may carry it: {topic!r} "
          f"-> {declared[topic]}")
PY
the guard's hardcoded set    : 8 ['analysis', 'capture', 'cli', 'contracts', 'docs', 'guards', 'store', 'viewer']
TOPIC_ORDER in the tool      : 8
topics the task files declare: 9 ['analysis', 'capture', 'cli', 'contracts', 'docs', 'guards', 'process', 'store', 'viewer']
  declared, but no open row may carry it: 'process' -> ['UX-0656-main-is-red-a-closed-outcome-is-eight-lines-over-the-cap.md']
```

`process` reaches the index's topic table — the table is derived from
what the files declare, and `TOPIC_ORDER`'s comment says anything not
listed sorts after the eight — so a reader of `README.md` sees a
`process` row and reasonably concludes it is a topic they may use. It
is not:
`test_docs_links_and_commands.py::test_every_open_row_carries_a_topic_from_the_closed_set`
holds open rows to a hardcoded eight and refuses it.

`UX-656` is why nothing noticed. It was filed and closed inside one
round, so its row was written into `closed.md` and never sat in the
open index the guard reads. A topic entered the vocabulary through the
one path that is not checked.

The derived half is right and the two hand-written halves are the
copies — which is `UX-131`'s shape, one document up from where
`UX-657` just found it in the priority column.

## Required Fix

One statement of the set. The natural home is `TOPIC_ORDER` in
`tools/dev_close_task.py`, which the index table already orders by and
which `UX-387`'s rule points at: the tool and the suite hold one
property by one reading. The guard imports it rather than repeating
it, and a topic a task file declares that the set does not name is a
failure with the file's name in it.

Then decide `process` on the measurement rather than by default: it is
one row today, and either it joins the set or `UX-656` is
reclassified into one of the eight. Whichever is chosen, the index and
the guard say the same thing afterwards.

## Out of Scope

- Reclassifying the other 654 rows — `UX-507` did that work against
  the set as it stood, and this row disputes where the set is written,
  not what is in it.
- The `Priority` pair — `UX-657`, filed in the same round and the same
  shape one column over.
- Whether a closed row should be checked for its topic at all. Declined
  because widening the population is a change of scope that would want
  its own measurement of how many closed rows would fail.

## Acceptance Test

The guard reads the set from one place; adding a task file with a
topic outside it reddens naming that file, and the index's topic table
and the guard's set cannot disagree because there is only one of them.

## Outcome

**Premise:** held. `TOPIC_ORDER` is the one statement of the set,
`test_docs_links_and_commands.py` imports it instead of repeating it,
and `topic_disagreements()` is `--check`'s seventh property. With
`UX-656` as filed, it names the file:

```console
$ python3 tools/dev_close_task.py --check
  ok    every row's status glyph matches its task file's
  ok    every row's priority matches its task file's
  FAIL  every task file's topic is one the closed set names - 1 problem(s)
          UX-0656-main-is-red-a-closed-outcome-is-eight-lines-over-the-cap.md:
          topic 'process' is outside the closed set ['analysis', 'capture',
          'cli', 'contracts', 'docs', 'guards', 'store', 'viewer']
1 problem(s) over 7 propert(y/ies), 657 backlog row(s)
```

**Widening to closed rows cost one failure, so it was taken.** The
population is the task file, which declares the topic, and that is the
path `UX-656` took. One script, read twice, the second with `UX-656`
reverted to `process`:

```text
task files: 657 | no header: 0 | open rows: 2 | closed rows: 655
outside TOPIC_ORDER: 0
outside TOPIC_ORDER: ["UX-0656-...: topic 'process' is outside ..."]
```

**`process` does not join the set; `UX-656` is `guards`.** The
neighbours decided it, not taste — the other `main is red` row, the
row that set the cap `UX-656` broke, and `UX-657`, which was filed
`process` and reclassified for the same reason:

```console
$ grep -o '\*\*Topic:\*\* [a-z-]*' docs/backlog/scenarios/UX-0497*.md \
    docs/backlog/scenarios/UX-0644*.md docs/backlog/scenarios/UX-0657*.md
UX-0497-the-register-is-a-budget.md:**Topic:** guards
UX-0644-main-is-red-a-map-entry-under-the-cap-widened-a-module.md:**Topic:** guards
UX-0657-the-priority-column-has-no-guard.md:**Topic:** guards
UX-0657-the-priority-column-has-no-guard.md:**Topic:** process
```

`UX-656` says of itself that it "is the same shape as `UX-644`"; a
ninth topic would carry one row against a smallest member of 16. The
fourth line is `UX-657`'s Outcome *arguing* about `process` — the next
clause.

**The header is the subject, the Outcome is the argument.** Two files
quote a `**Topic:**` line below line 8, one of them `process`, so both
readers take the first 8 lines — `file_statuses`' bound. Under a
whole-file read, deleting `UX-657`'s header made the guard report that
file as *declaring* `process`: a wrong name, not a missing one.

**Mutations.**

| mutation | expected | got |
|---|---|---|
| `UX-656` back to `**Topic:** process` | red, naming the file | red: "topic 'process' is outside the closed set" — 1 failed, 2 passed |
| `UX-644`'s `**Topic:**` header deleted | red as a *missing* header | red: "no `**Topic:**` header: ['UX-0644-...']" — 1 failed, 2 passed |
| `TOPIC_ORDER` `guards` → `guardrails` | red, printing the tool's set | red: "outside the closed set [...'guardrails'...]: ["UX-658: 'guards'"]" — 2 failed, 1 passed |
| `file_topics()` narrowed to the open index | `--check` misses a planted closed row | red: the topic property printed `ok` — 1 failed |
| the guard given its own copy of the set | red on the one-reading clause | red: `guard._TOPIC_ORDER is close.TOPIC_ORDER` — 1 failed |
| the header bound dropped | red, and with a wrong name | red: `_header_topic(...)` returned `'process'` — 1 failed, 3 passed |
| all six reverted | green | 4 passed, 51 deselected |

Every revert was a `cp` from the scratchpad snapshot (`UX-625`).

**Deviation.** A **fourth** copy of the set is in
`tools/bga_release_notes.py:36` — the same eight in a release-body
order, sorting an unlisted topic after them as the index did. Left
alone; it wants its own row.
`--check` reports the index's topic table as behind (`guards`
136 → 137, no `process` row); the index belongs to the round's gate,
so `--check --write` is left to it, and until it runs three clauses in
`test_the_loop_stays_fast.py` and one in
`test_the_fast_check_holds_what_the_suite_holds.py` are red for that
reason alone — committed with `BGA_SKIP_SELECTOR=1`, which is the case
that hook names. Against a copy of this tree with the index derived,
all seven properties are `ok` and `--check` exits 0.
