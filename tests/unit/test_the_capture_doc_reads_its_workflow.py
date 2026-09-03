"""UX-570: the capture document's file list and trigger sentence are
derived from the workflow, not retyped beside it.

Measured when this was filed, against
`.github/workflows/real-project-capture.yml`:

```text
files the yml writes under `capture/`      21
rows the doc's contents table named        12
named by the yml and by no row              9
crons in the yml's `schedule:` block        2   (weekly, monthly)
crons the trigger sentence named            1   ("weekly ... and on
                                                 nothing else", while
                                                 the same document's
                                                 own next section says
                                                 "the monthly cron
                                                 settled it")
```

Two guards already read this document and neither read the workflow:
`test_the_capture_directory_is_a_contract.py` checks four phrases,
`test_a_clone_without_the_archive.py` one sentence. The path to the
yml comes from `test_capture_ref_patterns.py`, which has parsed the
same file since `UX-122` - one guard's idea of where the workflow is.
"""
import pathlib
import re
import sys
from typing import List, Optional, Tuple

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_capture_ref_patterns import WORKFLOW  # noqa: E402

DOC = REPO / "docs/design/capture-workflow.md"

#: The task's own instrument: `grep -o "capture/[A-Za-z0-9._-]*"`.
CAPTURE_PATH = re.compile(r"capture/[A-Za-z0-9._-]*")
#: A backticked file name inside a table cell.
CELL_NAME = re.compile(r"`([A-Za-z0-9._/-]+)`")
CRON = re.compile(r'-\s*cron:\s*"([^"]+)"')
#: A top-level key of the `on:` block - `push`, `schedule`, ...
TRIGGER = re.compile(r"^  (\w+):", re.M)
DAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
        "Saturday")
#: Every cadence the derivation below can produce. A word in this list
#: that no cron produces must not appear in the sentence either -
#: that is the half which catches a *dropped* cron.
CADENCES = ("daily", "weekly", "monthly")


# --- the workflow half: what the yml actually says -------------------

def _workflow_files() -> set:
    """Every name the workflow writes under `capture/`."""
    text = WORKFLOW.read_text(encoding="utf-8")
    names = {token[len("capture/"):] for token in CAPTURE_PATH.findall(text)}
    return names - {""}          # the bare `capture/` directory itself


