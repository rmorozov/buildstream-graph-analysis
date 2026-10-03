"""UX-1335: an exact dev pin whose Requires-Python excludes the floor.

PR CI runs the newest Python only (UX-995), so a pin that drops the floor
reds main's `test (3.9)` cell alone; `hypothesis==6.168.3` did so on 15
merges unseen. The installed metadata carries each pin's Requires-Python.
"""

import importlib.metadata
import pathlib
import re
import sys

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - the floor's own cell
    tomllib = None

REPO = pathlib.Path(__file__).resolve().parents[2]


def _project():
    if tomllib is None:
        pytest.skip("tomllib arrives in 3.11; the newest-Python cell reads it")
    return tomllib.loads((REPO / "pyproject.toml").read_text())["project"]


def floor():
    m = re.search(r">=\s*(\d+\.\d+)", _project()["requires-python"])
    assert m, "requires-python names no floor"
    return m.group(1)


def offenders(requirements, at, requires_python_of):
    """Exact pins that apply at Python `at` and whose release excludes it."""
    env = {"python_version": at, "python_full_version": f"{at}.0", "extra": "dev"}
    out = []
    for text in requirements:
        req = Requirement(text)
        if req.marker is not None and not req.marker.evaluate(env):
            continue
        pinned = [s.version for s in req.specifier if s.operator == "=="]
        if not pinned:
            continue
        declared = requires_python_of(req.name, pinned[0])
        if declared and not SpecifierSet(declared).contains(f"{at}.0"):
            out.append(f"{req.name}=={pinned[0]} requires Python {declared}")
    return out


def _installed(name, version):
    try:
        dist = importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        return None
    if dist.version != version:
        return None
    return dist.metadata.get("Requires-Python")


def test_every_exact_dev_pin_admits_the_python_floor():
    project = _project()
    found = offenders(project["optional-dependencies"]["dev"], floor(), _installed)
    assert not found, f"pins that cannot install on {floor()}: {found}"


def test_an_unmarked_pin_above_the_floor_is_reported():
    meta = {("hypothesis", "6.168.3"): ">=3.10"}

    def lookup(name, version):
        return meta.get((name, version))

    assert offenders(["hypothesis==6.168.3"], "3.9", lookup) == ["hypothesis==6.168.3 requires Python >=3.10"]
    marked = ["hypothesis==6.168.3; python_version >= '3.10'"]
    assert offenders(marked, "3.9", lookup) == []
