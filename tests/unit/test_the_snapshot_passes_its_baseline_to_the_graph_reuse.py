"""UX-1083: `bga snapshot` wires the baseline through, no CLI flag - the
same `BGA_JOBSERVER_MODE` shape (UX-856). `bga_snapshot.take_snapshot`
sets `BGA_BASELINE_RUN_DIR` to the previous healthy snapshot's own
`run/`; the tracer's `run` reads it and hands it to `extract_run`. Two
snapshots sharing a fingerprint issue one `bst show --deps all` between
them, end to end through the real snapshot path - `run_traced_build` is
faked (no bwrap/cc needed, since the fake `bst` below never runs a
sandboxed command), but `take_snapshot`, `tracer.main` and `extract_run`
are all real.
"""

import os
import stat

from tools import bga_snapshot
from tools import bst_native_build_tracer as tracer

_FAKE_BST = '''#!/usr/bin/env python3
import os, sys
argv = sys.argv[1:]
with open(os.environ["FAKE_BST_ARGV_FILE"], "a", encoding="utf-8") as f:
    f.write(" ".join(argv) + "\\n")
if "show" in argv:
    FS, RS = "\\x1f", "\\x1e"
    for t in argv:
        if t.endswith(".bst"):
            sys.stdout.write(FS.join([t, "a" * 64, "import", "[]", "[]", "", ""]) + RS)
elif "--version" in argv:
    print("BuildStream 2.8.1")
'''

_WRAPPED_LOG = (
    "[wrapper][2026-01-01 00:00:00,000] INFO: Executing command: bst build app.bst\n"
    "[wrapper][2026-01-01 00:00:00,001] INFO: Targets:       app.bst\n"
    "[wrapper][2026-01-01 00:00:00,002] INFO: Pipeline\n"
    "[wrapper][2026-01-01 00:00:00,002] INFO:    buildable " + "a" * 64 + " app.bst \n"
    "[wrapper][2026-01-01 00:00:00,003] INFO: " + "=" * 79 + "\n"
)


def _fake_run_traced_build(project_dir, cmd, raw_log_path, wrapped_log_path=None, **kwargs):
    open(raw_log_path, "wb").close()
    if wrapped_log_path:
        with open(wrapped_log_path, "w", encoding="utf-8") as f:
            f.write(_WRAPPED_LOG)
    return 0


def _prepare(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "project.conf").write_text("name: p\nmin-version: 2.0\n")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_bst = bin_dir / "bst"
    fake_bst.write_text(_FAKE_BST)
    fake_bst.chmod(fake_bst.stat().st_mode | stat.S_IEXEC)
    argv_file = tmp_path / "argv.txt"
    monkeypatch.setenv("FAKE_BST_ARGV_FILE", str(argv_file))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(tracer, "run_traced_build", _fake_run_traced_build)
    return project, argv_file


def test_a_baseline_snapshot_pair_issues_one_bst_show_through_the_snapshot_path(tmp_path, monkeypatch):
    project, argv_file = _prepare(tmp_path, monkeypatch)
    config = {"trace_opens": False, "trace_spine": "off"}

    snapshot1, rc1 = bga_snapshot.take_snapshot(str(project), ["bst", "build", "app.bst"], config)
    assert rc1 == 0
    assert os.environ.get("BGA_BASELINE_RUN_DIR") is None, (
        "the first snapshot has no previous healthy run to reuse from"
    )

    snapshot2, rc2 = bga_snapshot.take_snapshot(str(project), ["bst", "build", "app.bst"], config)
    assert rc2 == 0
    assert os.environ.get("BGA_BASELINE_RUN_DIR") == os.path.join(snapshot1, bga_snapshot.RUN_SUBDIR)

    show_calls = [line for line in argv_file.read_text().splitlines() if "show" in line]
    assert len(show_calls) == 1, show_calls

    import json

    with open(os.path.join(snapshot2, bga_snapshot.RUN_SUBDIR, "graph.json"), encoding="utf-8") as f:
        graph2 = json.load(f)
    assert graph2["cache_fingerprint"]["cache_key_set"] is not None
