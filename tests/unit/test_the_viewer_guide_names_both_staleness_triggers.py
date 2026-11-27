"""UX-1392: viewer.md's staleness sentence names the two triggers `analysis_source` stales on."""

import copy
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import producer
from tools import bga_view

GUIDE = REPO / "docs/guides/viewer.md"


def _sentence() -> str:
    text = " ".join(GUIDE.read_text(encoding="utf-8").split())
    match = re.search(r"Stale means[^.]*\.", text)
    assert match, "viewer.md has no 'Stale means ...' sentence"
    return match.group(0)


def _stored(contracts=None, version=None) -> dict:
    stamp = copy.deepcopy(producer.stamp())
    if contracts is not None:
        stamp["contracts"] = contracts
    if version is not None:
        stamp["version"] = version
    return {"producer": stamp}


def _stale(stored) -> bool:
    return bga_view.analysis_source(stored, False)["stale"]


def test_a_stored_analysis_differing_only_in_contract_set_is_stale():
    mine = list(producer.stamp()["contracts"])
    assert _stale(_stored(contracts=mine[:-1]))


def test_a_stored_analysis_differing_only_in_producer_version_is_stale():
    assert _stale(_stored(version="0.0.0-other"))


def test_a_stored_analysis_differing_in_neither_is_not_stale():
    assert not _stale(_stored())


def test_the_sentence_names_the_contract_set_and_the_bga_version():
    sentence = _sentence().lower()
    assert "contract set" in sentence
    assert "another version of bga" in sentence
    assert "not a version comparison" not in sentence
    assert "finding your way" not in sentence
