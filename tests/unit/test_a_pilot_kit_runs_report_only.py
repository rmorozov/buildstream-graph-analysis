"""UX-1288: the pilot kit runs report-only, and its switches live in one table.

The guide's switch table, the script's switch block and the workflow's
`env:` name the same variables with the same defaults, every way round.
Every `bga` command and flag the kit runs or the guide names exists. A
dry run of `capture` then `report` - a stub standing in for the build -
prints a ci-comment and exits 0 on a slower verdict, through
`UX-1286`'s real `--bundles`. The guide's band threshold and exit-6
row are what the kit does (`UX-1296`), and every verdict and build wall
reaches a step that keeps it, pull requests included (`UX-1297`).
"""

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "examples/ci/bga-pilot.sh"
WORKFLOW = REPO / "examples/ci/bga-pilot.yml"
GUIDE = REPO / "docs/guides/pilot.md"
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"
SECOND = 1_000_000

NO_SHELLCHECK = "shellcheck is not installed (pip install shellcheck-py)"

sys.path.insert(0, str(REPO))


def _env(**extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PILOT_", "BGA_"))}
    env["PYTHONPATH"] = str(REPO)
    env.update(extra)
    return env


def _bga_help(*words) -> str:
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", *words, "--help"], cwd=REPO, env=_env(), capture_output=True, text=True
    )
    assert done.returncode == 0, f"bga {' '.join(words)} --help: {done.stderr}"
    return done.stdout


def _names(helptext: str, flag: str) -> bool:
    """The whole flag, not a prefix argparse would also accept."""
    return re.search(rf"{re.escape(flag)}(?![\w-])", helptext) is not None


# --- the switch table, three ways ---


def _script_switches() -> dict:
    text = SCRIPT.read_text(encoding="utf-8")
    block = text.split("# --- switches:", 1)[1].split("# --- end switches ---", 1)[0]
    return dict(re.findall(r'^: "\$\{(PILOT_[A-Z_]+):=(.*)\}"$', block, re.M))


def _guide_switches() -> dict:
    text = GUIDE.read_text(encoding="utf-8")
    section = text.split("## Every switch", 1)[1].split("\n## ", 1)[0]
    rows = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        name = re.fullmatch(r"`(PILOT_[A-Z_]+)`", cells[0]) if len(cells) > 2 else None
        if name:
            default = re.fullmatch(r"`(.*)`", cells[1])
            rows[name.group(1)] = default.group(1) if default else ""
    return rows


def _workflow_switches() -> dict:
    env = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["env"]
    return {k: str(v) for k, v in env.items() if k.startswith("PILOT_")}


class TestOneTableOfSwitches:
    def test_the_guide_and_the_script_name_the_same_switches(self):
        script, guide = _script_switches(), _guide_switches()
        assert script, "no switch block read from the script"
        assert sorted(set(script) - set(guide)) == [], "in the script, missing from the guide's table"
        assert sorted(set(guide) - set(script)) == [], "in the guide's table, not a switch in the script"

    def test_the_workflow_sets_every_switch_and_no_other(self):
        script, workflow = _script_switches(), _workflow_switches()
        assert sorted(set(script) ^ set(workflow)) == []

    def test_the_defaults_agree_everywhere(self):
        script, guide, workflow = _script_switches(), _guide_switches(), _workflow_switches()
        for other in (guide, workflow):
            shared = set(script) & set(other)
            assert {k: other[k] for k in shared} == {k: script[k] for k in shared}

    def test_the_jobserver_is_off_by_default(self):
        for switches in (_script_switches(), _guide_switches(), _workflow_switches()):
            assert switches["PILOT_JOBSERVER"] == "off"


# --- every bga command and flag named exists ---


def _named_invocations():
    """`(source, [words...], [--flags])` for each `bga ...` the guide names in code."""
    text = GUIDE.read_text(encoding="utf-8")
    for span in re.findall(r"`(bga [^`]+)`", text):
        words = span.split()[1:]
        subs = [w for w in words if re.fullmatch(r"[a-z][a-z-]*", w)][:2]
        yield "guide", subs, [w for w in words if w.startswith("--")]


