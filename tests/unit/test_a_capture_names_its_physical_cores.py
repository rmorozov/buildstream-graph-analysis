"""UX-1002: the capture context counts physical cores and sockets, not only
`nproc` - a 4-vCPU runner on 2 hyperthreaded cores is a different host class."""
import pytest

from tools.bga_snapshot import _capture_context, cpu_topology


def _sysfs(tmp_path, layout):
    """`layout` is one `(package, core)` per logical CPU."""
    for n, (package, core) in enumerate(layout):
        topo = tmp_path / f"cpu{n}" / "topology"
        topo.mkdir(parents=True)
        (topo / "physical_package_id").write_text(f"{package}\n")
        (topo / "core_id").write_text(f"{core}\n")
    (tmp_path / "cpufreq").mkdir()
    return str(tmp_path)


@pytest.mark.parametrize(("layout", "line"), [
    ([(0, 0), (0, 1), (0, 2), (0, 3)], "cpu: 4 logical, 4 cores, 1 socket(s)"),
    ([(0, 0), (0, 0), (0, 1), (0, 1)], "cpu: 4 logical, 2 cores, 1 socket(s)"),
    ([(0, 0), (1, 0)], "cpu: 2 logical, 2 cores, 2 socket(s)"),
])
def test_hyperthreads_and_sockets_are_told_apart(tmp_path, layout, line):
    assert cpu_topology(_sysfs(tmp_path, layout), str(tmp_path / "no-cpuinfo")) == line


def test_the_cpu_model_is_named(tmp_path):
    info = tmp_path / "cpuinfo"
    info.write_text("processor\t: 0\nmodel name\t: AMD EPYC 7763 64-Core Processor\n"
                    "processor\t: 1\nmodel name\t: AMD EPYC 7763 64-Core Processor\n")
    line = cpu_topology(_sysfs(tmp_path, [(0, 0), (0, 0)]), str(info))
    assert line == "cpu: 2 logical, 1 cores, 1 socket(s), AMD EPYC 7763 64-Core Processor"


def test_an_unreadable_topology_says_so(tmp_path):
    assert cpu_topology(str(tmp_path / "absent")) == "cpu: unreadable"


def test_the_context_carries_the_line():
    assert "\ncpu: " in _capture_context("p", ["bst", "build"], {})
