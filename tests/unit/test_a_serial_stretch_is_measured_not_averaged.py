"""UX-1358: an element's serial stretch is wall time at <=1 busy work process, not its mean.

holds: a 40 s autoreconf loop beside 60 s at six compilers is 40 s serial, owned by autoreconf; correlate then
refuses "already compute-bound" and names it, and the element card's advice carries the seconds and the owner.
"""

import json
import os
import pathlib
import shutil
import subprocess

import pytest

from bga.correlate import _SERIAL_SHARE_LINE, ElementJoin, _plane2_view, _recommend
from tools.bst_native_build_tracer import compute_per_element_parallelism

REPO = pathlib.Path(__file__).resolve().parents[2]
ELEMENT = "bootstrap/gcc.bst"
AUTORECONF = "/bin/perl -w /bin/autoreconf2.69 -I ../config -fvi"


def _record(start, end, cmd, pid):
    return {"open": False, "element": ELEMENT, "start_ts": start, "end_ts": end, "cmd": cmd, "pid": pid, "ppid": 2}


def _records():
    rows = [_record(0.0, 100.0, "sh -c -e build", 1), _record(0.0, 100.0, "make -j6", 2)]
    # 0-40 s: ten autoreconf runs one after another, each with an m4 child - no work binary at all.
    for i in range(10):
        rows.append(_record(4.0 * i, 4.0 * i + 4.0, AUTORECONF, 10 + i))
        rows.append(_record(4.0 * i + 1.0, 4.0 * i + 2.0, "m4 -P aclocal.m4", 30 + i))
    # 40-100 s: six compilers at once, back to back - a mean of 6 over the work span.
    for slot in range(6):
        for i in range(6):
            rows.append(_record(40.0 + 10.0 * i, 50.0 + 10.0 * i, f"cc1 -quiet f{slot}_{i}.c", 100 + slot * 6 + i))
    return rows


@pytest.fixture(scope="module")
def profile():
    (row,) = compute_per_element_parallelism(_records())
    return row


def test_the_stretch_is_the_time_at_one_work_process_or_none(profile):
    assert profile["mean_work_concurrency"] == pytest.approx(6.0), profile
    assert profile["element_span_s"] == pytest.approx(100.0)
    assert profile["serial_wall_s"] == pytest.approx(40.0), profile
    assert profile["serial_share"] == pytest.approx(0.4)


def test_autoreconf_owns_the_stretch(profile):
    owners = profile["serial_owners"]
    assert owners[0] == {"signature": AUTORECONF, "wall_s": pytest.approx(40.0)}, owners
    assert [owner["signature"] for owner in owners][1:] == ["m4 -P aclocal.m4"], owners


def _joined(profile):
    view = _plane2_view({"per_element_parallelism": [profile]})[ELEMENT]
    return ElementJoin(
        element=ELEMENT,
        on_critical_path=True,
        critical_path_share=0.18,
        potential_saving_us=1_837_400_000,
        saving_share=0.13,
        cores_busy=2.57,
        serial_stretch=view["serial_stretch"],
    )


def test_correlate_refuses_compute_bound_and_names_the_owner(profile):
    advice = {step["id"]: step["text"] for step in _recommend(_joined(profile))}
    assert "already-compute-bound" not in advice, advice
    assert "autoreconf2.69" in advice["serial-stretch"] and "40.0 s of its" in advice["serial-stretch"], advice
    assert profile["serial_share"] > _SERIAL_SHARE_LINE


_PROBE = r"""
const { readFileSync } = await import("node:fs");
const views = await import("%(views)s");
const payload = JSON.parse(readFileSync(%(payload)s, "utf8"));
const record = views.elementFacts(payload).get(%(uid)s);
console.log(JSON.stringify({ advice: record.advice.map((a) => a.text) }));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_element_card_shows_the_seconds_and_the_owner(profile, tmp_path):
    joined = _joined(profile)
    row = {
        "element": ELEMENT,
        "serial_stretch": joined.serial_stretch,
        "recommendations": _recommend(joined),
    }
    payload = {"critical_path_detail": [{"element_uid": ELEMENT, "share_of_path": 0.18}], "element_join": [row]}
    doc = tmp_path / "payload.json"
    doc.write_text(json.dumps(payload), encoding="utf-8")
    script = _PROBE % {
        "views": (REPO / "tests/viewer.mjs").as_uri(),
        "payload": json.dumps(str(doc)),
        "uid": json.dumps(ELEMENT),
    }
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=120,
        env={**os.environ, "BGA_DOM_SHIM": (REPO / "tests/dom_shim.mjs").as_uri()},
    )
    assert done.returncode == 0, done.stderr[-3000:]
    seen = json.loads(done.stdout)
    assert not any("compute-bound" in text for text in seen["advice"]), seen
    assert any("40.0 s of its" in text and "autoreconf2.69" in text for text in seen["advice"]), seen