class TestEveryCommandExists:
    def test_the_script_calls_only_real_subcommands(self):
        top = _bga_help()
        called = set(re.findall(r"(?:^\s*|\bif |\bthen )bga ([a-z][a-z-]*)", SCRIPT.read_text(encoding="utf-8"), re.M))
        assert called >= {"doctor", "capture", "bundle", "compare"}
        assert [s for s in sorted(called) if not re.search(rf"^\s+{s}\s", top, re.M)] == []

    def test_every_flag_the_guide_names_exists(self):
        for _source, subs, flags in _named_invocations():
            words = subs if subs[:1] == ["capture"] else subs[:1]
            helptext = _bga_help(*words)
            for flag in flags:
                assert _names(helptext, flag), f"bga {' '.join(words)} has no {flag}"


# --- the dry run ---


FAKE_CAPTURE = textwrap.dedent(
    """\
    import json, os, shutil, sys
    argv = sys.argv[1:]
    with open(os.environ["FAKE_ARGV_LOG"], "a") as log:
        log.write(json.dumps(["capture", "run", *argv]) + "\\n")
    run_dir = argv[argv.index("--run-dir") + 1]
    shutil.copytree(os.environ["FAKE_CAPTURE_SOURCE"], run_dir)
    """
)


def _run_dir(path: Path, seconds: float, host=None) -> Path:
    """The golden run, `app.bst` lasting `seconds`, declaring `review` - `test_the_band_comes_from_the_class`'s shape."""
    from bga import buildclass

    path.mkdir(parents=True)
    trace = json.loads((GOLDEN / "trace.json").read_text())
    for span in trace["spans"]:
        if span["task_key"].startswith("app.bst"):
            span["dur_us"] = int(seconds * SECOND)
    context = json.loads((GOLDEN / "run-context.json").read_text())
    context["wall_clock"]["end_us"] = max(s["ts_us"] + s["dur_us"] for s in trace["spans"])
    context["build_class"] = buildclass.declare("review", {})
    if host:
        context["host_manifest"] = host
    (path / "graph.json").write_text((GOLDEN / "graph.json").read_text())
    (path / "trace.json").write_text(json.dumps(trace))
    (path / "run-context.json").write_text(json.dumps(context))
    return path


