"""`UX-1125`: a junit with a failing file appends `{file, sha, round}`; a green one appends nothing."""

import io
import json
import pathlib
import sys
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import dev_guard_prices
import dev_red_ledger

JUNIT = """<testsuites><testsuite>
<testcase classname="tests.unit.test_a" name="test_one"/>
<testcase classname="tests.unit.test_b.TestB" name="test_two">{body}</testcase>
</testsuite></testsuites>"""


def _junit(body):
    return io.BytesIO(JUNIT.format(body=body).encode())


def _file_of(classname):
    return "/".join(classname.split(".")[:3]).replace("/TestB", "") + ".py"


def test_a_red_junit_appends_one_entry():
    files = dev_red_ledger.failing_files(_junit('<failure message="x"/>'), file_of=_file_of)
    assert files == ["tests/unit/test_b.py"]
    assert dev_red_ledger.append([], files, "abc", 152) == [
        {"file": "tests/unit/test_b.py", "sha": "abc", "round": 152}
    ]


def test_a_green_junit_appends_none():
    files = dev_red_ledger.failing_files(_junit(""), file_of=_file_of)
    assert files == []
    assert dev_red_ledger.append([], files, "abc", 152) == []


def test_an_error_counts_and_a_repeat_sha_is_not_appended_twice():
    files = dev_red_ledger.failing_files(_junit('<error message="x"/>'), file_of=_file_of)
    once = dev_red_ledger.append([], files, "abc", 152)
    assert dev_red_ledger.append(once, files, "abc", 152) == once


def test_the_last_catch_is_the_latest_round_and_feeds_the_prices():
    ledger = [{"file": "t.py", "sha": "a", "round": 3}, {"file": "t.py", "sha": "b", "round": 9}]
    assert dev_red_ledger.last_catch(ledger) == {"t.py": 9}
    rows = dev_guard_prices.proposals({"t.py": 5.0}, {"t.py": [("UX-1", "named")]}, {"t.py": 9}, 30, 10)
    assert rows[0][4] == "scheduled lane"


def test_an_absent_ledger_reads_unrecorded(monkeypatch):
    def missing(_path):
        raise FileNotFoundError

    monkeypatch.setattr(dev_guard_prices.dev_records, "load", missing)
    assert dev_guard_prices.recorded_catches() == {}


def test_the_pr_path_reads_only_red_ci_runs_junit_artifacts():
    calls = []
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("junit.xml", "<testsuites/>")

    def get(url, token):
        calls.append(url)
        if url.endswith("/pulls"):
            return json.dumps([{"head": {"sha": "H"}}]).encode()
        if "/actions/runs?" in url:
            runs = [
                {"id": 1, "path": ".github/workflows/ci.yml", "conclusion": "failure"},
                {"id": 2, "path": ".github/workflows/ci.yml", "conclusion": "success"},
            ]
            return json.dumps({"workflow_runs": runs}).encode()
        arts = [
            {"name": "junit-3.12", "archive_download_url": "u"},
            {"name": "other", "archive_download_url": "v"},
        ]
        return json.dumps({"artifacts": arts}).encode()

    out = dev_red_ledger.red_junits("o/r", "S", "tok", get=get, download=lambda url, token: archive.getvalue())
    assert out == [b"<testsuites/>"]
    assert sum("/runs/1/artifacts" in c for c in calls) == 1 and not any("/runs/2/" in c for c in calls)
