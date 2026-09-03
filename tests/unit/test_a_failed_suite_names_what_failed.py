"""UX-554: a red CI job still says which test was red.

`UX-491` made the drift gate's verdict reach a log-tail reader. It did
it on the steps that run when the suite *passed* - so on the one run
where the record matters, the junit was discarded with the runner and
the assertion had scrolled out of the log window the API returns.
Round 81 could not name four red jobs on its own PR.

Two claims, two instruments: the workflow keeps the file whatever the
suite did, and `tools/dev_junit_tail.py` turns it into the lines a
truncated log still needs.
"""
import pathlib
import subprocess
import sys

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

WORKFLOW = REPO / ".github/workflows/ci.yml"
TAIL = REPO / "tools/dev_junit_tail.py"

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" errors="1" failures="1" tests="3">
<testcase classname="tests.unit.test_a" name="test_green" time="0.01"/>
<testcase classname="tests.unit.test_b" name="test_red" time="0.01">
<failure message="AssertionError: 0 == 1&#10;second line">body</failure></testcase>
<testcase classname="tests.unit.test_c" name="test_broken" time="0.01">
<error message="RuntimeError: it threw">body</error></testcase>
</testsuite></testsuites>
"""


def _steps():
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    for job in document["jobs"].values():
        for step in job.get("steps", []):
            yield step


def _tail(path):
    result = subprocess.run([sys.executable, str(TAIL), str(path)],
                            capture_output=True, text=True, cwd=REPO)
    return result.returncode, result.stdout + result.stderr


class TestTheRecordOutlivesTheRunner:

    def test_the_junit_is_uploaded_whatever_the_suite_did(self):
        """The whole item. An upload gated on success is an upload that
        never happens on the run you need it for."""
        kept = [s for s in _steps()
                if "upload-artifact" in str(s.get("uses", ""))
                and "junit" in str(s.get("with", {}).get("path", ""))]
        assert kept, (
            "no step uploads the junit; a failed suite discards the only "
            "record naming what failed")
        for step in kept:
            assert "always()" in str(step.get("if", "")), (
                f"the junit upload is conditional on {step.get('if')!r}, so "
                f"it does not run on the failure it exists for")

    def test_a_step_names_the_failures_on_the_failure_path(self):
        """`UX-491`'s rule, on the path where the gate does not run: the
        log tail must carry the verdict even when truncated."""
        named = [s for s in _steps()
                 if "dev_junit_tail" in str(s.get("run", ""))]
        assert named, "nothing prints the failing ids on the failure path"
        assert any("failure()" in str(s.get("if", "")) for s in named), (
            "the naming step does not run on failure")


class TestTheTailNamesThem:

    def test_it_names_every_failure_and_error(self, tmp_path):
        path = tmp_path / "junit.xml"
        path.write_text(JUNIT, encoding="utf-8")
        code, out = _tail(path)
        assert code == 0, out
        assert "2 test(s) failed" in out, out
        assert "tests.unit.test_b::test_red" in out
        assert "tests.unit.test_c::test_broken" in out
        assert "AssertionError: 0 == 1" in out
        assert "tests.unit.test_a" not in out, (
            "a passing test is named, so the list is not the failures")

    def test_a_multi_line_message_is_cut_to_its_first_line(self, tmp_path):
        """The point is a legible tail, not a second copy of the log."""
        path = tmp_path / "junit.xml"
        path.write_text(JUNIT, encoding="utf-8")
        _code, out = _tail(path)
        assert "second line" not in out, out

    def test_a_junit_with_no_failure_says_so(self, tmp_path):
        """Non-vacuity: the suite can fail at collection or in `make`,
        and a tool that printed nothing would read as 'nothing failed'."""
        path = tmp_path / "junit.xml"
        path.write_text('<?xml version="1.0"?><testsuites><testsuite '
                        'name="pytest"><testcase classname="a" name="b"/>'
                        '</testsuite></testsuites>', encoding="utf-8")
        code, out = _tail(path)
        assert code == 0
        assert "records no failure" in out, out

    def test_an_unreadable_junit_does_not_mask_the_real_failure(self, tmp_path):
        """It runs *after* a failing suite. Exiting non-zero here would
        replace the reader's error with this tool's own."""
        code, out = _tail(tmp_path / "absent.xml")
        assert code == 0, "the tail masked the failure it was reporting on"
        assert "could not be read" in out, out


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
