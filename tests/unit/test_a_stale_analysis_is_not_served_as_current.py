"""UX-1367: an analysis written by another bga version is said to be, not served as current.

`stale` was the contract set alone, so UX-1357..1366 (additive, no contract
bump) left a bga 0.5.0 `analyze.json` reading current under 0.6.2. The stored
version is now compared as-is to this build's `producer.version_of`; a dev
build's version is `bga.__version__`, a static string with no git suffix, so
two dev builds of one release compare equal - a `+g<sha>` suffix, were one
added, would differ and read stale, which is the intended direction.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import producer
from tools import bga_view as view

FIXTURE = REPO / "tests/fixtures/with_timeline"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _run_dir(tmp_path, version):
    """A copy of the fixture whose `analyze.json` names `version` (None: no file)."""
    root = tmp_path / "snap"
    shutil.copytree(FIXTURE, root)
    stored = root / "analyze.json"
    if version is None:
        stored.unlink()
        return root
    document = json.loads(stored.read_text(encoding="utf-8"))
    document["producer"] = {"tool": "bga", "version": version, "contracts": producer.stamp()["contracts"]}
    stored.write_text(json.dumps(document), encoding="utf-8")
    return root


class TestTheStoredVersionIsCompared:
    def test_an_older_version_with_unmoved_contracts_is_stale(self, tmp_path):
        note = view.analysis_note(str(_run_dir(tmp_path, "0.5.0") / "run"))
        assert note["contracts_moved"] == []
        assert note["stored_producer"] == "0.5.0"
        assert note["version_moved"] is True
        assert note["stale"] is True, note

    def test_the_same_version_is_not_stale(self, tmp_path):
        note = view.analysis_note(str(_run_dir(tmp_path, producer.stamp()["version"]) / "run"))
        assert note["version_moved"] is False
        assert note["stale"] is False, note

    def test_a_suffixed_build_of_the_same_release_is_another_build(self, tmp_path):
        mine = producer.stamp()["version"]
        note = view.analysis_note(str(_run_dir(tmp_path, f"{mine}+gabc1234") / "run"))
        assert note["stale"] is True and note["version_moved"] is True, note

    def test_no_analysis_is_analysed_here_and_not_stale(self, tmp_path):
        note = view.analysis_note(str(_run_dir(tmp_path, None) / "run"))
        assert note["source"] == view.ANALYSIS_FROM_VIEW
        assert note["stale"] is False and note["version_moved"] is False, note

    def test_reanalysing_is_not_stale_whatever_was_stored(self, tmp_path):
        note = view.analysis_note(str(_run_dir(tmp_path, "0.5.0") / "run"), reanalyse=True)
        assert note["stale"] is False and note["version_moved"] is False, note

    def test_an_unstamped_capture_is_stale_but_its_version_is_not_said_to_have_moved(self):
        stored = json.loads((FIXTURE / "analyze.json").read_text(encoding="utf-8"))
        note = view.analysis_source(stored, reanalysed=False)
        assert note["stale"] is True and note["version_moved"] is False, note


_PROBE = """
const app = await import("./tests/viewer.mjs");
const BASE = { source: "capture", stored_producer: "0.5.0", this_build: "0.6.2",
               contracts_moved: [], sections_declared: 35, sections_absent: [],
               stale: true, version_moved: true, reanalyse: "bga view RUN --reanalyse" };
process.stdout.write(JSON.stringify({
  version: app.analysisSentence(BASE),
  same: app.analysisSentence({ ...BASE, stale: false, version_moved: false, stored_producer: "0.6.2" }),
  both: app.analysisSentence({ ...BASE, contracts_moved: ["a/v1 -> a/v2"] }),
}));
"""


@pytest.fixture(scope="module")
def said():
    result = subprocess.run(
        [node, "--input-type=module", "-e", _PROBE],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=60,
        env=dict(os.environ),
    )
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout)


@needs_node
class TestThePageSaysWhichBgaWroteIt:
    def test_a_version_only_staleness_names_both_builds_and_the_flag(self, said):
        assert said["version"] == (
            "analysed at capture by bga 0.5.0; this is bga 0.6.2, whose analysis may differ "
            "— re-run with `bga view RUN --reanalyse`"
        )

    def test_the_same_version_makes_no_claim(self, said):
        assert said["same"] == "analysed at capture by bga 0.6.2"

    def test_a_moved_contract_keeps_its_own_sentence(self, said):
        assert "1 of the contracts it records have moved" in said["both"], said["both"]
