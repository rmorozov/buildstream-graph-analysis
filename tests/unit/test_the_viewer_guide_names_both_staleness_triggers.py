"""UX-1392: viewer.md's staleness sentence names both triggers `analysis_source` stales on."""

import inspect
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import bga_view

GUIDE = REPO / "docs/guides/viewer.md"


def _sentence() -> str:
    text = " ".join(GUIDE.read_text(encoding="utf-8").split())
    match = re.search(r"Stale means[^.]*\.[^.]*\.", text)
    assert match, "viewer.md has no 'Stale means ...' sentence"
    return match.group(0)


def test_the_code_stales_on_exactly_a_contract_move_or_a_version_move():
    source = inspect.getsource(bga_view.analysis_source)
    assert re.search(r'"stale":.*\bmoved or version_moved\b', source)


def test_the_sentence_names_the_contract_set_and_the_bga_version():
    sentence = _sentence().lower()
    assert "contract set" in sentence
    assert "another version of bga" in sentence
    assert "not a version comparison" not in sentence