class Pilot:
    """A tmp CI agent: a `bga` on PATH that is this tree, except the build itself."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.kept = tmp / "kept"
        self.argv_log = tmp / "argv.jsonl"
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        (tmp / "fake_capture.py").write_text(FAKE_CAPTURE)
        shim = bin_dir / "bga"
        shim.write_text(
            "#!/usr/bin/env bash\n"
            'printf \'%s\\n\' "$*" >> "$FAKE_ALL_LOG"\n'
            f'if [ "$1" = capture ] && [ "$2" = run ]; then shift 2; exec {sys.executable} {tmp}/fake_capture.py "$@"; fi\n'
            f'exec {sys.executable} -m bga.cli "$@"\n'
        )
        shim.chmod(0o755)
        (tmp / "tmpdir").mkdir()
        (tmp / "tmpdir/bga-pilot").mkdir()
        (tmp / "tmpdir/bga-pilot/ready").touch()
        self.path = f"{bin_dir}:{os.environ['PATH']}"

    def keep(self, stamp: str, seconds: float, host=None) -> None:
        snapshot = _run_dir(self.tmp / "snapshots" / stamp / "run", seconds, host).parent
        target = self.kept / "review/default"
        target.mkdir(parents=True, exist_ok=True)
        done = subprocess.run(
            [
                sys.executable,
                "-m",
                "bga.cli",
                "bundle",
                "--export",
                str(snapshot),
                "-o",
                str(target / f"{stamp}.bga-bundle.tar.gz"),
            ],
            env=_env(),
            capture_output=True,
            text=True,
        )
        assert done.returncode == 0, done.stderr

    def run(self, sub: str, candidate_seconds: float = 130, host=None, **switches):
        source = _run_dir(self.tmp / f"candidate-{len(list(self.tmp.glob('candidate-*')))}", candidate_seconds, host)
        settings = {
            "PATH": self.path,
            "TMPDIR": str(self.tmp / "tmpdir"),
            "PILOT_KEEP_DIR": str(self.kept),
            "PILOT_TARGET": "all.bst",
            "PILOT_REVIEW_SAMPLE": "100",
            "FAKE_CAPTURE_SOURCE": str(source),
            "FAKE_ARGV_LOG": str(self.argv_log),
            "FAKE_ALL_LOG": str(self.tmp / "all.log"),
        }
        env = _env(**{**settings, **switches})
        return subprocess.run(
            ["bash", str(SCRIPT), sub, "--", "true"], cwd=self.tmp, env=env, capture_output=True, text=True
        )

    def bga_calls(self) -> list:
        return (self.tmp / "all.log").read_text().splitlines()


@pytest.fixture
def pilot(tmp_path):
    return Pilot(tmp_path)


class TestTheScriptIsClean:
    def test_bash_parses_it(self):
        done = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        assert done.returncode == 0, done.stderr

    def test_shellcheck_is_clean(self):
        if shutil.which("shellcheck") is None:
            pytest.skip(NO_SHELLCHECK)
        done = subprocess.run(["shellcheck", str(SCRIPT)], capture_output=True, text=True)
        assert done.returncode == 0, done.stdout

    def test_setup_refuses_a_commit_that_is_not_a_full_sha(self, pilot):
        done = subprocess.run(
            ["bash", str(SCRIPT), "setup"], env=_env(PILOT_BGA_COMMIT="main"), capture_output=True, text=True
        )
        assert done.returncode == 2 and "full 40-character commit sha" in done.stderr


class TestCapture:
    def test_a_capture_keeps_a_bundle_in_its_class_with_the_jobserver_off(self, pilot):
        done = pilot.run("capture")

        assert done.returncode == 0, done.stderr
        kept = list((pilot.kept / "review/default").glob("*.bga-bundle.tar.gz"))
        assert len(kept) == 1, done.stderr
        argv = json.loads(pilot.argv_log.read_text().splitlines()[0])
        assert argv[argv.index("--jobserver") + 1] == "off"
        assert "--trace-opens" not in argv

    def test_an_unsampled_review_build_runs_without_bga(self, pilot):
        done = pilot.run("capture", PILOT_REVIEW_SAMPLE="0")

        assert done.returncode == 0, done.stderr
        assert "not in the 0% review sample" in done.stderr
        assert not pilot.argv_log.exists()

    def test_every_flag_the_capture_passes_exists(self, pilot):
        assert pilot.run("capture", PILOT_TRACE_OPENS="on").returncode == 0
        for line in pilot.bga_calls():
            words = line.split()
            helptext = _bga_help(*words[:2]) if words[0] == "capture" else _bga_help(words[0])
            for flag in [w for w in words if w.startswith("--")]:
                assert _names(helptext, flag), f"bga {words[0]} has no {flag}"


class TestReport:
    """Two kept bundles plus a candidate 30% slower: the comment prints, the job passes."""

    def test_a_slower_candidate_comments_and_exits_0(self, pilot):
        pilot.keep("20260901T000000Z", 100)
        pilot.keep("20260902T000000Z", 100)
        assert pilot.run("capture").returncode == 0

        done = pilot.run("report")

        assert done.returncode == 0, done.stderr
        assert done.stdout.startswith("<!-- bga-ci-comment -->"), done.stdout + done.stderr
        assert "REGRESSED" in done.stdout
        assert "verdict exit 4" in done.stderr
        for line in pilot.bga_calls():
            words = line.split()
            helptext = _bga_help(words[0]) if words[0] != "capture" else _bga_help(*words[:2])
            assert [w for w in words if w.startswith("--") and not _names(helptext, w)] == []

    def test_enforcing_reapplies_the_gate(self, pilot):
        pilot.keep("20260901T000000Z", 100)
        pilot.keep("20260902T000000Z", 100)
        assert pilot.run("capture").returncode == 0

        done = pilot.run("report", PILOT_ENFORCE="on")

        assert done.returncode == 4, done.stderr

    def test_five_kept_runs_judge_against_the_band(self, pilot):
        for day, seconds in enumerate((98, 99, 100, 101, 102), 1):
            pilot.keep(f"202609{day:02d}T000000Z", seconds)
        assert pilot.run("capture").returncode == 0

        done = pilot.run("report")

        assert done.returncode == 0, done.stderr
        assert "judged against the band" in done.stderr
        assert "\tband\t4" in (pilot.kept / "verdicts.tsv").read_text()


HOST_4 = {"schema": "host/v2", "cpu_model": "Xeon A", "cpu_count": 4, "memory_bytes": 16 << 30}
HOST_8 = {"schema": "host/v2", "cpu_model": "EPYC B", "cpu_count": 8, "memory_bytes": 32 << 30}


def _exit_row(code: str) -> list:
    section = GUIDE.read_text(encoding="utf-8").split("## What the exit codes mean here", 1)[1].split("\n## ", 1)[0]
    rows = [
        [c.strip() for c in line.strip().strip("|").split("|")] for line in section.splitlines() if line.startswith("|")
    ]
    return next(r for r in rows if r[0] == code)


class TestTheBandThreshold:
    """UX-1296: the band excludes both principals, and the kit's baseline is a kept run."""

    @pytest.mark.parametrize("prior, judged", [(3, "rule"), (4, "band")])
    def test_the_band_needs_four_kept_runs_before_the_candidate(self, pilot, prior, judged):
        for day in range(1, prior + 1):
            pilot.keep(f"202609{day:02d}T000000Z", 99 + day % 3)
        assert pilot.run("capture").returncode == 0

        done = pilot.run("report")

        assert done.returncode == 0, done.stderr
        assert (pilot.kept / "verdicts.tsv").read_text().split("\t")[3] == judged, done.stderr

    def test_the_guide_reads_the_threshold_off_min_baseline_runs(self):
        from bga.compare import MIN_BASELINE_RUNS

        prose = GUIDE.read_text(encoding="utf-8").split("**`report`**", 1)[1].split("\n## ", 1)[0]
        below = re.search(r"Below (\d+) kept runs of the class before\s+this build", prose)
        row = re.fullmatch(r"fewer than (\d+) kept runs of the class before this build", _exit_row("8")[1])
        assert below and row, "the guide's band threshold sentence or exit-8 row moved"
        assert int(below.group(1)) == int(row.group(1)) == MIN_BASELINE_RUNS + 1

    def test_a_cross_host_refusal_still_comments(self, pilot):
        for day in range(1, 5):
            pilot.keep(f"202609{day:02d}T000000Z", 100, host=HOST_4)
        assert pilot.run("capture", host=HOST_8).returncode == 0

        done = pilot.run("report")

        assert done.returncode == 0, done.stderr
        assert done.stdout.startswith("<!-- bga-ci-comment -->"), done.stderr
        assert "\trule\t6" in (pilot.kept / "verdicts.tsv").read_text()
        assert "Cross-host gate FAILED" in done.stderr
        assert _exit_row("6")[2].startswith("comments"), "the guide's exit-6 row says the kit does not comment"