def _on_block() -> str:
    """Up to the next key at column 0. Not `split("\\n\\n")`: a block
    scalar in `workflow_dispatch.inputs` contains a blank line."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "\non:\n" in text, "the workflow has no `on:` block"
    lines = []
    for line in text.split("\non:\n", 1)[1].splitlines():
        if line.strip() and not line.startswith(" "):
            break
        lines.append(line)
    return "\n".join(lines)


def _schedule_block() -> str:
    """Only the `schedule:` list. A `cron` string anywhere else in the
    file - `CAPTURE_MODE` tests one - is not a trigger."""
    block = _on_block()
    assert "\n  schedule:\n" in block, "the workflow has no `schedule:` list"
    tail = block.split("\n  schedule:\n", 1)[1]
    lines = []                   # up to the next key at the same indent
    for line in tail.splitlines():
        if line.strip() and not line.startswith("    "):
            break
        lines.append(line)
    return "\n".join(lines)


def _crons() -> List[str]:
    return CRON.findall(_schedule_block())


def _cadence(cron: str) -> Tuple[str, Optional[str], str]:
    """`("weekly", "Sunday", "03:00 UTC")` from `0 3 * * 0`."""
    minute, hour, dom, _month, dow = cron.split()
    clock = "{:02d}:{:02d} UTC".format(int(hour), int(minute))
    if dow != "*" and dom == "*":
        return "weekly", DAYS[int(dow.split(",")[0]) % 7], clock
    if dom != "*" and dow == "*":
        return "monthly", "day {}".format(int(dom)), clock
    if dom == "*" and dow == "*":
        return "daily", None, clock
    raise AssertionError(
        "cron `{}` is neither weekly, monthly nor daily - the "
        "document's sentence needs a word this guard cannot derive"
        .format(cron))


def _triggers() -> set:
    return set(TRIGGER.findall(_on_block()))


# --- the document half: the subject, never the argument --------------

def _trigger_sentence() -> str:
    """The first paragraph of `## Reproducing`. The paragraphs after it
    argue about triggers - the removed `push`, the monthly cron's cold
    result - and a guard that read those would match its own
    explanation."""
    text = DOC.read_text(encoding="utf-8")
    assert "\n## Reproducing\n" in text, "the document has no Reproducing section"
    body = text.split("\n## Reproducing\n", 1)[1]
    return body.strip().split("\n\n", 1)[0]


def _table_files() -> set:
    """Every name in the contents table. One cell may list several."""
    text = DOC.read_text(encoding="utf-8")
    assert "| file | what it is |" in text, "the contents table has moved"
    body = text.split("| file | what it is |", 1)[1].split("\n\n", 1)[0]
    names = set()
    for line in body.splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        for name in CELL_NAME.findall(line.split("|")[1]):
            names.add(name.rstrip("/"))
    return names


# --- the guards ------------------------------------------------------

class TestTheContentsTableIsTheWorkflowsFileList:

    def test_it_names_every_file_the_workflow_writes(self):
        missing = sorted(_workflow_files() - _table_files())
        assert missing == [], (
            "the workflow writes these under `capture/` and the contents "
            "table names none of them: {}".format(missing))

    def test_it_names_nothing_the_workflow_does_not_write(self):
        extra = sorted(_table_files() - _workflow_files())
        assert extra == [], (
            "the contents table promises files no longer written to "
            "`capture/`: {}".format(extra))


class TestTheTriggerSentenceIsTheScheduleBlock:

    def test_it_names_every_cron(self):
        sentence = _trigger_sentence()
        for cron in _crons():
            cadence, when, clock = _cadence(cron)
            for token in (cadence, when, clock):
                if token is None:
                    continue
                assert token in sentence, (
                    "cron `{}` runs {} at {}; the trigger sentence does "
                    "not say `{}`:\n{}".format(
                        cron, cadence, clock, token, sentence))

    def test_it_claims_no_cadence_the_workflow_lacks(self):
        """The half that catches a *removed* cron: the sentence would
        still name it, and every positive check would still pass."""
        sentence = _trigger_sentence()
        real = {_cadence(cron)[0] for cron in _crons()}
        for cadence in CADENCES:
            if cadence in real:
                continue
            assert cadence not in sentence, (
                "the trigger sentence claims a {} run; the workflow's "
                "schedule has {}".format(cadence, sorted(_crons())))

    def test_it_names_every_trigger_the_workflow_has(self):
        """`and on nothing else` is a claim about the whole `on:` block,
        not only the crons."""
        sentence = _trigger_sentence()
        for trigger in sorted(_triggers()):
            if trigger == "schedule":
                continue          # named by its cadence, checked above
            assert trigger in sentence, (
                "`{}` is a trigger of this workflow and the sentence "
                "that says what triggers it does not mention it"
                .format(trigger))


class TestTheDerivationWouldCatchTheDriftItWasWrittenFor:
    """The parsers, against inputs this repository does not hold - so a
    mutation of the real files is not the only thing that can red them."""

    def test_a_cron_becomes_the_words_the_sentence_owes(self):
        assert _cadence("0 3 * * 0") == ("weekly", "Sunday", "03:00 UTC")
        assert _cadence("0 4 1 * *") == ("monthly", "day 1", "04:00 UTC")
        assert _cadence("30 0 * * *") == ("daily", None, "00:30 UTC")

    def test_a_cron_literal_outside_the_schedule_list_is_not_a_trigger(self):
        """`CAPTURE_MODE` compares `github.event.schedule` against a
        cron literal in `env:`. A parser that read every cron-shaped
        string in the file would report a trigger that does not exist."""
        env = WORKFLOW.read_text(encoding="utf-8").split("\nenv:\n", 1)[1]
        assert "0 4 1 * *" in env, "`env:` no longer selects the mode by cron"
        assert "env:" not in _schedule_block()
        assert CRON.search(env) is None

    def test_a_multi_name_cell_yields_every_name(self):
        names = _table_files()
        assert {"state-after-warm.txt", "state-after-delete.txt"} <= names
        assert {"analyze.txt", "analyze.json", "correlate.txt"} <= names


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
