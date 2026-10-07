"""UX-1283: under `auto` with no plan, the FIFO opens at bst's own `off`
width for one element (`project_max_jobs - 1`), not a cores-sized seed,
so every token past it passes the memory gate - the pure resolver, a real
FIFO with two giants live, `main`'s own seam, and a typed seed kept.
"""

import json
import os

from bga import cli
from tools import bst_native_build_tracer as tracer
from tools.jobserver.pool import opening_seed

GB = 1 << 30
PAGE = os.sysconf("SC_PAGE_SIZE")
GIANTS = {"giant-a.bst": 100, "giant-b.bst": 200}


def test_auto_with_no_plan_opens_at_max_jobs_less_one():
    assert opening_seed(15, 8, "auto", False) == 7
    assert opening_seed(8, 8, "auto", False) == 7
    assert opening_seed(3, 8, "auto", False) == 3


def test_everything_else_keeps_its_seed():
    assert opening_seed(15, None, "auto", False) == 15
    assert opening_seed(15, 8, "n", False) == 15
    assert opening_seed(15, 8, "auto", True) == 15
    assert opening_seed(15, 8, "auto", False, typed=True) == 15
    assert opening_seed(None, 8, "auto", False) is None


def _stat(root, pid, ppid, rss_bytes, comm="cc1"):
    os.makedirs(root / str(pid), exist_ok=True)
    (root / str(pid) / "stat").write_text(f"{pid} ({comm}) S {ppid} " + "0 " * 19 + f"{rss_bytes // PAGE} 0 0\n")


def _end(element, maxrss_bytes):
    kb = maxrss_bytes // 1024
    return f"END pid=7 ppid=1 ts=1.0 element={element} utime=0.1 stime=0.0 maxrss_kb={kb} cmd=cc1 -O2 x.c\n"


def _two_giants_at_the_opening_seed(tmp_path, available):
    """A 16-ceiling FIFO opened at `opening_seed(15, 8, ...)`, drained, two
    giant sandboxes live at 0.5 GB each, both with a 2 GB finished peak."""
    seed = opening_seed(15, 8, "auto", False)
    proc = tmp_path / "proc"
    _stat(proc, 1, 0, 8 * PAGE, "init")
    rows = []
    for element, pid in GIANTS.items():
        _stat(proc, pid, 1, 2 * PAGE, "bwrap")
        _stat(proc, pid + 1, pid, GB // 2)
        rows.append(json.dumps({"element": element, "pid": pid, "decision": "joined"}) + "\n")
    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text("".join(rows))
    trace_log = tmp_path / "trace.log"
    trace_log.write_text("".join(_end(element, 2 * GB) for element in GIANTS))
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(f"MemTotal: 67108864 kB\nMemAvailable: {available // 1024} kB\n")
    scratch = tmp_path / "fifo"
    scratch.mkdir()
    _path, fd, _tokens = tracer.open_jobserver(16, str(scratch), seed=seed)
    os.read(fd, seed)
    paths = {"seed": seed, "trace_log": str(trace_log), "decisions": str(decisions)}
    paths.update({"meminfo": str(meminfo), "proc_root": str(proc), "memory": str(tmp_path / "no-psi")})
    paths["self_cgroup"] = str(tmp_path / "no-cgroup")  # UX-1282: the runner's own cgroup cap must not bind
    ledger = str(tmp_path / "ledger.jsonl")
    controller = tracer.PoolController(fd, 16, capacity=16, ledger_path=ledger, psi_paths=paths)
    controller.tick(busy_cores=2.0, psi_some10=0.0)
    return controller, controller.tick(busy_cores=2.0, psi_some10=0.0)


def test_two_giants_that_fit_widen_past_the_seed(tmp_path):
    # 2 GB x (7 pool + 2 running + 1 + 1 reserve) = 22 GB <= 64 GB avail + 1 GB live.
    controller, row = _two_giants_at_the_opening_seed(tmp_path, 64 * GB)
    assert row["action"] == "add", row
    assert controller.pool == 8


def test_two_giants_that_do_not_fit_get_no_token_past_the_seed(tmp_path):
    # 22 GB > 8 GB avail + 1 GB live.
    controller, row = _two_giants_at_the_opening_seed(tmp_path, 8 * GB)
    assert row["action"] == "hold" and row["reason"].startswith("rss "), row
    assert controller.pool == 7


def _run_main(tmp_path, monkeypatch, seed_typed):
    seen = {}

    def fake_metadata(project_dir, cmd, jobserver):
        return 8, None, None, {}, {}, {}

    def fake_run_traced_build(project_dir, cmd, raw_log_path, wrapped_log_path=None, **kwargs):
        seen["seed"] = kwargs["jobserver_seed"]
        return 0

    monkeypatch.setenv("BGA_JOBSERVER_MODE", "auto")
    if seed_typed:
        monkeypatch.setenv(cli.JOBSERVER_SEED_TYPED_ENV, "1")
    else:
        monkeypatch.delenv(cli.JOBSERVER_SEED_TYPED_ENV, raising=False)
    monkeypatch.setattr(tracer, "read_jobserver_metadata_for_build", fake_metadata)
    monkeypatch.setattr(tracer, "run_traced_build", fake_run_traced_build)
    raw_log = tmp_path / "raw.log"
    raw_log.write_bytes(b"")
    output = tmp_path / "report.json"
    argv = ["run", "--raw-log", str(raw_log), "--jobserver", "16", "--jobserver-seed", "15"]
    assert tracer.main([*argv, str(tmp_path), str(output), "--", "bst", "build", "app.bst"]) == 0
    return seen["seed"], tracer._jobserver_block(json.loads(output.read_text()))


def test_main_resolves_the_seed_after_reading_max_jobs(tmp_path, monkeypatch):
    seed, block = _run_main(tmp_path, monkeypatch, seed_typed=False)
    assert seed == 7
    assert (block["mode"], block["seed"], block["seed_bound"]) == ("auto", 7, "max_jobs")


def test_a_typed_seed_is_honoured_under_auto(tmp_path, monkeypatch):
    seed, block = _run_main(tmp_path, monkeypatch, seed_typed=True)
    assert seed == 15
    assert (block["seed"], block["seed_bound"]) == (15, "typed")


def test_the_cli_marks_a_typed_seed_and_only_a_typed_one(monkeypatch):
    monkeypatch.delenv("BGA_JOBSERVER_MODE", raising=False)
    monkeypatch.delenv(cli.JOBSERVER_SEED_TYPED_ENV, raising=False)
    tail = ["--", "bst", "build", "app.bst"]
    cli._translate_capture_jobserver(["capture", "run", "--jobserver", "auto", "--jobserver-seed", "12", *tail])
    assert os.environ.get(cli.JOBSERVER_SEED_TYPED_ENV) == "1"
    cli._translate_capture_jobserver(["capture", "run", "--jobserver=auto", "--jobserver-seed=12", *tail])
    assert os.environ.get(cli.JOBSERVER_SEED_TYPED_ENV) == "1"
    cli._translate_capture_jobserver(["capture", "run", "--jobserver", "auto", *tail])
    assert cli.JOBSERVER_SEED_TYPED_ENV not in os.environ
