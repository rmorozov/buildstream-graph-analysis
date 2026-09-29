"""UX-1107: two exports of one run name one anchor and decode to one file.

`choose_anchor` broke a tie on `longest` by the hash order of a set. The
snapshot skews each element's Plane 1 build start so the offset follows
the anchor; rendered under `PYTHONHASHSEED` 1-4 in subprocesses.
"""

import gzip
import json
import pathlib
import shutil
import subprocess
import sys
import textwrap

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"
ELEMENTS = ["app.bst", "base.bst", "lib.bst", "tools.bst"]

_CHILD = textwrap.dedent("""
    import hashlib, gzip, json, sys
    sys.path.insert(0, %(repo)r)
    from tools.bga_timeline import render
    result = render(%(snapshot)r, %(output)r, quiet=True)
    print(json.dumps({"anchor": result["anchor"],
                      "sha": hashlib.sha256(gzip.open(%(output)r, "rb").read()).hexdigest()}))
""")


def _snapshot(tmp_path):
    snapshot = tmp_path / "20260821T120000Z"
    snapshot.mkdir()
    log = ["[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst\n"]
    plane2 = []
    for index, element in enumerate(ELEMENTS):
        begin = 1.0 + 1.3 * index
        for verb, at in (("START", begin), ("SUCCESS", begin + 1.0)):
            millis = round((at % 1) * 1000)
            stamp = f"2026-08-21 12:00:{int(at):02d},{millis:03d}"
            clock = f"00:00:{int(at):02d}"
            log.append(f"[wrapper][{stamp}] INFO: [{clock}][aaaaaaaa][   build:{element}] {verb} Building\n")
        for proc in range(6):
            pid = 100 + index * 10 + proc
            start = 1000.0 + proc * 0.1
            plane2.append(f"START pid={pid} ppid=1 ts={start:.6f} element={element} cmd=cc\n")
            plane2.append(f"END pid={pid} ppid=1 ts={start + 0.5:.6f} element={element} cmd=cc\n")
    log.append("[wrapper][2026-08-21 12:00:09,000] INFO: Return code: 0\n")
    (snapshot / "build.log").write_text("".join(log), encoding="utf-8")
    shutil.copytree(GOLDEN, snapshot / "run")
    (snapshot / "run" / "expected_output.json").unlink(missing_ok=True)
    with gzip.open(snapshot / "plane2.log.gz", "wt", encoding="utf-8") as handle:
        handle.write("".join(plane2))
    return snapshot


def test_the_anchor_and_the_export_do_not_depend_on_the_seed(tmp_path):
    snapshot = _snapshot(tmp_path)
    runs = {}
    for seed in (1, 2, 3, 4):
        out = tmp_path / f"seed{seed}.perfetto-trace.gz"
        done = subprocess.run(
            [sys.executable, "-c", _CHILD % {"repo": str(REPO), "snapshot": str(snapshot), "output": str(out)}],
            capture_output=True,
            text=True,
            cwd=REPO,
            env={"PYTHONHASHSEED": str(seed), "PATH": "/usr/bin:/bin"},
            timeout=300,
        )
        assert done.returncode == 0, done.stderr[-3000:]
        runs[seed] = json.loads(done.stdout.strip().splitlines()[-1])
    assert {run["anchor"] for run in runs.values()} == {"app.bst"}, runs
    assert len({run["sha"] for run in runs.values()}) == 1, runs
