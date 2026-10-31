"""UX-1358: a serial stretch is sampled wall time at or under one core busy, never a count of live processes.

holds: a linker driver waiting on its linker (two processes, one core) is serial; one four-thread process
(one process, four cores) is not; an autoreconf loop with no classified work binary is serial and named;
a low window on a saturated host is contention, not serial; children reaped between ticks still count; the
invocation log alone starts the sampler; and an element with no samples is unknown - correlate then says so
instead of "already compute-bound".
"""

import json
import os
import pathlib
import shutil
import subprocess

import pytest

from bga.correlate import _SERIAL_SHARE_LINE, ElementJoin, _plane2_view, _recommend
from tools.bst_native_build_tracer import (
    _TICKS_PER_S,
    SERIAL_CORES_LINE,
    ElementCpuSampler,
    compute_per_element_parallelism,
    element_cpu_windows,
    read_element_cpu_samples,
)

REPO = pathlib.Path(__file__).resolve().parents[2]
ELEMENT = "bootstrap/gcc.bst"
AUTORECONF = "/bin/perl -w /bin/autoreconf2.69 -I ../config -fvi"
TICK = 2.0


def _record(start, end, cmd, pid):
    return {"open": False, "element": ELEMENT, "start_ts": start, "end_ts": end, "cmd": cmd, "pid": pid, "ppid": 2}


def _flat(cores, start=0.0, end=100.0, idle=2.0):
    """Sampler windows at one rate, one tick apart, beside `idle` idle host cores."""
    count = int((end - start) / TICK)
    return {ELEMENT: [(start + TICK * i, start + TICK * (i + 1), cores, idle) for i in range(count)]}


def _profile(records, windows):
    (row,) = compute_per_element_parallelism(records, windows)
    return row


def test_a_parent_waiting_on_its_child_is_two_processes_and_one_core():
    # collect2 waits for ld: both classified work, so a process count reads two.
    records = [_record(0.0, 100.0, "/usr/bin/collect2 -o cc1", 1), _record(0.0, 100.0, "/usr/bin/ld -o cc1", 2)]
    row = _profile(records, _flat(1.0))
    assert row["observed_process_concurrency"] == pytest.approx(2.0), row
    assert row["serial_wall_s"] == pytest.approx(100.0) and row["serial_share"] == pytest.approx(1.0), row
    assert row["observed_process_concurrency_in_serial"] == pytest.approx(2.0), row


def test_one_four_thread_process_is_one_process_and_not_serial():
    row = _profile([_record(0.0, 100.0, "/usr/bin/ld.lld --threads=4 -o libLLVM.so", 1)], _flat(4.0))
    assert row["observed_process_concurrency"] == pytest.approx(1.0), row
    assert row["serial_wall_s"] == pytest.approx(0.0) and row["serial_share"] == pytest.approx(0.0), row


def _autoreconf_records():
    rows = [_record(0.0, 100.0, "sh -c -e build", 1), _record(0.0, 100.0, "make -j4", 2)]
    for i in range(10):  # 0-40 s: one autoreconf after another - no classified work binary at all
        rows.append(_record(4.0 * i, 4.0 * i + 4.0, AUTORECONF, 10 + i))
    for slot in range(4):  # 40-100 s: four compilers at once
        rows.append(_record(40.0, 100.0, f"cc1 -quiet f{slot}.c", 100 + slot))
    return rows


@pytest.fixture(scope="module")
def autoreconf():
    windows = {ELEMENT: _flat(1.0, 0.0, 40.0)[ELEMENT] + _flat(4.0, 40.0, 100.0)[ELEMENT]}
    return _profile(_autoreconf_records(), windows)


def test_an_autoreconf_stretch_with_no_work_binary_is_serial_and_named(autoreconf):
    assert autoreconf["work_process_count"] == 4, autoreconf
    assert autoreconf["serial_wall_s"] == pytest.approx(40.0) and autoreconf["serial_share"] == pytest.approx(0.4)
    assert autoreconf["serial_owners"][0] == {"signature": AUTORECONF, "wall_s": pytest.approx(40.0)}, autoreconf


def test_a_low_window_on_a_saturated_host_is_contention_not_serial():
    row = _profile([_record(0.0, 100.0, "/usr/bin/ld.lld --threads=4 -o libLLVM.so", 1)], _flat(0.7, idle=0.1))
    assert row["serial_wall_s"] is None and row["cpu_contended_s"] == pytest.approx(100.0), row
    assert row["serial_unknown"] == "the host had under one idle core for 100% of its sampled time", row


def test_an_element_with_no_samples_is_unknown_not_zero():
    row = _profile(_autoreconf_records(), {})
    assert row["serial_wall_s"] is None and row["serial_share"] is None, row
    assert row["serial_unknown"] == "no CPU samples for this element", row
    half = _profile(_autoreconf_records(), _flat(1.0, 0.0, 40.0))
    assert half["serial_unknown"] == "CPU samples cover 40% of its span", half


# --- the sampler: a reaped child counts, and the invocation log alone names the roots -------------------------


def _stat(pid, ppid, comm, utime, cutime):
    fields = ["S", ppid, pid, pid, 0, -1, 0, 0, 0, 0, 0, utime, 0, cutime, 0] + [0] * 8
    return f"{pid} ({comm}) " + " ".join(map(str, fields)) + "\n"


