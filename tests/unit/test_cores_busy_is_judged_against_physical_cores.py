"""UX-1364: the run context carries physical cores; pool size and cores-busy name both denominators.

Page: styleguide §1b, a published field reaches a reader.
"""

import contextlib
import io
import json
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import Browser, find_chrome

from bga import hostinfo
from tools import _run_context_common as common
from tools.bga_snapshot import cpu_topology

FIXTURE = REPO / "tests/fixtures/macro_micro"
chrome = find_chrome()
NO_CHROME = "no chrome/chromium for the geometry guards (set BGA_CHROME)"
BOTH = "4 logical / 2 physical"


def _sysfs(root, cpus):
    """`cpus` is [(package, core)] per logical cpu."""
    for number, (package, core) in enumerate(cpus):
        topo = root / f"cpu{number}" / "topology"
        topo.mkdir(parents=True)
        (topo / "physical_package_id").write_text(f"{package}\n")
        (topo / "core_id").write_text(f"{core}\n")
    return str(root)


def _run(tmp_path, physical):
    """macro_micro's run, 4 logical CPUs, `physical` cores (or no field), plane2 beside it."""
    snap = tmp_path / "snap"
    shutil.copytree(FIXTURE / "run", snap / "run")
    shutil.copy(FIXTURE / "plane2.json", snap / "plane2.json")
    path = snap / "run" / "run-context.json"
    context = json.loads(path.read_text())
    context["host_cpu_count"] = 4
    context.pop("host_physical_cores", None)
    if physical is not None:
        context["host_physical_cores"] = physical
        context["host_manifest"]["physical_cores"] = physical
    path.write_text(json.dumps(context))
    return snap / "run"


def _cli(*argv):
    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
        main(list(argv))
    return buffer.getvalue()


def test_the_capture_records_the_cores_ux_1002_prints(tmp_path, monkeypatch):
    sysfs = _sysfs(tmp_path / "cpu", [(0, 0), (0, 0), (0, 1), (0, 1)])
    assert common.cpu_topology_counts(sysfs) == (4, 2, 1)
    assert cpu_topology(sysfs, str(tmp_path / "none")) == "cpu: 4 logical, 2 cores, 1 socket"
    monkeypatch.setattr(common, "cpu_topology_counts", lambda sysfs="", allowed=None: (4, 2, 1))
    assert common.host_physical_cores() == 2


def test_the_run_context_writer_carries_the_field(monkeypatch):
    monkeypatch.setattr(common, "host_physical_cores", lambda: 2)
    monkeypatch.setattr(common, "host_cpu_count", lambda: 4)
    context = {}
    common.add_cpu_capacity_fields(context, None, None, None, None)
    assert context["host_physical_cores"] == 2
    assert hostinfo.collect(with_toolchain=False)["physical_cores"] == 2


def test_the_pool_line_names_both(tmp_path):
    assert f"Pool size: 4, from host_cpu_count ({BOTH})" in _cli("analyze", str(_run(tmp_path, 2)))


def test_an_old_run_context_says_physical_unknown(tmp_path):
    out = _cli("analyze", str(_run(tmp_path, None)))
    assert "Pool size: 4, from host_cpu_count (4 logical / physical unknown)" in out


def test_correlate_states_both_where_the_cores_busy_is_judged(tmp_path):
    out = _cli("correlate", str(_run(tmp_path, 2)))
    assert f"0.90 cores busy of {BOTH} — it is waiting" in out
    assert f"kept under half their granted cores busy of {BOTH}: lib-b.bst 1.86 of 4" in out
    assert " cores busy of " not in _cli("correlate", str(_run(tmp_path / "old", None)))


def test_equal_denominators_are_one_number(tmp_path):
    assert hostinfo.core_denominators(4, 4) == "4"
    assert " cores busy of " not in _cli("correlate", str(_run(tmp_path, 4)))


@pytest.mark.skipif(chrome is None, reason=NO_CHROME)
@pytest.mark.medium
@pytest.mark.parametrize(("physical", "said"), [(2, BOTH), (None, "4 logical / physical unknown")])
def test_the_page_names_both(tmp_path, physical, said):
    uri = pages.export_uri(_run(tmp_path, physical), tmp_path / "out")
    with Browser(chrome) as browser:
        text = browser.measure(uri, "document.body.textContent.replace(/\\s+/g, ' ')", 1440, 900)
    assert f"· {said}" in text
