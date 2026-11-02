"""UX-1366 review: `requested_jobs` is the recipe's observed `-jN`; `resolved_jobs` the width granted.

A `--max-jobs 4` build: autotools' `make -j1 install` stays 1 at a width of 4, a `notparallel` element
resolves to 1, and a sandbox tagged by its build root's last segment finds its uid's width.
"""

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.plane2 import PINNED_FINDING, WIDTH_UNKNOWN_FINDING, apply_resolved_widths, resolved_widths
from tools.bst_native_build_tracer import compute_per_element_parallelism

MAX_JOBS = 4


def _record(element, cmd, start, end):
    return {"pid": 1, "ppid": 0, "element": element, "cmd": cmd, "start_ts": start, "end_ts": end, "open": False}


def _compiles(element, count, overlap):
    step = 0.0 if overlap else 3.0
    return [_record(element, "/usr/libexec/gcc/cc1 -quiet a.c", i * step, i * step + 3.0) for i in range(count)]


def _graph(tmp_path, elements):
    graph = tmp_path / "graph.json"
    graph.write_text(json.dumps({"elements": elements}), encoding="utf-8")
    return resolved_widths(str(graph))


def _capture(tmp_path, records, elements):
    """The tracer's own profiles over `records`, scored against `graph.json` as `bga analyze` does."""
    report = {"per_element_parallelism": compute_per_element_parallelism(records)}
    apply_resolved_widths(report, _graph(tmp_path, elements))
    return {row["element"]: row for row in report["per_element_parallelism"]}


def _max_jobs_4(tmp_path):
    records = [
        # autotools: the build's width rides MAKEFLAGS, the install step writes its own -j1.
        _record("autotools.bst", "make PREFIX=/usr", 0.0, 6.0),
        _record("autotools.bst", "make -j1 PREFIX=/usr install", 6.0, 7.0),
        *_compiles("autotools.bst", 8, overlap=True),
        # notparallel: BuildStream composes -j1 itself.
        _record("serial.bst", "make -j1", 0.0, 12.0),
        *_compiles("serial.bst", 4, overlap=False),
    ]
    elements = [
        {"uid": "autotools.bst", "max_jobs": MAX_JOBS, "notparallel": None},
        {"uid": "serial.bst", "max_jobs": MAX_JOBS, "notparallel": True},
    ]
    return _capture(tmp_path, records, elements)


def test_a_real_j1_install_step_stays_one_at_a_granted_four(tmp_path):
    row = _max_jobs_4(tmp_path)["autotools.bst"]
    assert (row["requested_jobs"], row["resolved_jobs"]) == (1, MAX_JOBS)
    assert PINNED_FINDING not in row["findings"]


def test_a_notparallel_element_resolves_to_one_and_is_pinned(tmp_path):
    row = _max_jobs_4(tmp_path)["serial.bst"]
    assert (row["requested_jobs"], row["resolved_jobs"]) == (1, 1)
    assert PINNED_FINDING in row["findings"]


def _build_root_tags(tmp_path):
    """fdsdk's `build-root` override: two uncorrelated sandboxes tagged `libsepol` and `libselinux`."""
    records = [
        _record("libsepol", "make -j1", 0.0, 6.0),
        *_compiles("libsepol", 2, overlap=False),
        _record("libselinux", "make -j1 install", 0.0, 6.0),
        *_compiles("libselinux", 4, overlap=True),
        _record("gettext", "make -j1 install", 0.0, 6.0),
        _record("orphan", "make -j1 install", 0.0, 6.0),
        _record("bootstrap/gettext.bst", "ninja -j4", 0.0, 6.0),
        # the hook's own tag for an unset element, beside an element that happens to share the name.
        _record("unknown", "make -j1 install", 0.0, 6.0),
    ]
    elements = [
        {"uid": "bootstrap/libsepol.bst", "max_jobs": MAX_JOBS, "notparallel": True},
        {"uid": "bootstrap/libselinux.bst", "max_jobs": MAX_JOBS, "notparallel": None},
        {"uid": "bootstrap/gettext.bst", "max_jobs": MAX_JOBS, "notparallel": None},
        {"uid": "components/gettext.bst", "max_jobs": MAX_JOBS, "notparallel": None},
        {"uid": "tools/unknown.bst", "max_jobs": MAX_JOBS, "notparallel": None},
    ]
    return _capture(tmp_path, records, elements)


def test_a_build_root_tag_finds_its_elements_width(tmp_path):
    rows = _build_root_tags(tmp_path)
    assert (rows["libsepol"]["requested_jobs"], rows["libsepol"]["resolved_jobs"]) == (1, 1)
    assert PINNED_FINDING in rows["libsepol"]["findings"]
    assert (rows["libselinux"]["requested_jobs"], rows["libselinux"]["resolved_jobs"]) == (1, MAX_JOBS)
    assert PINNED_FINDING not in rows["libselinux"]["findings"]


def test_a_tag_no_one_uid_answers_says_the_width_is_unknown(tmp_path):
    """`gettext` names two uids, `orphan` none, `unknown` is no element: none is called pinned on its argv -j1."""
    rows = _build_root_tags(tmp_path)
    for name in ("gettext", "orphan", "unknown"):
        assert rows[name]["resolved_jobs"] is None
        assert rows[name]["findings"] == [WIDTH_UNKNOWN_FINDING]
