"""UX-595: a model whose assumptions are visible beside its numbers.

`UX-234` published the fact base and declined to model. This is the
model, and the thing under test is not the arithmetic - which is
checked here against hand-computed Erlang C and against the two cases
where a closed form exists - but the *visibility*: no number may rest
on an assumption its printout does not name.

The assumptions are recorded by `_Assumed.on` where they enter the
arithmetic, so the guards below read the same list the computation
built rather than a second one kept in step with it.
"""
import json
import math
import os
import pathlib
import shutil
import statistics

import pytest

from bga import capacity_model
from bga.compare import MIN_BASELINE_RUNS

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

# Six finished runs on one machine, in microseconds. Mean 703.33 s,
# sample sd 105.39 s, CV^2 0.0225 - a real store's shape, not an
# exponential one, which is the whole reason M/M/c alone will not do.
SAMPLES = [600_000_000, 720_000_000, 660_000_000,
           900_000_000, 640_000_000, 700_000_000]


def _listing(rows):
    return {"project": "/p", "snapshots": rows}


def _row(stamp, duration_us, host_class="one machine", **extra):
    return dict({"stamp": stamp, "total_duration_us": duration_us,
                 "host_class": host_class, "incomplete_reason": None}, **extra)


def _one_class(samples=None, host_class="one machine"):
    return _listing([_row(f"2026010{n}T000000Z", value, host_class)
                     for n, value in enumerate(samples or SAMPLES, start=1)])


def _unwrapped(lines):
    """The printout as one string with its wrapping undone, so a guard
    reads what it says rather than where the column happened to fall."""
    return " ".join(line.strip() for line in lines)


def _answers(document, label="one machine"):
    entry = next(e for e in document["host_classes"]
                 if e["host_class"] == label)
    return {answer["name"]: answer for answer in entry["answers"]}


class TestTheArithmetic:
    @pytest.mark.parametrize("builders,load", [(1, 0.5), (2, 1.0), (4, 3.0),
                                               (10, 8.0), (20, 15.0)])
    def test_erlang_c_matches_the_factorial_form(self, builders, load):
        """The recurrence and the textbook formula, to 12 places. The
        recurrence exists because the factorial overflows first."""
        below = sum(load ** k / math.factorial(k) for k in range(builders))
        busy = load ** builders / math.factorial(builders) * (
            builders / (builders - load))
        assert capacity_model.erlang_c(builders, load) == pytest.approx(
            busy / (below + busy), rel=1e-12)

    def test_a_saturated_system_makes_everyone_wait(self):
        assert capacity_model.erlang_c(4, 4.0) == 1.0

    def test_one_builder_reduces_to_the_m_m_1_wait(self):
        """`Wq = rho / (mu - lambda)` at c=1, and the Allen-Cunneen
        factor is 1 on an exponential service time - so the closed form
        is reachable and this checks against it."""
        mean = 600_000_000.0
        # Exponential-shaped: mean and standard deviation equal, so
        # CV^2 is 1 and the correction (1 + CV^2)/2 is exactly 1.
        samples = [mean * f for f in (0.2, 0.4, 1.0, 2.4)]
        service = capacity_model.service_time(samples)
        assert service["cv2"] == pytest.approx(1.0, rel=0.05)
        rate = 40.0
        rate_us = rate / capacity_model.MICROSECONDS_PER_DAY
        document = capacity_model.model(
            _listing([_row(f"2026010{n}T000000Z", int(v))
                      for n, v in enumerate(samples, start=1)]), 1, rate)
        rho = rate_us * service["mean_us"]
        closed_form = rho / (1 / service["mean_us"] - rate_us)
        assert _answers(document)["wait_us"]["value"] == pytest.approx(
            closed_form * (1 + service["cv2"]) / 2, rel=1e-9)

    def test_the_measured_spread_is_what_bends_the_wait(self):
        """The store's CV^2 is 0.02, so the wait is about half what
        M/M/c would have said. If that correction were dropped the
        number would be the exponential one, which the store measured
        and contradicted."""
        document = capacity_model.model(_one_class(), 4, 400)
        entry = document["host_classes"][0]
        wait_us = _answers(document)["wait_us"]["value"]
        mmc_us = wait_us / ((1 + entry["service"]["cv2"]) / 2)
        assert mmc_us / 1e6 == pytest.approx(588.08, rel=1e-4)
        assert wait_us / 1e6 == pytest.approx(300.64, rel=1e-4)

    def test_the_service_time_is_the_stores_own_moments(self):
        service = capacity_model.service_time([float(v) for v in SAMPLES])
        assert service["mean_us"] == pytest.approx(statistics.fmean(SAMPLES))
        assert service["stdev_us"] == pytest.approx(statistics.stdev(SAMPLES))

    def test_the_queue_length_is_littles_law_on_the_wait(self):
        document = capacity_model.model(_one_class(), 4, 400)
        answers = _answers(document)
        rate_us = 400 / capacity_model.MICROSECONDS_PER_DAY
        assert answers["queue_length"]["value"] == pytest.approx(
            rate_us * answers["wait_us"]["value"])


