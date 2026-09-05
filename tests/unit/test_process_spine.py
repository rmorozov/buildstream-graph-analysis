"""UX-106: a process spine the dynamic linker cannot hide from.

`hook.c` sees a process because the dynamic linker loads it into that
process; a fully static executable never invokes the linker, so the hook
is never loaded and - as its own header says - cannot detect its own
absence. `UX-105` measured how large that hole gets: every command
`examples/01` runs is static busybox, and its Plane 2 capture has always
been empty.

These cover the spine's contract. The two properties that matter most
are not about tracing at all: the wrapped build's exit status must be
what it would have been untraced, in every failure mode, and a tracer
that dies must leave the build running.
"""
import contextlib
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest

from tools.bst_native_build_tracer import compile_spine, parse_trace_log
from tools.native_trace.bwrap_shim import build_shim_argv

SPINE_SOURCE = Path(__file__).resolve().parents[2] / "tools" / "native_trace" / "spine.c"

CC_AVAILABLE = shutil.which("cc") is not None or shutil.which("gcc") is not None


@pytest.fixture(scope="module")
def spine(tmp_path_factory):
    """The real tracer, compiled the way a capture compiles it."""
    if not CC_AVAILABLE:
        pytest.skip("no C compiler on PATH")
    return compile_spine(str(tmp_path_factory.mktemp("spine")))


def _run(spine_bin, script, log=None, env=None):
    environment = dict(os.environ)
    if log:
        environment["BST_TRACE_LOG"] = str(log)
    environment.update(env or {})
    return subprocess.run(
        [spine_bin, "--", "/bin/sh", "-c", script],
        env=environment, capture_output=True, text=True,
    )


# --- injection ----------------------------------------------------------

def test_the_spine_wraps_the_sandboxed_command_not_the_bwrap_options():
    """It has to run *inside* the sandbox, after bwrap has set the
    namespaces up - that is what makes every process BuildStream starts
    its own descendant, and so traceable with no capability under Yama
    `ptrace_scope=1`."""
    argv = build_shim_argv(
        "/usr/bin/bwrap", ["--dir", "/buildstream/x/core.bst", "--", "sh", "-c", "make"],
        "/bind", "/dst", "/dst/hook.so", "/dst/trace.log", spine="/dst/spine",
    )
    assert argv[-5:] == ["/dst/spine", "--", "sh", "-c", "make"]
    # And the injected options still precede it, unchanged.
    assert "--setenv" in argv and "/dst/hook.so" in argv


def test_without_a_spine_the_argv_is_byte_for_byte_what_it_was():
    """Opt-in until `UX-108` measures the overhead, and opt-in has to
    mean the untraced path is untouched."""
    args = ["--dir", "/buildstream/x/core.bst", "--", "sh", "-c", "make"]
    assert build_shim_argv("/usr/bin/bwrap", args, "/b", "/d", "/d/h.so", "/d/t.log") == \
        build_shim_argv("/usr/bin/bwrap", args, "/b", "/d", "/d/h.so", "/d/t.log",
                        spine=None)


# --- the record format --------------------------------------------------

def test_spine_records_round_trip_through_the_existing_parser():
    """`src=` and `exit=` are new fields, and the parser's key loop
    *stops* at the first key it does not know - so an unhandled field
    would not be ignored, it would swallow `cmd=` and leave every spine
    record with an empty command line."""
    text = (
        "START pid=7 ppid=3 ts=1.5 element=work-a.bst inv=42 src=spine cmd=busybox true\n"
        "END pid=7 ppid=3 ts=1.9 element=work-a.bst inv=42 utime=0.010000 "
        "stime=0.020000 maxrss_kb=1412 exit=0 src=spine cmd=busybox true\n"
    )
    start, end = parse_trace_log(text)
    assert start["src"] == "spine" and start["cmd"] == "busybox true"
    assert end["cmd"] == "busybox true"
    assert end["cpu_us"] == 30_000
    assert end["max_rss_kb"] == 1412
    assert end["exit_status"] == "0"


def test_a_hook_record_still_says_it_came_from_the_hook():
    """Every capture taken before the spine existed carries no `src=`,
    and defaulting it to `hook` gives those records one honest answer
    rather than None."""
    text = "START pid=7 ppid=3 ts=1.5 element=core.bst inv=9 cmd=cc1plus a.cpp\n"
    assert parse_trace_log(text)[0]["src"] == "hook"


def test_a_signal_death_is_distinguishable_from_that_exit_code():
    """`exit=signal:9` and `exit=9` are different facts. The hook has no
    equivalent at all: its destructor runs before the process has a
    status, and does not run when one is killed."""
    text = ("END pid=7 ppid=3 ts=1.9 element=e.bst inv=1 exit=signal:9 src=spine "
            "cmd=/bin/sleep 5\n")
    assert parse_trace_log(text)[0]["exit_status"] == "signal:9"


# --- the tracer itself --------------------------------------------------

@pytest.mark.parametrize("script,expected", [
    ("exit 0", 0),
    ("exit 7", 7),
    # Negative: Python reports a signal death as -N, and that is exactly
    # why this case is checked through Python rather than a shell.
    ("kill -TERM $$", -15),
])
def test_the_exit_status_is_the_commands_own(spine, script, expected):
    """`hook.c`'s standing rule - never break the wrapped build - is
    harder to keep here, because this process sits between BuildStream
    and the command it asked for.

    The signal case caught a real difference. Returning `128 + N` reads
    identically to a shell, but the *wait status* a parent inspects is
    not the same: `WIFEXITED` against `WIFSIGNALED`, and BuildStream is
    that parent. The spine now dies the way the command died instead of
    exiting with a number that looks like it.
    """
    assert _run(spine, script).returncode == expected
    assert subprocess.run(["/bin/sh", "-c", script],
                          capture_output=True).returncode == expected


def test_a_static_binary_is_traced(spine, tmp_path):
    """The whole point. `LD_PRELOAD` produces nothing for a static
    executable; this produces a START and an END with argv, CPU time and
    peak RSS."""
    busybox = shutil.which("busybox")
    if busybox is None:
        pytest.skip("no busybox on PATH to exercise a static binary with")
    log = tmp_path / "trace.log"
    assert _run(spine, f"{busybox} true", log=log).returncode == 0
    records = [r for r in parse_trace_log(log.read_text()) if "busybox true" in r["cmd"]]
    assert {r["event"] for r in records} == {"START", "END"}
    end = next(r for r in records if r["event"] == "END")
    assert end["src"] == "spine"
    assert end["exit_status"] == "0"
    assert end["max_rss_kb"] > 0


