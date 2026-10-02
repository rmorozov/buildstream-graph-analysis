"""UX-1286: `bga compare --band-from-class --bundles DIR` reads its band from the kept tree.

A review runner holds the candidate and nothing else, so the members come
from the bundles CI kept, through a temporary store deleted on exit - the
route `bga snapshot --bundles` takes - and no `project.conf` is needed.
"""

import os
import pathlib
import tempfile

import pytest

from bga import bundle
from bga.exceptions import EXIT_BAND_UNAVAILABLE, EXIT_GENERAL, EXIT_INGESTION, EXIT_OK
from tests.unit.test_the_band_comes_from_the_class import REVIEW, SECOND, _compare, _run_dir
from tests.unit.test_the_band_is_drawn_on_the_candidates_host import HOST_A, HOST_B, _on

CANDIDATE_STAMP = "20260921T000000Z"


def _tree(tmp_path, hosts, with_candidate=False):
    """A CI tree of one bundle per member, oldest first, in build-number directories."""
    home = tmp_path / "home" / ".bga" / "runs"
    tree = tmp_path / "kept"
    stamps = [f"202609{index + 1:02d}T000000Z" for index in range(len(hosts))]
    if with_candidate:
        stamps.append(CANDIDATE_STAMP)
        hosts = [*hosts, HOST_A]
    for number, (stamp, host) in enumerate(zip(stamps, hosts), start=100):
        _on(_run_dir(home / stamp / "run", 100 * SECOND, "review", REVIEW), host)
        (tree / str(number)).mkdir(parents=True)
        bundle.export(str(home / stamp), str(tree / str(number) / bundle.default_output(stamp)))
    return tree


@pytest.fixture
def runner(tmp_path, monkeypatch):
    """A stateless review runner: cwd and the temporary directory are empty, no project anywhere."""
    work = tmp_path / "work"
    scratch = tmp_path / "tmp"
    work.mkdir()
    scratch.mkdir()
    monkeypatch.chdir(work)
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    elsewhere = tmp_path / "ci-job"
    baseline = _on(_run_dir(elsewhere / "baseline", 100 * SECOND, "review", REVIEW), HOST_A)
    candidate = _on(_run_dir(elsewhere / CANDIDATE_STAMP / "run", 101 * SECOND, "review", REVIEW), HOST_A)
    return work, scratch, baseline, candidate


def _members(output: str) -> set:
    return {f"202609{index:02d}T000000Z" for index in range(1, 30) if f"`202609{index:02d}T000000Z`" in output}


class TestTheBandComesFromTheKeptTree:
    def test_five_kept_bundles_are_the_band_and_nothing_is_left_behind(self, tmp_path, runner, monkeypatch):
        work, scratch, baseline, candidate = runner
        tree = _tree(tmp_path, [HOST_A] * 5)
        stores = []
        load_tree = bundle.load_tree
        monkeypatch.setattr(
            bundle, "load_tree", lambda root, project: stores.append(project) or load_tree(root, project)
        )

        code, output = _compare(
            baseline, candidate, "--band-from-class", "--bundles", str(tree), "--format", "ci-comment"
        )

        assert code == EXIT_OK, output
        assert "band from baseline 5 runs" in output
        assert f"read from the bundles under `{tree}`" in output
        assert [os.path.dirname(store) for store in stores] == [str(scratch)]
        assert os.listdir(work) == []
        assert os.listdir(scratch) == []

    def test_the_candidates_own_stamp_in_the_tree_does_not_vote(self, tmp_path, runner):
        work, scratch, baseline, candidate = runner
        tree = _tree(tmp_path, [HOST_A] * 5, with_candidate=True)

        code, output = _compare(
            baseline, candidate, "--band-from-class", "--bundles", str(tree), "--format", "ci-comment"
        )

        assert code == EXIT_OK, output
        assert "band from baseline 5 runs" in output
        assert f"`{CANDIDATE_STAMP}`" not in output

    def test_the_host_filter_applies_to_the_tree(self, tmp_path, runner):
        work, scratch, baseline, candidate = runner
        tree = _tree(tmp_path, [HOST_A] * 3 + [HOST_B] * 2)

        code, output = _compare(
            baseline, candidate, "--band-from-class", "--bundles", str(tree), "--format", "ci-comment"
        )

        assert code == EXIT_OK, output
        assert _members(output) == {"20260901T000000Z", "20260902T000000Z", "20260903T000000Z"}
        assert "2 runs of this class skipped, measured on another host" in output

    def test_too_few_kept_runs_refuse_naming_the_tree(self, tmp_path, runner):
        work, scratch, baseline, candidate = runner
        tree = _tree(tmp_path, [HOST_A] * 2)

        code, output = _compare(
            baseline, candidate, "--band-from-class", "--bundles", str(tree), "--fail-on-regression"
        )

        assert code == EXIT_BAND_UNAVAILABLE, output
        assert f"the bundles under {tree} hold other 2 runs of that class" in output
        assert os.listdir(scratch) == []

    def test_a_truncated_bundle_is_refused_by_name_and_nothing_is_judged(self, tmp_path, runner):
        work, scratch, baseline, candidate = runner
        tree = _tree(tmp_path, [HOST_A] * 5)
        broken = pathlib.Path(bundle.bundles_under(str(tree))[2])
        broken.write_bytes(broken.read_bytes()[: broken.stat().st_size // 2])

        code, output = _compare(
            baseline, candidate, "--band-from-class", "--bundles", str(tree), "--fail-on-regression"
        )

        assert code == EXIT_INGESTION, output
        assert str(broken) in output
        assert "Verdict:" not in output
        assert os.listdir(scratch) == []

    def test_bundles_without_the_band_flag_is_a_usage_error(self, tmp_path, runner):
        work, scratch, baseline, candidate = runner
        tree = _tree(tmp_path, [HOST_A] * 5)

        code, output = _compare(baseline, candidate, "--bundles", str(tree))

        assert code == EXIT_GENERAL, output
        assert "pass --band-from-class" in output