class TestEveryNumberNamesWhatItAssumed:
    def test_no_published_number_assumes_nothing(self):
        document = capacity_model.model(_one_class(), 4, 400)
        for entry in document["host_classes"]:
            for answer in entry["answers"]:
                assert answer["assumes"], (
                    f"{answer['name']} is published with no assumptions "
                    f"beside it")

    def test_every_assumption_a_number_used_is_printed_on_its_own_line(self):
        """The Acceptance Test's mutation: drop one id from the printout
        while the model still uses it."""
        document = capacity_model.model(_one_class(), 4, 400)
        printed = capacity_model.render(document)
        for entry in document["host_classes"]:
            for answer in entry["answers"]:
                start = next(n for n, line in enumerate(printed)
                             if line.strip().startswith(
                                 capacity_model._UNITS[answer["name"]][0]))
                block = ""
                for line in printed[start + 1:]:
                    if not line.startswith("      "):
                        break
                    block += line
                for name in answer["assumes"]:
                    assert name in block, (
                        f"{answer['name']} used {name} and does not name "
                        f"it: {block!r}")

    def test_every_assumption_used_is_stated_once_below(self):
        document = capacity_model.model(_one_class(), 4, 400)
        printed = _unwrapped(capacity_model.render(document))
        for name in capacity_model._used(document):
            assert capacity_model.ASSUMPTIONS[name] in printed, (
                f"{name} is named beside a number and stated nowhere")
            assert printed.count(capacity_model.ASSUMPTIONS[name]) == 1, (
                f"{name} is stated more than once")

    def test_an_assumption_no_number_used_is_not_printed(self):
        """The other half: a legend of everything bga could assume
        teaches nothing about the numbers on this page."""
        document = capacity_model.model(_one_class(), 4, 400)
        printed = _unwrapped(capacity_model.render(document))
        unused = set(capacity_model.ASSUMPTIONS) - set(
            capacity_model._used(document))
        assert unused, "this fixture was meant to leave one unused"
        for name in unused:
            assert capacity_model.ASSUMPTIONS[name] not in printed, name

    def test_an_undeclared_assumption_cannot_be_recorded(self):
        assumed = capacity_model._Assumed()
        with pytest.raises(KeyError):
            assumed.on("the_machine_is_never_busy")

    def test_the_arrival_process_is_named_on_the_wait_and_not_on_the_use(self):
        """Utilization is `lambda x E[S] / c` - true whatever the
        arrival process is. The wait is not, and the two must not carry
        the same list or the list is decoration."""
        answers = _answers(capacity_model.model(_one_class(), 4, 400))
        assert "arrivals_poisson" not in answers["utilization"]["assumes"]
        assert "arrivals_poisson" in answers["wait_us"]["assumes"]

    def test_the_service_shape_is_named_only_where_it_is_used(self):
        answers = _answers(capacity_model.model(_one_class(), 4, 400))
        assert "service_general" not in answers["utilization"]["assumes"]
        assert "service_general" in answers["wait_us"]["assumes"]

    def test_littles_law_is_named_only_on_the_queue_length(self):
        answers = _answers(capacity_model.model(_one_class(), 4, 400))
        assert "littles_law" not in answers["wait_us"]["assumes"]
        assert "littles_law" in answers["queue_length"]["assumes"]


