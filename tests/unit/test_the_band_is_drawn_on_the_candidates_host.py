"""UX-1285: `--band-from-class` draws its members from the candidate's host.

A band over two runner types is wider than either machine's noise, so a
member whose host manifest differs from the candidate's is skipped unless
`--allow-cross-host` is passed, and the refusal and the comment say how
many were skipped. A run with no manifest on either side is kept.
"""

import json
import pathlib

from bga.exceptions import EXIT_BAND_UNAVAILABLE, EXIT_OK
from tests.unit.test_the_band_comes_from_the_class import REVIEW, SECOND, _compare, _run_dir

HOST_A = {"schema": "host/v2", "cpu_model": "Xeon A", "cpu_count": 16, "memory_bytes": 64 << 30}
HOST_B = {"schema": "host/v2", "cpu_model": "EPYC B", "cpu_count": 16, "memory_bytes": 64 << 30}


def _on(path: pathlib.Path, host) -> pathlib.Path:
    context_path = path / "run-context.json"
    context = json.loads(context_path.read_text())
    if host is not None:
        context["host_manifest"] = host
    context_path.write_text(json.dumps(context))
    return path


def _store(tmp_path, hosts, baseline_host=HOST_A, candidate_host=HOST_A, baseline_in_members=False):
    """`hosts` are the members, oldest first; the baseline is the last of them
    when `baseline_in_members`, else its own newer run; the candidate is newest."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "project.conf").write_text("name: ux1285\n", encoding="utf-8")
    runs = project / ".bga" / "runs"
    made = []
    for index, host in enumerate(hosts):
        made.append(
            _on(_run_dir(runs / f"202609{index + 1:02d}T000000Z" / "run", 100 * SECOND, "review", REVIEW), host)
        )
    if baseline_in_members:
        baseline = made[-1]
    else:
        baseline = _on(_run_dir(runs / "20260920T000000Z" / "run", 100 * SECOND, "review", REVIEW), baseline_host)
    candidate = _on(_run_dir(runs / "20260921T000000Z" / "run", 101 * SECOND, "review", REVIEW), candidate_host)
    return baseline, candidate


def _members(output: str) -> set:
    return {f"202609{index:02d}T000000Z" for index in range(1, 20) if f"`202609{index:02d}T000000Z`" in output}


class TestTheBandIsTheCandidatesHost:
    def test_a_host_a_candidate_gets_the_three_host_a_runs(self, tmp_path):
        baseline, candidate = _store(tmp_path, [HOST_A] * 3 + [HOST_B] * 3, baseline_in_members=True)

        code, output = _compare(baseline, candidate, "--band-from-class", "--format", "ci-comment")

        assert code == EXIT_OK, output
        assert "band from baseline 3 runs" in output
        assert _members(output) == {"20260901T000000Z", "20260902T000000Z", "20260903T000000Z"}
        assert "2 runs of this class skipped, measured on another host" in output

    def test_allow_cross_host_pools_the_five(self, tmp_path):
        baseline, candidate = _store(tmp_path, [HOST_A] * 3 + [HOST_B] * 3, baseline_in_members=True)

        code, output = _compare(
            baseline, candidate, "--band-from-class", "--allow-cross-host", "--format", "ci-comment"
        )

        assert code == EXIT_OK, output
        assert "band from baseline 5 runs" in output
        assert "skipped, measured on another host" not in output

    def test_too_few_on_this_host_refuses_naming_the_skipped(self, tmp_path):
        baseline, candidate = _store(tmp_path, [HOST_A] * 2 + [HOST_B] * 4)

        code, output = _compare(baseline, candidate, "--band-from-class", "--fail-on-regression")

        assert code == EXIT_BAND_UNAVAILABLE, output
        assert "holds other 2 runs of that class" in output
        assert "4 skipped for host: cpu_model" in output
        assert "Verdict:" not in output

    def test_a_member_with_no_manifest_is_kept(self, tmp_path):
        baseline, candidate = _store(tmp_path, [None] * 3 + [HOST_B] * 2)

        code, output = _compare(baseline, candidate, "--band-from-class", "--format", "ci-comment")

        assert code == EXIT_OK, output
        assert "band from baseline 3 runs" in output
        assert "2 runs of this class skipped" in output

    def test_a_candidate_with_no_manifest_keeps_every_member(self, tmp_path):
        baseline, candidate = _store(tmp_path, [HOST_A] * 2 + [HOST_B] * 2, baseline_host=None, candidate_host=None)

        code, output = _compare(baseline, candidate, "--band-from-class", "--format", "ci-comment")

        assert code == EXIT_OK, output
        assert "band from baseline 4 runs" in output
        assert "skipped, measured on another host" not in output