LEDGERS = ("verdicts.tsv", "builds.tsv")


def _steps() -> list:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["build"]["steps"]


def _keeps_on_every_event(step: dict, ledger: str) -> bool:
    """An artifact, on every event: a pull request's cache never leaves the pull request."""
    keep = _workflow_switches()["PILOT_KEEP_DIR"]
    path = str(step.get("with", {}).get("path", ""))
    paths = [p.strip().replace("${{ env.PILOT_KEEP_DIR }}", keep) for p in path.splitlines()]
    return (
        str(step.get("uses", "")).startswith("actions/upload-artifact@")
        and step.get("if") == "always()"
        and any(fnmatch.fnmatch(f"{keep}/{ledger}", p) or p.rstrip("/") == keep for p in paths)
    )


class TestEveryReadingIsKept:
    """UX-1297: every report's verdict and every build's wall reach a step that keeps it."""

    @pytest.mark.parametrize("ledger", LEDGERS)
    def test_the_workflow_keeps_the_ledger_after_the_report_on_every_event(self, ledger):
        steps = _steps()
        report = next(i for i, s in enumerate(steps) if "bga-pilot.sh report" in str(s.get("run", "")))
        assert [s["name"] for s in steps[report + 1 :] if _keeps_on_every_event(s, ledger)], f"no step keeps {ledger}"

    def test_the_guide_names_where_the_readings_land(self):
        artifact = next(s for s in _steps() if _keeps_on_every_event(s, "verdicts.tsv"))["with"]["name"]
        section = GUIDE.read_text(encoding="utf-8").split("## What two weeks measure", 1)[1].split("\n## ", 1)[0]
        assert [n for n in (artifact, *LEDGERS) if f"`{n}`" not in section] == []

    @pytest.mark.parametrize(
        "arm, switches", [("captured", {}), ("plain", {"PILOT_REVIEW_SAMPLE": "0"}), ("unready", {})]
    )
    def test_every_build_writes_its_wall(self, pilot, arm, switches):
        if arm == "unready":
            (pilot.tmp / "tmpdir/bga-pilot/ready").unlink()

        assert pilot.run("capture", **switches).returncode == 0

        fields = (pilot.kept / "builds.tsv").read_text().rstrip("\n").split("\t")
        assert fields[1:4] == ["review", "default", arm] and fields[4].isdigit() and fields[5] == "0", fields
