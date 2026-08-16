"""Tests for UX-38: `bst_native_build_tracer report` took a raw trace
log, and handing it the JSON report `run` had just written parsed as zero
trace lines - printing `Processes traced: 0 (0 matched, 0 no observed
exit)` and exiting 0, in the same format it uses for a real answer.

`run` discards the raw log unless `--raw-log` is passed, so the JSON
report is the artifact most sessions actually keep, and there was no way
to re-render it at all.
"""
import json

import pytest

from tools.bst_native_build_tracer import (
    EmptyTraceError, load_and_summarize, load_saved_report,
)

_SAVED_REPORT = {
    "process_count": 822,
    "matched_count": 663,
    "open_count": 159,
    "open_records_note": "",
    "by_binary": {"cc1plus": 51, "make": 99},
    "by_element": {"core.bst": 113, "lib-a.bst": 88},
    "max_concurrency": 20,
    "wall_span_s": 39.06,
    "redundant_operations": [],
    "processes": [],
    "static_binary_disclaimer": "",
}


def test_a_saved_json_report_is_recognized(tmp_path):
    path = tmp_path / "native.json"
    path.write_text(json.dumps(_SAVED_REPORT))
    assert load_saved_report(str(path)) == _SAVED_REPORT


def test_a_raw_trace_log_is_not_mistaken_for_a_report(tmp_path):
    path = tmp_path / "trace.log"
    path.write_text("START 1 1 1000.0 /usr/bin/make -j4\n")
    assert load_saved_report(str(path)) is None


def test_unrelated_json_is_not_mistaken_for_a_report(tmp_path):
    """Detection is by this tool's own report keys, not by "it's JSON" -
    a Chrome Trace or a bga run-context must not be rendered as one."""
    path = tmp_path / "chrome-trace.json"
    path.write_text(json.dumps({"traceEvents": [], "displayTimeUnit": "ms"}))
    assert load_saved_report(str(path)) is None


def test_an_unparseable_file_is_an_error_not_a_zero_process_report(tmp_path):
    """The core defect: a confident, correctly-formatted, wrong answer."""
    path = tmp_path / "junk.txt"
    path.write_text("this is not a trace log at all\n")
    with pytest.raises(EmptyTraceError):
        load_and_summarize(str(path))


def test_a_genuinely_empty_log_is_still_a_legitimate_zero_result(tmp_path):
    """An empty log means nothing ran (or the hook never loaded) - a real
    zero-process result, distinct from the wrong-file case above and it
    must stay distinguishable."""
    path = tmp_path / "empty.log"
    path.write_text("")
    report = load_and_summarize(str(path))
    assert report["process_count"] == 0


def test_report_subcommand_renders_a_saved_json_report(tmp_path, capsys):
    from tools.bst_native_build_tracer import main

    path = tmp_path / "native.json"
    path.write_text(json.dumps(_SAVED_REPORT))
    import sys
    argv = sys.argv
    sys.argv = ["bst_native_build_tracer.py", "report", str(path)]
    try:
        assert main() == 0
    finally:
        sys.argv = argv
    out = capsys.readouterr().out
    assert "Processes traced: 822" in out
    assert "Processes traced: 0" not in out


def test_report_subcommand_exits_nonzero_on_a_wrong_file(tmp_path, capsys):
    from tools.bst_native_build_tracer import main

    path = tmp_path / "junk.txt"
    path.write_text("nope\n")
    import sys
    argv = sys.argv
    sys.argv = ["bst_native_build_tracer.py", "report", str(path)]
    try:
        assert main() == 1
    finally:
        sys.argv = argv
    assert "no trace events could be parsed" in capsys.readouterr().err


def test_an_option_after_the_positionals_is_a_usage_error(tmp_path, capsys):
    """`cmd` is argparse.REMAINDER, so a misplaced option was swallowed
    into the wrapped command and surfaced as a bare
    `FileNotFoundError: '--wrapped-log'` from subprocess.run."""
    from tools.bst_native_build_tracer import main

    import sys
    argv = sys.argv
    sys.argv = [
        "bst_native_build_tracer.py", "run", "PROJ", "OUT",
        "--wrapped-log", "/tmp/x", "--", "bst", "build", "all.bst",
    ]
    try:
        with pytest.raises(SystemExit) as excinfo:
            main()
    finally:
        sys.argv = argv
    assert excinfo.value.code == 2
    assert "options must come before the positional arguments" in capsys.readouterr().err
