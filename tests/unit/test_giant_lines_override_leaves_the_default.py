"""UX-1009: `giant_lines` (project.conf) lets Graviton CI shrink
`giant.bst`'s generated units for its own calibration run, without
moving the 9800 every other `bst build` still gets - `--option` only
overrides what `bst show`/`bst build` resolve to, never the file on
disk.
"""
import pathlib

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
PROJECT = REPO / "examples/11-serial-giant/project.conf"
GIANT = REPO / "examples/11-serial-giant/elements/giant.bst"


def test_the_committed_default_is_still_9800():
    project = yaml.safe_load(PROJECT.read_text())

    assert project["options"]["giant_lines"]["default"] == "9800"


def test_giant_bst_reads_the_variable_not_a_literal():
    giant = yaml.safe_load(GIANT.read_text())

    commands = giant["config"]["configure-commands"]
    assert any("%{giant_lines}" in cmd for cmd in commands)
    assert not any("9800" in cmd for cmd in commands)
