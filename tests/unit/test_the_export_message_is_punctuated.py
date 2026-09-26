"""UX-1036: the export's timeline-absence line reads one sentence.

`written["omitted"]` is a sentence from `bga/plane2.py` that already
ends in a period; `main()` appended `. ` before its own hint and the
terminal printed "goes missing.. `bga timeline` renders one".
"""
import json
import os
import shutil

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"


def _run_with_plane2_no_raw_log(tmp_path):
    snapshot = tmp_path / "20260102T000000Z"
    run = snapshot / "run"
    run.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(GOLDEN, run)
    os.remove(run / "expected_output.json")
    (snapshot / "plane2.json").write_text(json.dumps({
        "schema": "plane2/v3", "process_count": 3,
        "matched_count": 0, "open_count": 0, "by_binary": []}))
    return str(run)


def test_no_double_period_before_the_timeline_hint(tmp_path, capsys):
    from tools import bga_view

    run = _run_with_plane2_no_raw_log(tmp_path)
    page = tmp_path / "out.html"

    code = bga_view.main([run, "--export", str(page)])

    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert ".." not in captured.err, captured.err