def _sample(tmp_path, ticks, decisions=None, invocations=None, host=()):
    """`ticks`: per tick, `{pid: (ppid, comm, utime, cutime)}` in jiffies; `host`: per tick, (user, idle) jiffies."""
    proc, out = tmp_path / "proc", tmp_path / "samples.jsonl"
    paths = {}
    for name, rows in (("decisions", decisions), ("invocations", invocations)):
        paths[name] = tmp_path / f"{name}.jsonl"
        if rows is not None:
            paths[name].write_text("".join(json.dumps(row) + "\n" for row in rows))
    sampler = ElementCpuSampler(
        str(out), str(paths["decisions"]), TICK, str(proc), invocations_path=str(paths["invocations"])
    )
    sampler._handle = open(out, "w", encoding="utf-8")
    for index, tree in enumerate(ticks):
        shutil.rmtree(proc, ignore_errors=True)
        for pid, (ppid, comm, utime, cutime) in tree.items():
            task = proc / str(pid) / "task" / str(pid)
            task.mkdir(parents=True)
            (proc / str(pid) / "stat").write_text(_stat(pid, ppid, comm, utime, cutime))
            (task / "children").write_text("".join(f"{kid} " for kid, row in tree.items() if row[0] == pid))
        if host:
            user, idle = host[index]
            (proc / "stat").write_text(
                f"cpu  {user} 0 0 {idle} 0 0 0 0 0 0\n" + "".join(f"cpu{i} 0\n" for i in range(4))
            )
        sampler.tick(index * TICK)
    sampler._handle.close()
    return read_element_cpu_samples(str(out))


def _tree(make_utime, make_cutime):
    return {5100: (1, "bwrap", 1, 0), 5101: (5100, "bwrap", 1, 0), 5102: (5101, "make", make_utime, make_cutime)}


def test_children_reaped_between_ticks_count_as_cores(tmp_path):
    # Four compilers, each under a tick, ran and were reaped inside the window: 8 s of CPU in 2 s.
    eight_s = int(8 * _TICKS_PER_S)
    decisions = [{"element": ELEMENT, "pid": 5100}]
    rows = _sample(tmp_path, [_tree(10, 0), _tree(11, eight_s)], decisions, host=[(1000, 1000), (1200, 1400)])
    windows = element_cpu_windows(rows)
    ((t0, t1, cores, idle),) = windows[ELEMENT]
    assert (t0, t1) == (0.0, TICK) and cores == pytest.approx(4.0, abs=0.01), windows
    assert idle == pytest.approx(4 * 400 / 600), windows
    records = [_record(0.0, TICK, "make -j4", 3)] + [_record(0.1, 1.9, f"cc1 f{i}.c", 10 + i) for i in range(4)]
    assert _profile(records, windows)["serial_wall_s"] == pytest.approx(0.0)
    assert cores > SERIAL_CORES_LINE


def test_the_invocation_log_alone_names_the_roots(tmp_path):
    invocations = [{"invocation_id": 5100, "dir_tag": ELEMENT, "started_at": 0.0, "spine_traced": False}]
    rows = _sample(tmp_path, [_tree(10, 0), _tree(210, 0)], invocations=invocations)
    assert {row["root"] for row in rows} == {5100} and {row["element"] for row in rows} == {ELEMENT}, rows
    assert element_cpu_windows(rows, {"5100": "renamed.bst"})["renamed.bst"][0][2] == pytest.approx(1.0, abs=0.01)


# --- correlate and the page --------------------------------------------------------------------------------


def _joined(profile):
    return ElementJoin(
        element=ELEMENT,
        on_critical_path=True,
        critical_path_share=0.18,
        potential_saving_us=1_837_400_000,
        saving_share=0.13,
        cores_busy=2.57,
        serial_stretch=_plane2_view({"per_element_parallelism": [profile]})[ELEMENT].get("serial_stretch"),
    )


def test_correlate_refuses_compute_bound_and_names_the_owner(autoreconf):
    advice = {step["id"]: step["text"] for step in _recommend(_joined(autoreconf))}
    assert "already-compute-bound" not in advice, advice
    assert "autoreconf2.69" in advice["serial-stretch"] and "40.0 s of its 1.7 min sampled" in advice["serial-stretch"]
    assert autoreconf["serial_share"] > _SERIAL_SHARE_LINE


@pytest.mark.parametrize("fields", ["unsampled", "predates"])
def test_correlate_says_unknown_rather_than_compute_bound(fields):
    profile = _profile(_autoreconf_records(), {})
    if fields == "predates":
        profile = {key: value for key, value in profile.items() if "serial" not in key and "cpu_" not in key}
    advice = {step["id"]: step["text"] for step in _recommend(_joined(profile))}
    assert set(advice) & {"already-compute-bound", "serial-stretch"} == set(), advice
    text = advice["serial-share-unknown"]
    assert "serial share is unknown" in text and "nothing to gain" not in text, text


_PROBE = r"""
const { readFileSync } = await import("node:fs");
const views = await import("%(views)s");
const payload = JSON.parse(readFileSync(%(payload)s, "utf8"));
const record = views.elementFacts(payload).get(%(uid)s);
console.log(JSON.stringify({ advice: record.advice.map((a) => a.text) }));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_element_card_shows_the_seconds_and_the_owner(autoreconf, tmp_path):
    joined = _joined(autoreconf)
    row = {"element": ELEMENT, "serial_stretch": joined.serial_stretch, "recommendations": _recommend(joined)}
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