class TestWhatItRefuses:
    def test_a_class_below_the_sample_floor_is_not_modelled(self):
        document = capacity_model.model(
            _one_class(SAMPLES[:MIN_BASELINE_RUNS - 1]), 4, 400)
        entry = document["host_classes"][0]
        assert entry["answers"] == []
        assert entry["shortfall"]["need"] == MIN_BASELINE_RUNS
        assert str(MIN_BASELINE_RUNS) in "\n".join(
            capacity_model.render(document))

    def test_an_unstable_queue_publishes_no_wait(self):
        document = capacity_model.model(_one_class(), 4, 600)
        entry = document["host_classes"][0]
        assert [a["name"] for a in entry["answers"]] == ["utilization"]
        assert entry["refusal"]["check"] == "unstable_queue"
        assert entry["answers"][0]["value"] > 1

    def test_a_mix_of_machines_publishes_no_fleet_wide_number(self):
        document = capacity_model.model(_listing(
            [_row(f"2026010{n}T000000Z", 600_000_000, "ryzen")
             for n in range(1, 4)]
            + [_row(f"2026011{n}T000000Z", 1_200_000_000, "xeon")
               for n in range(1, 4)]), 4, 200)
        assert document["refusal"]["check"] == "cross_host_model"
        assert len(document["host_classes"]) == 2
        for entry in document["host_classes"]:
            for answer in entry["answers"]:
                assert "whole_arrival_stream" in answer["assumes"], (
                    "each class is modelled on the whole stream and does "
                    "not say so")

    def test_one_machine_makes_no_claim_about_a_split_stream(self):
        document = capacity_model.model(_one_class(), 4, 400)
        assert document["refusal"] is None
        assert "whole_arrival_stream" not in capacity_model._used(document)

    def test_an_unfinished_capture_is_not_a_service_time(self):
        rows = list(_one_class()["snapshots"])
        rows.append(_row("20260107T000000Z", 9_000_000_000,
                         incomplete_reason="interrupted"))
        document = capacity_model.model(_listing(rows), 4, 400)
        assert document["excluded_runs"] == 1
        assert document["host_classes"][0]["service"]["samples"] == len(SAMPLES)

    @pytest.mark.parametrize("builders,rate", [(0, 40), (-1, 40), (4, 0),
                                               (4, -1)])
    def test_a_fleet_that_cannot_exist_is_refused(self, builders, rate):
        with pytest.raises(ValueError):
            capacity_model.model(_one_class(), builders, rate)

    @pytest.mark.parametrize("spec", ["", "4", "4,", "four,40", "0,40",
                                      "4,0", "4,40,7"])
    def test_the_flag_refuses_what_is_not_a_fleet(self, spec):
        assert capacity_model.parse_capacity(spec) is None

    def test_the_flag_reads_a_fleet(self):
        assert capacity_model.parse_capacity(" 4 , 40 ") == (4, 40.0)


def _store(tmp_path, durations):
    (tmp_path / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    for nth, duration in enumerate(durations, start=1):
        run = tmp_path / ".bga" / "runs" / f"202601{nth:02d}T000000Z" / "run"
        run.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        path = run / "run-context.json"
        context = json.loads(path.read_text())
        context["wall_clock"] = {"start_us": 0, "end_us": duration}
        path.write_text(json.dumps(context))
    return str(tmp_path)


class TestTheReader:
    def test_the_command_prints_the_model_and_its_legend(self, tmp_path,
                                                         capsys):
        from tools.bga_snapshot import _capacity

        assert _capacity(_store(tmp_path, SAMPLES), "4,400") == 0
        out = capsys.readouterr().out
        assert "Utilization: 81.4%" in out
        assert "Wait before a build starts: 300.6s" in out
        assert "assumes " in out
        assert "arrivals_poisson" in out

    def test_a_mixed_store_exits_on_the_cross_host_code(self, tmp_path,
                                                        capsys):
        from bga.cli import EXIT_CODE_MISMATCHED_RUNS
        from tools.bga_snapshot import _capacity

        project = _store(tmp_path, SAMPLES)
        run = pathlib.Path(project) / ".bga/runs/20260101T000000Z/run"
        context = json.loads((run / "run-context.json").read_text())
        context["host_manifest"] = dict(context.get("host_manifest") or {},
                                        cpu_model="a different machine")
        (run / "run-context.json").write_text(json.dumps(context))
        assert _capacity(project, "4,400") == EXIT_CODE_MISMATCHED_RUNS
        assert "host classes" in capsys.readouterr().out

    def test_json_is_refused_rather_than_emitted_unstamped(self, tmp_path,
                                                           capsys):
        """`UX-190`: an unversioned payload is the drift, so the model
        prints and says why it does not publish."""
        from tools.bga_snapshot import _capacity

        assert _capacity(_store(tmp_path, SAMPLES), "4,400", "json") == 2
        assert "UX-190" in capsys.readouterr().err


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
