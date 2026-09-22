"""UX-916: `style_for_make_version` has two branches and, until the
pins landed, one live one - every example sandbox carried the staging
host's own make. The two `switch-*` arms are the fix: identical
elements whose `PATH` selects a different staged series, so one
capture crosses the switch in both directions.

This file guards the two halves that hold without a sandbox: that each
arm names a real staged alias, and that
`check_jobserver_width.check_switch` reads the report rather than
re-deriving the style it is supposed to be checking.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

from tools import nix_store_fetch

REPO_ROOT = Path(__file__).resolve().parents[2]
ELEMENTS = REPO_ROOT / "examples" / "11-serial-giant" / "elements"


def _width_check_module():
    path = (REPO_ROOT / "examples" / "11-serial-giant"
            / "check_jobserver_width.py")
    spec = importlib.util.spec_from_file_location("_width_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WIDTH_CHECK = _width_check_module()


def _report(rows):
    return {"jobserver_decisions": rows}


def _row(element, version, style):
    return {"element": element, "sandbox_make": version, "auth_style": style}


def _passing_rows():
    return [_row(element, version + ".1", style)
            for element, (version, style)
            in WIDTH_CHECK.SWITCH_ARMS.items()]


def _run(tmp_path, rows):
    path = tmp_path / "plane2.json"
    path.write_text(json.dumps(_report(rows)), encoding="utf-8")
    return WIDTH_CHECK.check_switch(str(path))


class TestEachArmNamesAStagedAlias:
    """The `.bst` files are the declaration; `nix_store_fetch` is what
    actually puts a make at that path. A `PATH` naming a directory no
    pin stages is an arm that silently falls through to `/usr/bin`."""

    def test_every_arm_selects_a_directory_a_pin_stages(self):
        staged = {str(Path(nix_store_fetch.alias_path(name)).parent)
                  for name in nix_store_fetch.PINS["x86_64"]["paths"]}

        for element in WIDTH_CHECK.SWITCH_ARMS:
            parsed = yaml.safe_load(
                (ELEMENTS / element).read_text(encoding="utf-8"))
            first = parsed["environment"]["PATH"].split(":")[0]
            assert first in staged, (
                f"{element} leads its PATH with {first!r}, which "
                f"nix_store_fetch stages nothing at: {sorted(staged)}")

    def test_the_two_arms_do_not_select_the_same_make(self):
        leads = {element: yaml.safe_load(
            (ELEMENTS / element).read_text(encoding="utf-8")
        )["environment"]["PATH"].split(":")[0]
            for element in WIDTH_CHECK.SWITCH_ARMS}

        assert len(set(leads.values())) == len(leads), leads

    def test_each_arm_selects_the_series_its_own_expectation_names(self):
        """`switch-4-2.bst` pointed at the 4.4 alias would still pass
        the two rows above, and would then be checked against `fd`
        while running a make that speaks `fifo`."""
        for element, (version, _style) in WIDTH_CHECK.SWITCH_ARMS.items():
            parsed = yaml.safe_load(
                (ELEMENTS / element).read_text(encoding="utf-8"))
            lead = parsed["environment"]["PATH"].split(":")[0]
            series = version.split()[-1]
            assert Path(lead).name == series, (
                f"{element} expects {version} but selects {lead}")

    def test_both_arms_are_built(self):
        depends = yaml.safe_load(
            (ELEMENTS / "all.bst").read_text(encoding="utf-8"))["depends"]

        assert set(WIDTH_CHECK.SWITCH_ARMS) <= set(depends), depends


class TestTheCheckReadsTheReport:
    def test_a_capture_crossing_the_switch_passes(self, tmp_path):
        assert _run(tmp_path, _passing_rows()) is None

    def test_both_arms_on_one_make_is_refused(self, tmp_path):
        """The defect the row exists to end: one staged make, so the
        switch has one live branch and the capture proves nothing."""
        rows = [_row(element, "GNU Make 4.4.1", "fifo")
                for element in WIDTH_CHECK.SWITCH_ARMS]

        error = _run(tmp_path, rows)

        assert error and "not the GNU Make 4.2" in error, error

    def test_an_arm_on_the_wrong_style_is_refused(self, tmp_path):
        """`sandbox_make` and `auth_style` are written by two different
        readings (a probe and `style_for_make_version`); a 4.2 that
        reports `fifo` is the switch itself being wrong."""
        rows = _passing_rows()
        rows[-1] = dict(rows[-1], auth_style="fifo")

        error = _run(tmp_path, rows)

        assert error and "auth_style" in error, error

    def test_a_missing_arm_is_refused(self, tmp_path):
        """An element BuildStream never built, or one whose probe never
        ran, must read as missing rather than as one arm passing."""
        error = _run(tmp_path, _passing_rows()[:1])

        assert error and "no jobserver_decisions row" in error, error

    def test_a_report_with_no_decisions_at_all_is_refused(self, tmp_path):
        error = _run(tmp_path, [])

        assert error and "no jobserver_decisions row" in error, error

    def test_an_unprobed_arm_is_refused(self, tmp_path):
        """`write_decisions_with_sandbox_make` adds nothing when the
        probe is absent, so the row is there with neither key. Reading
        that as a pass would make the whole check optional."""
        rows = _passing_rows()
        rows[-1] = {"element": rows[-1]["element"]}

        error = _run(tmp_path, rows)

        assert error and "not the GNU Make 4.2" in error, error

    def test_the_arms_and_the_pins_name_the_same_series(self):
        """Two tables, one fact: the check's expectations and the pin
        table have to move together or CI asserts a series nothing
        stages."""
        pinned = {name.split("-", 1)[1]
                  for name in nix_store_fetch.PINS["x86_64"]["paths"]}
        expected = {version.split()[-1]
                    for version, _style in WIDTH_CHECK.SWITCH_ARMS.values()}

        assert expected == pinned


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
