"""UX-1305/UX-1306: real-project.md's troubleshooting and disk text quote what the code prints."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

from tools import bst_native_build_tracer as tracer
from tools.native_trace import bwrap_shim

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs/guides/real-project.md"
TROUBLE = "## Troubleshooting: Plane 2 recorded zero processes"
DISK = "### Disk"
TRACER = ROOT / "tools/bst_native_build_tracer.py"


def _squash(text: str) -> str:
    return " ".join(text.split())


def _section(heading: str) -> str:
    text = GUIDE.read_text(encoding="utf-8")
    assert heading in text, f"real-project.md lost `{heading}`"
    return _squash(text.split(heading, 1)[1].split("\n---\n", 1)[0].split("\n## ", 1)[0])


def _help(*argv: str) -> str:
    env = {"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin", "COLUMNS": "200"}
    done = subprocess.run([sys.executable, "-m", "bga.cli", *argv, "--help"], capture_output=True, text=True, env=env)
    return _squash(done.stdout)


def test_the_env_var_the_shim_tells_the_user_to_set_is_named():
    source = (ROOT / "tools/native_trace/bwrap_shim.py").read_text(encoding="utf-8")
    told = re.search(r"set (BST_TRACE_\w+) if it lives somewhere else", source)
    assert told, "the shim no longer tells the user which variable to set"
    argv_max = re.search(r'os\.environ\.get\("(BST_TRACE_ARGV_MAX)"', source)
    assert argv_max, "the shim no longer reads BST_TRACE_ARGV_MAX"
    section = _section(TROUBLE)
    for name in (told.group(1), argv_max.group(1)):
        assert f"`{name}`" in section, f"the troubleshooting section does not name {name}"
    assert f"bga: set {told.group(1)} if it lives somewhere else." in section


def test_the_flags_named_are_flags_the_commands_have():
    section = _section(TROUBLE)
    for command in (("snapshot",), ("capture", "run")):
        text = _help(*command)
        for flag in ("--diagnose", "--no-inject"):
            assert flag in text, f"`bga {' '.join(command)}` has no {flag}"
            assert flag in section
    assert "bga doctor --capture" in section and "--capture" in _help("doctor")


@pytest.mark.parametrize("tasks", [0, 3])
def test_the_diagnose_readings_are_the_sentences_it_prints(tmp_path, tasks):
    empty = tmp_path / "d.jsonl"
    empty.write_text("")
    printed = _squash(tracer.format_capture_diagnostics(str(empty), sandbox_tasks=tasks))
    section = _section(TROUBLE)
    zero = "The bwrap shim ran 0 times."
    if tasks == 0:
        reading = shown = "This build launched no sandbox at all - every element was a cache hit"
    else:
        reading = (
            "This build ran N element task(s), so sandboxes were launched and the shim was not called by any of them"
        )
        shown = reading.replace("N element", f"{tasks} element")
    for quote in ("Capture diagnostics (UX-146)", zero):
        assert quote in printed and quote in section
    assert shown in printed and reading in section


def test_the_untraced_warning_and_no_inject_line_are_quoted(tmp_path):
    warning = tracer.format_untraced_build_warning(0, 3)
    section = _section(TROUBLE)
    assert "PLANE 2 CAPTURED NOTHING" in warning and "PLANE 2 CAPTURED NOTHING" in section
    line = "--no-inject was set, so nothing was captured and no process record exists."
    record = tmp_path / "d.jsonl"
    record.write_text(
        '{"element": "a.bst", "injected": false, "real_bwrap": "/usr/bin/bwrap", "real_bwrap_executable": true}\n'
    )
    assert line in section and line in _squash(tracer.format_capture_diagnostics(str(record), no_inject=True))


def test_the_self_test_failures_are_the_ones_the_probe_raises(tmp_path):
    section = _section(TROUBLE)
    assert bwrap_shim.SELF_TEST_ARGV in section and "bga-shim-ok" in section
    plain = tmp_path / "bwrap"
    plain.write_text("#!/bin/sh\n")
    plain.chmod(0o644)
    with pytest.raises(tracer.TraceError) as denied:
        tracer.probe_bwrap_shim(str(plain))
    assert "cannot be executed" in str(denied.value) and "cannot be executed" in section
    with pytest.raises(tracer.TraceError) as gone:
        tracer.probe_bwrap_shim(str(tmp_path / "nope"))
    assert "could not be run" in str(gone.value) and "could not be run" in section
    source = _squash(TRACER.read_text(encoding="utf-8"))
    for quote in ("ran but did not answer its own probe", "no real bwrap found on PATH"):
        assert quote in source and quote in section


def test_the_pilot_links_the_section():
    pilot = (ROOT / "docs/guides/pilot.md").read_text(encoding="utf-8")
    assert "real-project.md#troubleshooting-plane-2-recorded-zero-processes" in pilot


def test_the_tracer_overwrites_the_real_bwrap_variable_as_the_section_says():
    source = TRACER.read_text(encoding="utf-8")
    assert 'env["BST_TRACE_REAL_BWRAP"] = real_bwrap' in source
    assert "real_bwrap = install_bwrap_shim(shim_dir)" in source
    assert 'real_bwrap = shutil.which("bwrap")' in source
    section = _section(TROUBLE)
    assert 'sets this variable itself, to `shutil.which("bwrap")`' in section
