"""UX-905: `tools/jobserver_arms.py` reads width at equal work, and refuses
a pair whose arms are mislabelled or whose mode never ran."""
import json

from tools import jobserver_arms


def _report(jobserver=None, decisions=(), peak=2, work=530):
    return {
        "jobserver": jobserver, "jobserver_auth": "fifo" if jobserver else None,
        "jobserver_pool": {"ceiling": jobserver} if jobserver else None,
        "jobserver_decisions": list(decisions),
        "wall_span_s": 100.0,
        "per_element_parallelism": [{"element": "giant.bst", "peak_work_concurrency": peak,
                                     "requested_jobs": 2, "work_process_count": work}],
    }


JOINED = {"element": "giant.bst", "decision": "joined", "policy": "cmake_meson"}


def test_a_true_pair_reads_both_widths_and_passes(tmp_path, capsys):
    off, auto = tmp_path / "off.json", tmp_path / "auto.json"
    off.write_text(json.dumps(_report()))
    auto.write_text(json.dumps(_report(4, [JOINED], peak=4)))
    assert jobserver_arms.main([str(off), str(auto)]) == 0
    out = capsys.readouterr().out
    assert "giant.bst" in out and "decision joined policy cmake_meson: 1" in out
    row = jobserver_arms.arms(_report(), _report(4, [JOINED], peak=4))["rows"][0]
    assert (row["off_peak"], row["auto_peak"], row["off_work"], row["auto_work"]) == (2, 4, 530, 530)


def test_an_auto_arm_with_no_mode_is_not_a_pair():
    assert jobserver_arms.arms(_report(), _report())["problems"] == [
        "the auto arm ran no jobserver"]


def test_an_auto_arm_that_decided_nothing_is_not_a_pair():
    assert jobserver_arms.arms(_report(), _report(4))["problems"] == [
        "the auto arm recorded no per-sandbox decision"]


def test_swapped_arms_are_named(tmp_path):
    off, auto = tmp_path / "off.json", tmp_path / "auto.json"
    off.write_text(json.dumps(_report(4, [JOINED])))
    auto.write_text(json.dumps(_report()))
    assert jobserver_arms.main([str(off), str(auto)]) == 1


def test_an_off_arm_that_ran_the_mode_is_named_even_beside_a_good_auto():
    problems = jobserver_arms.arms(_report(4, [JOINED]), _report(4, [JOINED]))["problems"]
    assert problems == ["the off arm ran a jobserver of 4"]