def test_a_killed_process_is_recorded_with_how_it_died(spine, tmp_path):
    """The acceptance asks for "START without a fabricated END". What
    the spine produces is better and not a fabrication: the kernel's own
    exit-stop fires for a SIGKILLed process too, so the END carries real
    CPU and RSS read while the task still existed, plus `exit=signal:9`.
    Nothing is invented - a measurement the hook simply cannot take."""
    log = tmp_path / "trace.log"
    _run(spine, "/bin/sleep 5 & p=$!; /bin/sleep 0.2; kill -9 $p; wait", log=log)
    ends = [
        r for r in parse_trace_log(log.read_text())
        if r["event"] == "END" and r["cmd"] == "/bin/sleep 5"
    ]
    assert [r["exit_status"] for r in ends] == ["signal:9"]


def test_the_timestamps_share_the_hooks_clock(spine, tmp_path):
    """Both streams read `CLOCK_MONOTONIC`, so they share one timeline by
    construction rather than by correlation - which is what lets `UX-107`
    join them at all."""
    import time

    log = tmp_path / "trace.log"
    before = time.clock_gettime(time.CLOCK_MONOTONIC)
    _run(spine, "/bin/true", log=log)
    after = time.clock_gettime(time.CLOCK_MONOTONIC)
    stamps = [r["ts"] for r in parse_trace_log(log.read_text())]
    assert stamps and all(before <= ts <= after for ts in stamps)


