"""UX-891: the CPU floor divides by the machine's cores, not the builders.

Every floor in Part 16 divides work by a *builder slot* count, so `LB`
certifies against the scheduler's width and never against the machine's.
`tests/fixtures/macro_micro` certifies four slots 29.1% used with zero
headroom while 1.60 of its four cores were busy over the same span.

The trap this guard clears: that fixture has `PROCESS` 4 and
`host_cpu_count` 4, so a floor divided by the *builder* count returns
the same number. The second case runs a copy with `host_cpu_count`
edited to 8, where the two candidate divisors give 8723282 and 17446564.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

FIXTURE = Path("tests/fixtures/macro_micro")
GOLDEN = Path("tests/fixtures/golden/mixed_task_kinds")

# `total_cpu_us` and the process census `tests/fixtures/macro_micro`
# carries, written down rather than read back from the fixture: a guard
# that derives its expectation from the same file moves with a defect
# in it.
TOTAL_CPU_US = 69_786_259
MEASURED, UNMEASURED = 663, 150
LB_US = 43_200_000

# The note `tests/fixtures/golden/mixed_task_kinds` prints today, byte
# for byte. A run with no Plane 2 gains no CPU floor and no clause.
GOLDEN_NOTE = (
    "LB/Efficiency Score certify against this run's recorded resource "
    "capacities (builders/fetchers/pushers), not real host CPU cores or any "
    "declared CPU budget - native build-system parallelism (--max-jobs) is a "
    "separate, currently unmodeled axis. Capacity checks "
    "(over/under-subscription, memory) did not run for this run - missing: "
    "native_max_jobs, governing core count (host_cpu_count/cpu_budget). They "
    "are inert here, not passing; a wrapped log records --max-jobs on its own "
    "first line, or declare the missing value explicitly at extraction time."
)


def _floors(tmp_path, run_dir, plane2=None):
    out = tmp_path / "report.json"
    argv = ["analyze", str(run_dir), "-f", "json", "-o", str(out)]
    if plane2:
        argv += ["--plane2", str(plane2)]
    else:
        argv += ["--no-plane2"]
    proc = subprocess.run(
        [sys.executable, "-c",
         f"from bga.cli import main; raise SystemExit(main({argv!r}))"],
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return json.loads(out.read_text())["floors"]


def _fixture_with_cores(tmp_path, cores, key="host_cpu_count"):
    """A copy of `macro_micro` whose governing core count is `cores`,
    with `resource_capacities['PROCESS']` left at 4 - the two divisors
    only differ where the fixture's own equality is broken."""
    run_dir = tmp_path / "run"
    shutil.copytree(FIXTURE / "run", run_dir)
    context_path = run_dir / "run-context.json"
    context = json.loads(context_path.read_text())
    context[key] = cores
    assert context["resource_capacities"]["PROCESS"] == 4
    context_path.write_text(json.dumps(context))
    return run_dir


def test_the_floor_is_the_measured_cpu_over_the_governing_cores(tmp_path):
    """The fixture as it stands: four cores, and the floor below LB."""
    floors = _floors(tmp_path, FIXTURE / "run", FIXTURE / "plane2.json")

    assert floors["lb"] == LB_US
    assert floors["lb_cpu_us"] == TOTAL_CPU_US // 4 == 17_446_564
    assert floors["lb_cpu_coverage"] == MEASURED / (MEASURED + UNMEASURED)
    assert floors["lb_cpu_governing_cores"] == 4
    assert floors["lb_cpu_cores_source"] == "host_cpu_count"
    assert floors["lb_cpu_binds"] is False


def test_the_divisor_is_the_cores_and_not_the_builder_slots(tmp_path):
    """The trap: `PROCESS` stays 4 while the host has 8 cores. A floor
    that read the builder count would still say 17446564 here."""
    floors = _floors(
        tmp_path, _fixture_with_cores(tmp_path, 8), FIXTURE / "plane2.json")

    assert floors["lb_cpu_us"] == TOTAL_CPU_US // 8 == 8_723_282
    assert floors["lb_cpu_governing_cores"] == 8


def test_a_declared_budget_governs_over_the_detected_host(tmp_path):
    """`cpu_budget` is the ceiling its operator asked to be held to, so
    it wins over the detected count and says so."""
    floors = _floors(
        tmp_path, _fixture_with_cores(tmp_path, 1, key="cpu_budget"),
        FIXTURE / "plane2.json")

    assert floors["lb_cpu_governing_cores"] == 1
    assert floors["lb_cpu_cores_source"] == "cpu_budget"
    assert floors["lb_cpu_us"] == TOTAL_CPU_US > LB_US
    # The whole point of the axis: on this machine the cores bind and
    # the builder slots do not.
    assert floors["lb_cpu_binds"] is True


def test_no_plane_two_leaves_the_floors_and_the_note_as_they_were(tmp_path):
    """Absent, never zero - and the standing note byte-identical."""
    floors = _floors(tmp_path, GOLDEN)

    assert [key for key in floors if key.startswith("lb_cpu")] == []
    assert floors["capacity_model_note"] == GOLDEN_NOTE
