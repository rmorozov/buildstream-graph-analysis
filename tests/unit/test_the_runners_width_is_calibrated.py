"""UX-1004: the giant's wall at each width gives the runner's effective
core count and the knee past which more width stops paying."""
import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "calibrate_width", REPO / "examples/11-serial-giant/calibrate_width.py")
calibrate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(calibrate)

#: A 4-vCPU host on 2 hyperthreaded cores: width 4 buys 7% over width 2.
SMT = {1: 90.0, 2: 45.8, 4: 42.6, 6: 42.9, 8: 43.4}
#: 4 real cores that also pay for one oversubscribed step.
REAL = {1: 90.0, 2: 45.5, 4: 23.4, 6: 21.9, 8: 21.8}


def test_the_effective_count_is_t1_over_tw():
    eff = calibrate.effective(SMT)
    assert round(eff[2], 2) == 1.97 and round(eff[4], 2) == 2.11


def test_the_knee_stops_where_a_step_saves_under_the_gain():
    assert calibrate.knee(SMT) == 4
    assert calibrate.knee(REAL) == 6
    # a later step that pays again does not move a knee already reached
    assert calibrate.knee({1: 90.0, 2: 45.0, 4: 44.0, 6: 30.0}) == 2


def test_one_wall_per_width_through_a_fake_bst(tmp_path):
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs.get("env", {}).get("XDG_CONFIG_HOME")))
        if argv[:2] == ["bst", "build"] and argv[2] == "giant.bst":
            conf = pathlib.Path(kwargs["env"]["XDG_CONFIG_HOME"], "buildstream2.conf")
            assert f"max-jobs: {widths.pop(0)}" in conf.read_text()

    widths = [1, 2, 4]
    assert calibrate.main([str(tmp_path), "4", "1", "2"], run=run) == 0
    assert widths == []
    assert [c[0][:3] for c in calls].count(["bst", "artifact", "delete"]) == 3


def test_width_one_is_required():
    assert calibrate.main(["p", "2", "4"], run=lambda *a, **k: None) == 2


class TestTheLinesOverride:
    """UX-1009: `giant.bst`'s committed 9800 lines/unit is too slow to
    calibrate at width 1 on a slow single core (2013s measured, raw, on
    Graviton) - `CALIBRATE_GIANT_LINES` shrinks it for this script's own
    builds only, never moving the element's own default."""

    def test_unset_adds_no_option(self, monkeypatch):
        monkeypatch.delenv("CALIBRATE_GIANT_LINES", raising=False)

        assert calibrate.lines_option() == []

    def test_set_overrides_giant_lines(self, monkeypatch):
        monkeypatch.setenv("CALIBRATE_GIANT_LINES", "1800")

        assert calibrate.lines_option() == ["--option", "giant_lines", "1800"]

    def test_the_override_reaches_the_build_command(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CALIBRATE_GIANT_LINES", "1800")
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)

        calibrate.build_at(str(tmp_path), 1, run=run)

        build_calls = [c for c in calls if "build" in c]
        assert build_calls == [["bst", "--option", "giant_lines", "1800",
                                "build", "giant.bst"]]

    def test_the_override_reaches_the_delete_command(self, monkeypatch, tmp_path):
        # Unoptioned, it deletes another cache key's artifact: widths 2-16 read 2.14s.
        monkeypatch.setenv("CALIBRATE_GIANT_LINES", "1800")
        calls = []
        calibrate.build_at(str(tmp_path), 1, run=lambda argv, **k: calls.append(argv))

        assert calls[0] == ["bst", "--option", "giant_lines", "1800",
                            "artifact", "delete", "giant.bst"]


def test_the_ci_step_calibrates_every_width_and_runs_the_pinned_arm():
    ci = (REPO / ".github/workflows/ci.yml").read_text()
    step = ci[ci.index("Calibrate the runner's width"):]
    step = step[:step.index("\n      - name:")]
    assert "calibrate_width.py\" \"$PROJ\" 1 2 4 6 8" in step
    assert "bst --builders 2 build all.bst" in step
    assert "::notice::calibration" in step
