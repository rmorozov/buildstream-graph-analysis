"""UX-895: Plane 2's cost was prose - "runs on a hot path" - with no
number behind it. This reads the paragraph that replaced that prose and
asserts it still carries what makes it a measurement rather than an
adjective: a percentage, a host class, a date, and a budget verdict.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
DOC = REPO / "docs/guides/real-project.md"

ANCHOR = "Plane 2 costs real overhead."

PERCENT = re.compile(r"[+-]?\d+(\.\d+)?%")
ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
HOST_CLASS = re.compile(r"Graviton|Cortex-A72|EPYC|Ryzen", re.I)
BUDGET = re.compile(r"budget", re.I)


def _paragraph():
    text = DOC.read_text(encoding="utf-8")
    start = text.index(ANCHOR)
    end = text.index("\n---", start)
    return text[start:end]


def test_the_paragraph_exists():
    text = DOC.read_text(encoding="utf-8")
    assert ANCHOR in text, "the overhead sentence has moved or was removed"


def test_it_names_a_percentage():
    assert PERCENT.search(_paragraph()), (
        "the overhead paragraph names no percentage - it is prose again")


def test_it_names_a_host_class():
    assert HOST_CLASS.search(_paragraph()), (
        "the overhead paragraph names no host class")


def test_it_names_a_date():
    assert ISO_DATE.search(_paragraph()), (
        "the overhead paragraph is undated")


def test_it_states_which_arms_fit_the_budget():
    assert BUDGET.search(_paragraph()), (
        "the overhead paragraph never says whether the arms fit the budget")