def test_no_trace_log_means_no_records_and_no_failure(spine):
    """`BST_TRACE_LOG` unset is how a caller turns tracing off, and it
    must leave the command's behaviour untouched rather than erroring."""
    environment = {k: v for k, v in os.environ.items() if k != "BST_TRACE_LOG"}
    result = subprocess.run(
        [spine, "--", "/bin/sh", "-c", "echo hi"],
        env=environment, capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "hi"


def test_a_lone_tracee_survives_the_tracers_death(spine, tmp_path):
    """`PTRACE_O_EXITKILL` is deliberately NOT set: it would kill every
    tracee when the tracer died, turning a tracer bug into a failed
    build, which is exactly the outcome forbidden. Without it the kernel
    detaches on tracer death and the command runs on, untraced.

    Measured, and the measurement is narrower than the acceptance's
    wording - see `UX-106`'s "What a SIGKILLed tracer does" for the
    process-tree case, which does not survive on this kernel and which a
    plain fork/exec wrapper does. A lone tracee is the case where
    detachment is provably doing its job.
    """
    marker = tmp_path / "finished"
    script = f"/bin/sleep 1.5; echo done > {marker}"
    process = subprocess.Popen(
        [spine, "--", "/bin/sleep", "1.5"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    _wait_until(lambda: _children_of(process.pid), timeout=3.0)
    tracee = _children_of(process.pid)
    assert tracee, "the tracer never started the command"
    process.kill()
    process.wait(timeout=5)
    # Still running after its tracer is gone, rather than killed with it.
    assert _wait_until(lambda: os.path.exists(f"/proc/{tracee[0]}"), timeout=1.0)
    del script


def _wait_until(predicate, timeout):
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


def _children_of(pid):
    """Polled rather than slept for, so the test does not race on a
    loaded machine."""
    try:
        return subprocess.run(
            ["pgrep", "-P", str(pid)], capture_output=True, text=True,
        ).stdout.split()
    except OSError:
        return []


BST_AVAILABLE = shutil.which("bst") is not None
BWRAP_AVAILABLE = shutil.which("bwrap") is not None
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.bst
@pytest.mark.skipif(
    not (BST_AVAILABLE and BWRAP_AVAILABLE and CC_AVAILABLE),
    reason="bst/bwrap/cc not all found on PATH - see docs/spec/ingestion-pipeline.md",
)
def test_a_real_static_build_is_invisible_to_the_hook_and_visible_to_the_spine(tmp_path):
    """UX-106's acceptance, on the project `UX-105`'s census identified.

    `examples/01-resource-contention` runs every build command through
    static busybox. Its Plane 2 capture has been empty for as long as
    Plane 2 has existed, and nothing in the report said why until the
    census; nothing could *fix* it until the spine.

    Both halves are run here rather than only the interesting one,
    because "the spine found 24 processes" means nothing without "and
    the hook alone found 0 on the same build".
    """
    from tests.unit._bst_env import isolated_bst_env
    from tools.bst_native_build_tracer import run_traced_build

    project = os.path.join(REPO_ROOT, "examples", "01-resource-contention")
    if not os.path.isfile(os.path.join(project, "files", "runtime", "bin", "sh")):
        pytest.skip("examples/01 is not staged - run examples/stage_runtimes.sh")

    def _capture(name, trace_spine):
        home = tmp_path / f"home-{name}"
        home.mkdir()
        raw = tmp_path / f"{name}.log"
        environment = isolated_bst_env(home)
        previous = dict(os.environ)
        os.environ.update(environment)
        try:
            code = run_traced_build(
                project, ["bst", "--no-colors", "build", "all.bst"], str(raw),
                trace_spine=trace_spine,
            )
        finally:
            os.environ.clear()
            os.environ.update(previous)
        return code, parse_trace_log(raw.read_text() if raw.exists() else "")

    hook_code, hook_records = _capture("hook", trace_spine=False)
    spine_code, spine_records = _capture("spine", trace_spine=True)

    # The build itself is unaffected either way - the whole point.
    assert hook_code == 0 and spine_code == 0

    assert hook_records == [], (
        "the hook is expected to see nothing here: every command is static busybox"
    )
    assert spine_records, "the spine saw nothing on a build that runs real commands"
    assert {r["src"] for r in spine_records} == {"spine"}
    # Real element attribution, inherited from the same shim env the hook
    # reads - the spine is not a second, parallel identity scheme.
    assert any(r["element"].endswith(".bst") for r in spine_records)
    # And real measurements, not just names.
    ends = [r for r in spine_records if r["event"] == "END"]
    assert ends and all("max_rss_kb" in r for r in ends)


# --- the two failure paths round 12's code review found -----------------

def test_a_degrade_does_not_strand_the_tracees_it_was_meant_to_free(spine, tmp_path):
    """UX-117: the error path inverted its own contract.

    `degrade()` exists so that a tracer-side failure never breaks the
    wrapped build. It detached the one offending pid and then *skipped*
    every other tracee that reached a stop - and a tracee popped from
    `waitpid` is stopped, so skipping it leaves it stopped forever. The
    loop then waited on processes that could never move again and exited
    only on `ECHILD`, which never came.

    Measured before the fix, with the degrade forced at events 2, 4 and
    8: **hung every time**, killed at a 25s timeout. After: exit 4 in
    0.7s, every time.
    """
    marker = tmp_path / "done"
    script = (f"for i in 1 2 3 4 5; do (sleep 0.4; true) & done; wait; "
              f"sleep 0.3; echo done > {marker}; exit 4")
    log = tmp_path / "trace.log"

    result = subprocess.run(
        [spine, "--", "/bin/sh", "-c", script],
        env={**os.environ, "BST_TRACE_LOG": str(log),
             "BST_TRACE_ELEMENT": "e.bst", "BST_TRACE_INVOCATION": "inv",
             # The seam exists because this failure cannot be provoked
             # from outside: only the tracer may detach its own tracees.
             "BST_TRACE_SPINE_DEGRADE_AFTER": "4"},
        capture_output=True, text=True, timeout=30,
    )

    assert result.returncode == 4, "the build's own exit status must survive a degrade"
    assert marker.exists(), "the wrapped command did not run to completion"
    assert "DEGRADED" in log.read_text(), "the degradation went unrecorded"


def test_the_seams_are_off_unless_asked_for(spine, tmp_path):
    """They ship in the binary, so they have to be inert. Nothing in the
    capture path sets them: `bwrap_shim.py` passes a fixed list of
    BST_TRACE_* variables through and none of these is among it.

    UX-143: this asserted only `DEGRADE_AFTER` while UX-128's own file
    said it covered both seams - so the seam that can hang a build was
    the one going unchecked. All three are named now, including
    UX-140's."""
    from tools.native_trace.bwrap_shim import build_shim_argv

    log = tmp_path / "trace.log"
    result = _run(spine, "exit 0", log=log)

    assert result.returncode == 0
    assert "DEGRADED" not in (log.read_text() if log.exists() else "")
    argv = build_shim_argv(
        "/usr/bin/bwrap", ["--", "sh", "-c", "true"],
        "/bind", "/dst", "/dst/hook.so", "/dst/trace.log", spine="/dst/spine",
    )
    rendered = " ".join(str(arg) for arg in argv)
    for seam in ("DEGRADE_AFTER", "FAIL_CONT_AT", "FAIL_SEIZE"):
        assert seam not in rendered, f"the {seam} seam reaches the capture path"


def test_a_killed_tracer_leaves_the_build_running(spine, tmp_path):
    """UX-106 recorded this clause as *measured failing* and attributed
    it to ptrace at large: killing the tracer left `sh` and its `sleep`
    as zombies where a plain fork/exec wrapper let both finish.

    UX-118 found the real mechanism. Every auto-attached child's first
    stop is the kernel's attach-SIGSTOP, and the spine restarted it *with*
    that signal - turning an attach-stop into a real group stop. When the
    tracer then died, `__ptrace_unlink` re-instated the pending group
    stop and the tree stayed stopped. It was our bug, not ptrace's.

    Measured across three runs each, before and after: the traced tree
    never completed on the old binary and completed every time on the
    new one.
    """
    marker = tmp_path / "done"
    proc = subprocess.Popen(
        [spine, "--", "/bin/sh", "-c", f"sleep 4; echo done > {marker}"],
        env={**os.environ, "BST_TRACE_LOG": str(tmp_path / "t.log"),
             "BST_TRACE_ELEMENT": "e.bst", "BST_TRACE_INVOCATION": "inv"},
        start_new_session=True,
    )
    time.sleep(1.0)
    os.kill(proc.pid, signal.SIGKILL)   # the tracer itself, directly
    proc.wait()

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and not marker.exists():
        time.sleep(0.2)
    assert marker.exists(), "the traced tree did not survive its tracer"


def _stop_probe(binary, tmp_path, delay=1.0):
    """Run `binary -- sh -c 'kill -STOP $$'` and look at the shell while
    it should be stopped.

    UX-130's central point, made executable. The test this replaces ran
    `(sleep 1; kill -CONT $$) & kill -STOP $$` and asserted exit 0 plus a
    marker file - **both of which hold whether the stop was honored or
    swallowed**, because the `sleep 1` supplies the elapsed time either
    way. It passed against a tracer that ate the signal.

    The CONT here comes from *outside* the traced tree, after the probe
    has already looked at `/proc/<pid>/stat`. A tracer that swallows the
    SIGSTOP lets the shell run to completion immediately, so the process
    is **gone** before the CONT is sent - which is what
    `exited_before_cont` records, and what no exit code can show.
    """
    pidfile = tmp_path / "shell.pid"
    script = f"echo $$ > {pidfile}; kill -STOP $$; exit 3"
    started = time.time()
    process = subprocess.Popen(
        [binary, "--", "/bin/sh", "-c", script],
        env={**os.environ, "BST_TRACE_LOG": str(tmp_path / "t.log"),
             "BST_TRACE_ELEMENT": "e.bst", "BST_TRACE_INVOCATION": "inv"},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    pid = None
    while time.time() - started < 10 and pid is None:
        try:
            pid = int(pidfile.read_text().strip())
        except (OSError, ValueError):
            time.sleep(0.02)
    assert pid is not None, "the traced shell never reported its pid"

    time.sleep(delay)
    try:
        state = open(f"/proc/{pid}/stat").read().rsplit(") ", 1)[-1].split()[0]
    except OSError:
        state = "gone"
    exited_before_cont = process.poll() is not None
    with contextlib.suppress(ProcessLookupError):
        os.kill(pid, signal.SIGCONT)
    returncode = process.wait(timeout=30)
    return {"state": state, "exited_before_cont": exited_before_cont,
            "returncode": returncode, "elapsed": time.time() - started}


def test_a_stop_the_program_raises_itself_really_stops_it(spine, tmp_path):
    """UX-130: the tracee must *stay* stopped, exactly as untraced.

    Classic ptrace cannot tell a group-stop from a signal-delivery stop -
    both are `WSTOPSIG == SIGSTOP` with no event - so the old spine
    restarted the tracee and it never stayed still. `PTRACE_SEIZE` types
    the stop and `PTRACE_LISTEN` holds it.

    The state letter is `t` (tracing stop) rather than the untraced `T`,
    because a listened group-stop *is* a ptrace-stop. What has to match
    untraced is the behaviour - still alive, still stopped, resumable by
    an ordinary SIGCONT, same exit status - and that is what is asserted.
    """
    probe = _stop_probe(spine, tmp_path)

    assert not probe["exited_before_cont"], (
        "the traced shell ran to completion through its own SIGSTOP - the "
        "stop was swallowed, which is what UX-130 was filed for")
    assert probe["state"] in ("T", "t"), (
        f"the traced shell was in state {probe['state']!r}, not stopped")
    assert probe["returncode"] == 3, "the exit status changed"


def test_a_grandchilds_stop_is_honored_too(spine, tmp_path):
    """The direct child and an auto-attached descendant reach the loop by
    different routes - the child through the SEIZE the parent performs,
    a grandchild through `PTRACE_O_TRACEFORK`'s inheritance - so both
    halves need checking. The old code's defect was specifically in the
    first: the child's attach-stop was consumed before the loop and so
    never entered the seen-set, making its *next* genuine SIGSTOP look
    like an attach-stop.
    """
    pidfile = tmp_path / "grandchild.pid"
    script = f"( echo $$ > {pidfile}; kill -STOP $$; exit 0 ) & wait; exit 3"
    started = time.time()
    process = subprocess.Popen(
        [spine, "--", "/bin/sh", "-c", script],
        env={**os.environ, "BST_TRACE_LOG": str(tmp_path / "t.log"),
             "BST_TRACE_ELEMENT": "e.bst", "BST_TRACE_INVOCATION": "inv"},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    pid = None
    while time.time() - started < 10 and pid is None:
        try:
            pid = int(pidfile.read_text().strip())
        except (OSError, ValueError):
            time.sleep(0.02)
    assert pid is not None

    time.sleep(1.0)
    alive = process.poll() is None
    try:
        state = open(f"/proc/{pid}/stat").read().rsplit(") ", 1)[-1].split()[0]
    except OSError:
        state = "gone"
    with contextlib.suppress(ProcessLookupError):
        os.kill(pid, signal.SIGCONT)
    returncode = process.wait(timeout=30)

    assert alive, "the whole tree finished through a stopped grandchild"
    assert state in ("T", "t"), f"the grandchild was in state {state!r}"
    assert returncode == 3


def test_pid_churn_at_scale_loses_no_records(spine, tmp_path):
    """UX-130's last clause, and the reason the table had to go rather
    than be repaired.

    `forget_pid` zeroed its slot instead of tombstoning it, which breaks
    an open-addressed probe chain; the hash was a bijection below pid
    8192, so the breakage began exactly where a real freedesktop-sdk
    capture lives. There is no table any more, so the property to pin is
    the outcome: churn several thousand pids through the tracer and lose
    nothing.
    """
    log = tmp_path / "churn.log"
    result = subprocess.run(
        [spine, "--", "/bin/sh", "-c", "i=0; while [ $i -lt 2000 ]; do "
                                       "/bin/true; i=$((i+1)); done; exit 0"],
        env={**os.environ, "BST_TRACE_LOG": str(log),
             "BST_TRACE_ELEMENT": "e.bst", "BST_TRACE_INVOCATION": "inv"},
        capture_output=True, text=True, timeout=300,
    )

    assert result.returncode == 0
    text = log.read_text()
    assert "DEGRADED" not in text, "the tracer degraded under ordinary pid churn"
    starts = text.count("\nSTART ") + text.startswith("START ")
    ends = text.count("\nEND ") + text.startswith("END ")
    # 2000 `/bin/true` execs plus the shell itself; every one exits, and
    # the spine reads the status at the kernel's exit-stop, so START and
    # END counts agree exactly.
    assert starts >= 2000, f"only {starts} START records for 2000 execs"
    assert ends == starts, f"{starts} STARTs but {ends} ENDs"


def test_the_stop_probe_reproduces_untraced_behaviour(tmp_path):
    """The control, so the assertions above are anchored to what the
    kernel does with no tracer rather than to what the spine happens to
    do. `/bin/env` stands in for "no tracer": it execs its arguments."""
    probe = _stop_probe("/bin/env", tmp_path)

    assert not probe["exited_before_cont"]
    assert probe["state"] == "T"
    assert probe["returncode"] == 3


# --- the shape it actually ships in (UX-119) ----------------------------

@pytest.mark.bst
@pytest.mark.skipif(not BWRAP_AVAILABLE, reason="bwrap not on PATH")
def test_the_spine_is_pid_2_in_the_shape_buildstream_runs(spine, tmp_path):
    """`spine.c`'s header claimed pid 1 and justified its signal handling
    by pid 1's missing default dispositions. BuildStream's real bwrap
    argv carries `--unshare-pid --die-with-parent` and no `--as-pid-1`,
    so bubblewrap's own reaper is pid 1 and everything it launches starts
    at 2."""
    def _pid_of_shell(extra):
        return subprocess.run(
            ["bwrap", "--dev-bind", "/", "/", "--unshare-pid", *extra,
             "/bin/sh", "-c", "echo $$"],
            capture_output=True, text=True, timeout=60).stdout.strip()

    assert _pid_of_shell([]) == "2"
    assert _pid_of_shell(["--as-pid-1"]) == "1"


@pytest.mark.bst
@pytest.mark.skipif(not BWRAP_AVAILABLE, reason="bwrap not on PATH")
@pytest.mark.parametrize("script,label", [
    ("exit 0", "success"),
    ("exit 7", "an ordinary failure"),
    ("kill -TERM $$", "a signal death"),
])
def test_a_traced_status_equals_an_untraced_one_inside_the_sandbox(
        spine, script, label):
    """The contract, checked where it is actually kept: inside a real
    bwrap sandbox, against bare bwrap as the control.

    This is what the spine's own tests could not see while they ran it as
    a plain subprocess - and it is worth checking against the control
    rather than against an expected number, because bwrap renders a
    signal death as 143 all by itself.
    """
    def _run(argv):
        return subprocess.run(
            ["bwrap", "--dev-bind", "/", "/", "--unshare-pid", *argv,
             "/bin/sh", "-c", script],
            capture_output=True, text=True, timeout=60).returncode

    assert _run([spine, "--"]) == _run([]), label


@pytest.mark.bst
@pytest.mark.skipif(not BWRAP_AVAILABLE, reason="bwrap not on PATH")
def test_why_the_shim_does_not_pass_as_pid_1(spine):
    """UX-119 offers passing `--as-pid-1` as the alternative to accepting
    pid-2 reality. It is the wrong half of the choice, and bare bwrap
    says so: with that flag a signal-killed command surfaces **0**, and
    without it 143. Adding it would change what BuildStream observes
    about its own builds even with no tracer attached."""
    from tools.native_trace.bwrap_shim import build_shim_argv

    def _bare(extra):
        return subprocess.run(
            ["bwrap", "--dev-bind", "/", "/", "--unshare-pid", *extra,
             "/bin/sh", "-c", "kill -TERM $$"],
            capture_output=True, text=True, timeout=60).returncode

    assert _bare([]) == 143
    assert _bare(["--as-pid-1"]) == 0, "the reason the flag stays out"

    argv = build_shim_argv(
        "/usr/bin/bwrap", ["--unshare-pid", "--", "sh", "-c", "true"],
        "/bind", "/dst", "/dst/hook.so", "/dst/trace.log", spine="/dst/spine",
    )
    assert "--as-pid-1" not in argv, "the shim must not change the sandbox"


# --- UX-128: every restart site, not one of five ------------------------

def _nothing_is_stopped(pids):
    """The pids from `pids` still in state `T`, read from /proc.

    UX-117's acceptance asked for this assertion and it never landed: the
    degrade test asserted the build's exit status, which a hung tracee
    cannot affect once the tracer has already been killed by a timeout.
    A stranded tracee is visible in `/proc/<pid>/stat`'s third field, and
    nowhere in an exit code.
    """
    stopped = []
    for pid in pids:
        try:
            with open(f"/proc/{pid}/stat") as handle:
                fields = handle.read().rsplit(") ", 1)[-1].split()
        except OSError:
            continue                      # reaped between listing and reading
        if fields and fields[0] == "T":
            stopped.append(pid)
    return stopped


def _descendants_of(root):
    """Every live pid whose ancestry reaches `root`, from /proc."""
    parents = {}
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/stat") as handle:
                fields = handle.read().rsplit(") ", 1)[-1].split()
            parents[int(entry)] = int(fields[1])
        except (OSError, IndexError, ValueError):
            continue
    found = []
    for pid, _parent in parents.items():
        walker, depth = pid, 0
        while walker > 1 and depth < 64:
            walker = parents.get(walker, 0)
            depth += 1
            if walker == root:
                found.append(pid)
                break
    return found


# UX-141: every site `resume()` actually has, and the spine rejects a
# name that is not one of them - so this list drifting again fails
# loudly instead of testing nothing. It named `initial`, which UX-130
# deleted, for a whole round: two parametrized runs injected nothing and
# passed vacuously while `attach` - the restart that runs once per
# auto-attached descendant, more often than every other site combined -
# had no coverage at all.
CONT_SITES = ["exec", "exit", "fork", "signal", "attach"]


@pytest.mark.parametrize("site", CONT_SITES)
def test_a_cont_failure_at_any_site_still_completes_the_build(spine, tmp_path, site):
    """UX-128: UX-117 guarded one restart site of five and then wrote, in
    a comment, that no other path could strand a tracee.

    The exec-stop, exit-stop, fork-stop and initial restarts all
    discarded the `PTRACE_CONT` return value. A failure at any of them
    leaves that tracee stopped forever, `waitpid(-1)` never reaches
    `ECHILD`, and the build hangs - the identical failure mode UX-117
    exists to prevent, one branch over.
    """
    marker = tmp_path / f"done-{site}"
    script = (f"for i in 1 2 3; do (sleep 0.3; true) & done; wait; "
              f"echo done > {marker}; exit 7")
    log = tmp_path / f"trace-{site}.log"

    result = subprocess.run(
        [spine, "--", "/bin/sh", "-c", script],
        env={**os.environ, "BST_TRACE_LOG": str(log),
             "BST_TRACE_ELEMENT": "e.bst", "BST_TRACE_INVOCATION": "inv",
             "BST_TRACE_SPINE_FAIL_CONT_AT": site},
        capture_output=True, text=True, timeout=30,
    )

    assert result.returncode == 7, (
        f"a CONT failure at the {site} site changed the build's exit status")
    assert marker.exists(), f"the wrapped command did not complete ({site})"


@pytest.mark.parametrize("site", CONT_SITES)
def test_a_cont_failure_names_the_site_it_happened_at(spine, tmp_path, site):
    """A degradation record that says only "cont-failed" tells a reader
    the tracer gave up and not which restart broke - and with five sites
    sharing one guard, that is the whole diagnostic value."""
    log = tmp_path / f"trace-{site}.log"
    subprocess.run(
        [spine, "--", "/bin/sh", "-c", "(sleep 0.2; true) & wait; exit 0"],
        env={**os.environ, "BST_TRACE_LOG": str(log),
             "BST_TRACE_ELEMENT": "e.bst", "BST_TRACE_INVOCATION": "inv",
             "BST_TRACE_SPINE_FAIL_CONT_AT": site},
        capture_output=True, text=True, timeout=30,
    )

    assert f"reason=cont-failed-{site}" in log.read_text()


def test_a_degrade_leaves_nothing_in_state_T(spine, tmp_path):
    """UX-117's acceptance clause, finally asserted rather than implied.

    The exit status cannot see a stranded tracee - the build completes
    around it - so the check has to read `/proc/<pid>/stat` while the
    processes are still alive. The script keeps a descendant alive past
    the tracer's exit precisely so there is something to look at.
    """
    log = tmp_path / "trace.log"
    marker = tmp_path / "spawned"
    script = (f"(sleep 2; true) & echo $! > {marker}; "
              f"for i in 1 2 3; do (sleep 0.2; true) & done; wait -n; exit 0")

    process = subprocess.Popen(
        [spine, "--", "/bin/sh", "-c", script],
        env={**os.environ, "BST_TRACE_LOG": str(log),
             "BST_TRACE_ELEMENT": "e.bst", "BST_TRACE_INVOCATION": "inv",
             "BST_TRACE_SPINE_DEGRADE_AFTER": "3"},
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    deadline = time.time() + 10
    survivors = []
    while time.time() < deadline:
        survivors = _descendants_of(process.pid)
        if survivors:
            break
        if process.poll() is not None:
            break
        time.sleep(0.05)
    stopped = _nothing_is_stopped(survivors)
    process.wait(timeout=20)

    assert stopped == [], (
        f"tracee(s) left in state T after a degrade: {stopped} - "
        "a stranded tracee is exactly the hang UX-117 was filed for, and "
        "an exit code cannot see it"
    )


# --- UX-128: the failure paths, inside the sandbox they ship in ---------
#
# UX-117 and UX-119 both wrote acceptance clauses saying "in a real bwrap
# sandbox" and both landed as plain subprocess tests. The distinction is
# not pedantic: `--unshare-pid` puts the traced command at pid 2 under
# bubblewrap's own reaper, which is a different signal and reaping
# environment from a bare `subprocess.run` - and it is the one every real
# capture uses.

def _in_sandbox(argv, timeout=90, env=None):
    return subprocess.run(
        ["bwrap", "--dev-bind", "/", "/", "--unshare-pid", *argv],
        capture_output=True, text=True, timeout=timeout,
        env={**os.environ, **(env or {})},
    )


@pytest.mark.bst
@pytest.mark.skipif(not (BWRAP_AVAILABLE and CC_AVAILABLE),
                    reason="bwrap/cc not both on PATH")
@pytest.mark.parametrize("site", CONT_SITES)
def test_a_cont_failure_inside_the_sandbox_still_completes_the_build(
        spine, tmp_path, site):
    """UX-128, in the shape it ships in.

    Measured with the guard removed (`resume` returning before its error
    check, i.e. the pre-UX-128 discard): every one of the five sites
    hangs until the test's own 30-second timeout. With it: the command's
    exit status, every time.
    """
    log = tmp_path / f"sandbox-{site}.log"
    result = _in_sandbox(
        [spine, "--", "/bin/sh", "-c",
         "for i in 1 2 3; do (sleep 0.3; true) & done; wait; exit 7"],
        env={"BST_TRACE_LOG": str(log), "BST_TRACE_ELEMENT": "e.bst",
             "BST_TRACE_INVOCATION": "inv",
             "BST_TRACE_SPINE_FAIL_CONT_AT": site},
    )

    assert result.returncode == 7, (
        f"a CONT failure at the {site} site inside the sandbox changed the "
        f"build's exit status ({result.stderr[-400:]})")


@pytest.mark.bst
@pytest.mark.skipif(not (BWRAP_AVAILABLE and CC_AVAILABLE),
                    reason="bwrap/cc not both on PATH")
def test_a_degrade_inside_the_sandbox_keeps_the_builds_exit_status(spine, tmp_path):
    """UX-117's own acceptance clause, run where it said it would be."""
    log = tmp_path / "sandbox-degrade.log"
    result = _in_sandbox(
        [spine, "--", "/bin/sh", "-c",
         "for i in 1 2 3 4 5; do (sleep 0.4; true) & done; wait; exit 4"],
        env={"BST_TRACE_LOG": str(log), "BST_TRACE_ELEMENT": "e.bst",
             "BST_TRACE_INVOCATION": "inv",
             "BST_TRACE_SPINE_DEGRADE_AFTER": "4"},
    )

    assert result.returncode == 4
    assert "DEGRADED" in log.read_text()


@pytest.mark.bst
@pytest.mark.skipif(not (BWRAP_AVAILABLE and CC_AVAILABLE),
                    reason="bwrap/cc not both on PATH")
@pytest.mark.parametrize("tracees", [1, 8])
def test_sigterm_at_the_spine_inside_the_sandbox(spine, tmp_path, tracees):
    """UX-119's clause, corrected twice over.

    Its own test killed the *command*, not the spine, and never varied
    the tracee count - so it could not see either thing it claimed to
    check. This aims the signal at the spine's own pid, at one tracee and
    at eight, inside the sandbox.

    The assertion is against bare bwrap rather than a number, because
    bubblewrap renders a signal death itself and the contract is
    "identical to untraced", not "equal to 143".
    """
    script = (f"for i in $(seq {tracees}); do (sleep 5; true) & done; wait")

    def _kill_after_start(argv):
        process = subprocess.Popen(
            ["bwrap", "--dev-bind", "/", "/", "--unshare-pid", *argv,
             "/bin/sh", "-c", script],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env={**os.environ, "BST_TRACE_LOG": str(tmp_path / f"t{tracees}.log"),
                 "BST_TRACE_ELEMENT": "e.bst", "BST_TRACE_INVOCATION": "inv"},
        )
        time.sleep(1.0)
        process.terminate()
        process.wait(timeout=60)
        return process.returncode

    assert _kill_after_start([spine, "--"]) == _kill_after_start([]), (
        f"a SIGTERM at the spine with {tracees} tracee(s) produced a different "
        "status than the same signal with no tracer at all")


# --- UX-133: the tracer must not change when an element finishes --------

def test_a_background_daemon_does_not_hold_the_element_open(spine, tmp_path):
    """UX-133 item 3, and a "never break the wrapped build" defect no
    prior filing covered.

    The loop ran to `ECHILD` - every descendant, not just the command -
    so a build step that leaves a daemon behind kept the *element*
    running until the daemon exited, while untraced bubblewrap's own
    reaper owns it and BuildStream moves on. A tracer that changes when
    an element finishes has changed the build.

    Measured against the pre-fix binary: **30.01s** traced against
    **0.00s** untraced, for a step whose own work is instant.
    """
    log = tmp_path / "daemon.log"
    # The daemon's own stdout/stderr are redirected, deliberately: a
    # backgrounded process inherits the captured pipe, and
    # `subprocess.run` waits for that pipe to close whatever the tracer
    # does. Without this the test measures Python's pipe semantics and
    # reports 30s for the untraced control too - it would "pass" by
    # comparing two hangs.
    script = "sleep 30 >/dev/null 2>&1 & echo started; exit 0"

    def _elapsed(argv):
        started = time.time()
        result = subprocess.run(
            argv + ["/bin/sh", "-c", script],
            env={**os.environ, "BST_TRACE_LOG": str(log),
                 "BST_TRACE_ELEMENT": "e.bst", "BST_TRACE_INVOCATION": "inv"},
            capture_output=True, text=True, timeout=60,
        )
        return time.time() - started, result.returncode

    traced, traced_rc = _elapsed([spine, "--"])
    untraced, untraced_rc = _elapsed([])

    assert traced_rc == untraced_rc == 0
    assert traced < untraced + 5.0, (
        f"the traced step took {traced:.2f}s against {untraced:.2f}s untraced - "
        "the tracer is waiting for a descendant the build does not wait for")


def test_a_released_survivor_is_visible_as_an_open_record(spine, tmp_path):
    """Letting go of a descendant is right, and also a fact about the
    build worth knowing.

    The first attempt had the spine emit a `SURVIVORS count=N` line, and
    the count was wrong: `waitpid(WNOHANG)` reports only tracees stopped
    at that instant, so a still-running daemon - the ordinary case - was
    released uncounted. The record layer already carries this correctly:
    a process the spine STARTed and never saw exit is an `open` record.
    """
    from tools.bst_native_build_tracer import pair_events, parse_trace_log

    log = tmp_path / "survivors.log"
    # The daemon is given time to exec before the command exits. Without
    # that the test is a race and not a property: whether a survivor was
    # recorded at all depends on whether its exec-stop had happened when
    # the tracer stopped watching, which is inherent to stopping. What is
    # guaranteed is that a process the spine *did* see start and never
    # saw finish is reported as open rather than dropped.
    subprocess.run(
        [spine, "--", "/bin/sh", "-c",
         "sleep 30 >/dev/null 2>&1 & sleep 0.3; exit 0"],
        env={**os.environ, "BST_TRACE_LOG": str(log),
             "BST_TRACE_ELEMENT": "e.bst", "BST_TRACE_INVOCATION": "inv"},
        capture_output=True, text=True, timeout=60,
    )

    records = pair_events(parse_trace_log(log.read_text()))
    survivors = [r for r in records if r["open"]]

    assert survivors, "the daemon the tracer let go left no trace at all"
    assert all(r["open_reason"] == "no-observed-exit" for r in survivors)
    assert any("sleep 30" in r["cmd"] for r in survivors), survivors


def test_a_build_that_reaps_its_own_children_leaves_no_open_records(spine, tmp_path):
    """The signal has to be evidence, not decoration."""
    from tools.bst_native_build_tracer import pair_events, parse_trace_log

    log = tmp_path / "clean.log"
    subprocess.run(
        [spine, "--", "/bin/sh", "-c", "(sleep 0.1; true) & wait; exit 0"],
        env={**os.environ, "BST_TRACE_LOG": str(log),
             "BST_TRACE_ELEMENT": "e.bst", "BST_TRACE_INVOCATION": "inv"},
        capture_output=True, text=True, timeout=60,
    )

    records = pair_events(parse_trace_log(log.read_text()))

    assert [r for r in records if r["open"]] == []


class TestWhenSeizeIsUnavailableTheSpineExecsRatherThanWrapping:
    """UX-140: the branch taken in *every* environment without ptrace,
    and until this seam existed nothing could reach it on a machine that
    has it - `grep -rn seize tests/` was empty.

    It used to `waitpid` and return `128 + WTERMSIG`, rendering a signal
    death as a normal exit. That is the same WIFSIGNALED-vs-WIFEXITED
    confusion this file's own UX-106 correction documents as wrong, with
    BuildStream as the parent that reads it. Measured before the fix:
    returncode **143** where untraced gives **-15**, and one extra
    process alive for the whole build.
    """

    def _kill_after(self, argv, env, signal_name="SIGTERM", delay=0.4):
        import signal as signals
        import time

        process = subprocess.Popen(argv, env=env)
        time.sleep(delay)
        process.send_signal(getattr(signals, signal_name))
        return process.wait(timeout=30)

    def test_a_signal_killed_command_reaches_the_caller_as_a_signal(
            self, spine, tmp_path):
        """`subprocess` reports WIFSIGNALED as a *negative* returncode -
        the technique that caught this class of bug before."""
        log = tmp_path / "trace.log"
        env = {**os.environ, "BST_TRACE_LOG": str(log),
               "BST_TRACE_SPINE_FAIL_SEIZE": "1"}

        traced = self._kill_after([spine, "--", "/bin/sh", "-c", "sleep 30"], env)
        untraced = self._kill_after(["/bin/sh", "-c", "sleep 30"], dict(os.environ))

        assert traced == untraced == -15, (
            f"traced {traced}, untraced {untraced} - the fallback must be "
            f"indistinguishable from not being there")

    def test_the_exit_status_of_a_normal_command_survives_too(self, spine, tmp_path):
        log = tmp_path / "trace.log"

        result = subprocess.run(
            [spine, "--", "/bin/sh", "-c", "exit 7"],
            env={**os.environ, "BST_TRACE_LOG": str(log),
                 "BST_TRACE_SPINE_FAIL_SEIZE": "1"},
            capture_output=True, text=True, timeout=30)

        assert result.returncode == 7

    def test_no_wrapper_process_lingers(self, spine, tmp_path):
        """The spine *becomes* the command. An extra process per sandbox,
        on every machine without ptrace, is a tracer that changed the
        build it was measuring."""
        import time

        log = tmp_path / "trace.log"
        marker = tmp_path / "pids"
        process = subprocess.Popen(
            [spine, "--", "/bin/sh", "-c",
             f"sleep 5 & echo $$ > {marker}; wait"],
            env={**os.environ, "BST_TRACE_LOG": str(log),
                 "BST_TRACE_SPINE_FAIL_SEIZE": "1"})
        time.sleep(0.6)
        try:
            # The spine's own pid *is* the shell's, because it exec'd.
            shell_pid = int(marker.read_text().strip())
            assert shell_pid == process.pid, (
                f"the command runs as pid {shell_pid} under a wrapper at "
                f"{process.pid} - the spine did not exec")
        finally:
            process.kill()
            process.wait(timeout=30)

    def test_the_degradation_is_recorded_before_control_transfers(
            self, spine, tmp_path):
        """Exec destroys this process image, so a record written after it
        would never exist. "We could not trace" and "there was nothing to
        trace" must not look the same."""
        log = tmp_path / "trace.log"

        subprocess.run(
            [spine, "--", "/bin/sh", "-c", "exit 0"],
            env={**os.environ, "BST_TRACE_LOG": str(log),
                 "BST_TRACE_SPINE_FAIL_SEIZE": "1"},
            capture_output=True, text=True, timeout=30)

        assert "reason=seize-failed" in log.read_text()

    def test_the_seam_is_absent_from_the_shims_injected_environment(self):
        """Asserted alongside the other two seams: it ships in the
        binary, so it has to be inert in every real capture."""
        from tools.native_trace.bwrap_shim import build_shim_argv

        argv = build_shim_argv(
            "/usr/bin/bwrap", ["--", "sh", "-c", "true"],
            "/bind", "/dst", "/dst/hook.so", "/dst/trace.log", spine="/dst/spine",
        )

        assert not any("FAIL_SEIZE" in str(arg) for arg in argv)

    def test_without_the_seam_the_traced_path_is_what_runs(self, spine, tmp_path):
        """The seam must not leak into a normal run: with it unset the
        spine traces, so there is no degradation at all."""
        log = tmp_path / "trace.log"

        result = subprocess.run(
            [spine, "--", "/bin/sh", "-c", "exit 0"],
            env={**os.environ, "BST_TRACE_LOG": str(log)},
            capture_output=True, text=True, timeout=30)

        assert result.returncode == 0
        assert "seize-failed" not in (log.read_text() if log.exists() else "")


def test_a_site_that_names_no_restart_is_rejected_rather_than_ignored(spine, tmp_path):
    """UX-141: `resume()` matches by `strcmp`, so a stale name injects
    nothing and the test asking for it exercises the ordinary path while
    reading as coverage. Two of them did exactly that for a round, one of
    them inside the pinned bst tier."""
    result = subprocess.run(
        [spine, "--", "/bin/sh", "-c", "exit 7"],
        env={**os.environ, "BST_TRACE_LOG": str(tmp_path / "t.log"),
             "BST_TRACE_SPINE_FAIL_CONT_AT": "initial"},
        capture_output=True, text=True, timeout=30,
    )

    assert result.returncode == 2, "a stale site name ran the build instead"
    assert "names no restart site" in result.stderr
    assert "attach" in result.stderr, "the error does not say what the sites are"


class TestAGroupStoppedTraceeIsNotResumedByADetach:
    """UX-152: UX-143 shipped this function with the bug it was filed
    against, and the log claimed otherwise.

    Under `PTRACE_SEIZE` a group-stop **is** an event-stop -
    `wstatus >> 16 == PTRACE_EVENT_STOP`, with `WSTOPSIG` carrying the
    job-control signal. `detach_signal` tested `event != 0` *first*, so
    it returned 0 for precisely the case it was written for, on every
    detach path at once. Detaching with 0 resumes a suspended process;
    untraced it would have stayed stopped.

    Checked through a decision table rather than a live process, and the
    reason is itself a finding: when the traced command exits, the
    survivor's process group is orphaned, and POSIX has the kernel send
    SIGHUP+SIGCONT to an orphaned group with stopped members. The
    survivor is therefore resumed moments after the detach whatever
    signal it carried - measured, identically, on a correct spine and a
    broken one. A state-`T` probe cannot tell them apart, which is why
    UX-143's acceptance asked for one and it was never written.
    """

    def _table(self, spine):
        result = subprocess.run(
            [spine], env={**os.environ, "BST_TRACE_SPINE_SELFTEST": "detach-signal"},
            capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        return {
            line.split()[0]: int(line.split()[1])
            for line in result.stdout.splitlines() if line.strip()}

    @pytest.mark.parametrize("case,expected", [
        ("group-stop-SIGSTOP", signal.SIGSTOP),
        ("group-stop-SIGTSTP", signal.SIGTSTP),
        ("group-stop-SIGTTIN", signal.SIGTTIN),
        ("group-stop-SIGTTOU", signal.SIGTTOU),
    ])
    def test_a_group_stop_detaches_with_its_own_signal(self, spine, case, expected):
        """Re-delivering it is what keeps the process stopped."""
        assert self._table(spine)[case] == expected

    @pytest.mark.parametrize("case", [
        "attach-stop-SIGTRAP", "exec-event", "exit-event", "signal-SIGTRAP",
    ])
    def test_the_tracers_own_stops_detach_with_nothing(self, spine, case):
        """Passing SIGTRAP on would kill a process that never asked for
        it - the mirror error, and the reason the group-stop test comes
        first rather than the event test being deleted."""
        assert self._table(spine)[case] == 0

    def test_a_real_signal_still_reaches_the_process(self, spine):
        assert self._table(spine)["signal-SIGSEGV"] == signal.SIGSEGV

    def test_all_three_detach_paths_use_the_one_rule(self):
        """The degrade branch kept its own copy (`pass_through`) and so
        kept resuming group-stopped tracees after the other two were
        fixed. One rule, three call sites."""
        import re

        source = SPINE_SOURCE.read_text()
        # The call spans two lines at three of the sites, so match the
        # whole call rather than a line containing part of it.
        calls = re.findall(r"ptrace\(PTRACE_DETACH[^;]*;", source, re.S)
        assert len(calls) == 5, [c.split("\n")[0] for c in calls]

        by_rule = [c for c in calls if "detach_signal" in c]
        assert len(by_rule) == 3, (
            f"{len(by_rule)} of 5 detach sites use detach_signal; the degrade "
            f"branch keeping its own copy is what UX-152 was filed for")

        # The other two are `resume`'s failure detach and the
        # listen-failed branch, which pass on the signal they were handed
        # rather than re-deriving it from a wait status they do not have.
        others = [c for c in calls if "detach_signal" not in c]
        assert all("(long)sig" in c for c in others), others
