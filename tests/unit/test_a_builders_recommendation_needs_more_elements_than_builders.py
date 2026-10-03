"""UX-1324: a run that built fewer elements than its builders recommends no builders value.

The walk's one-element incremental run said `Lower --builders to 1` because a
memory envelope measured over one element peak "allowed" one builder.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from bga.correlate import compute_capacity_recommendation

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "macro_micro"
WITHHELD = "Builders recommendation withheld: this run built 1 element, too few to measure a bound for 4 builders."


def _plane2():
    return {'cores_busy': 0.96, 'host_cpu_count': 4, 'saturated': False, 'pinned_elements': []}


def _envelope():
    """One element measured, as the walk's incremental run had: `memory allows 1`."""
    return {
        'host_memory_bytes': 16 * 2**30,
        'elements_measured': 1,
        'largest_element_peak_bytes': 50 * 2**20,
        'projections': [{'builders': 1, 'envelope_bytes': 50 * 2**20, 'share_of_host': 0.003, 'fits': True}],
    }


class TestTheRecommendationIsWithheld:
    def test_fewer_built_elements_than_builders_recommend_nothing(self):
        rec = compute_capacity_recommendation(_plane2(), _envelope(), knee=None, builders=4, built_elements=1)
        assert rec['recommended_builders'] is None and rec['binding_constraint'] is None, rec
        assert rec['constraints'] == []
        assert rec['verdict'] == WITHHELD
        assert rec['withheld'] == {'built_elements': 1, 'reason': WITHHELD}

    def test_as_many_built_elements_as_builders_still_recommend(self):
        rec = compute_capacity_recommendation(_plane2(), _envelope(), knee=None, builders=4, built_elements=4)
        assert 'withheld' not in rec
        assert (rec['binding_constraint'], rec['recommended_builders']) == ('memory', 1)


def _analyze(run, fmt):
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(run / "run"), "--plane2", str(run / "plane2.json")]
        + (["--format", fmt] if fmt else []),
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO,
    )
    return done.stdout


@pytest.fixture(scope="module")
def one_built(tmp_path_factory):
    """`macro_micro` with its Pipeline Summary saying one element built and ten came from cache."""
    run = tmp_path_factory.mktemp("one-built") / "macro_micro"
    shutil.copytree(FIXTURE, run)
    context_path = run / "run" / "run-context.json"
    context = json.loads(context_path.read_text())
    context["queue_summary"]["build"] = {"processed": 1, "skipped": 10, "failed": 0}
    context_path.write_text(json.dumps(context))
    return run


class TestTheRunOnThePageAndInTheTerminal:
    def test_the_text_prints_the_withheld_line_and_no_builders_step(self, one_built):
        text = _analyze(one_built, None)
        assert "1 element built, too few to bound 4 builders: builders recommendation withheld" in text, text
        assert "Lower --builders" not in text
        assert "Time a build at --builders" not in text

    def test_the_json_the_page_reads_withholds_it_everywhere(self, one_built):
        document = json.loads(_analyze(one_built, "json"))
        rec = document["capacity_recommendation"]
        assert rec["withheld"]["built_elements"] == 1
        assert rec["recommended_builders"] is None and rec["verdict"] == WITHHELD
        assert document["agent_sizing"]["builders"]["recommended"] is None
        finding = next(f for f in document["findings"] if f["id"] == "capacity-recommendation")
        assert "text" not in finding["step"], finding["step"]

    def test_the_unmodified_fixture_still_recommends(self):
        document = json.loads(_analyze(FIXTURE, "json"))
        assert "withheld" not in document["capacity_recommendation"]
        assert document["capacity_recommendation"]["recommended_builders"] is not None
