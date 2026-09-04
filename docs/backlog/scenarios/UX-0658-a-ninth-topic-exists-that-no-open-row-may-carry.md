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
