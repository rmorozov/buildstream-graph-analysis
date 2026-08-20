#!/usr/bin/env python3
"""UX-125: the setup half-day, checked in a minute.

Every capture-capable environment this project has ever stood up - three
times in one audit alone - was assembled by failure. `pluginbase` breaks
under a distro-patched setuptools until a venv is used;
`buildstream-plugins` turns out to be missing at the first `cmake`-kind
element ("No element plugin registered"); `bwrap` is present but cannot
bring up loopback until a sysctl is applied; there is no C compiler for
the hook and spine; runtimes and toolchains are not staged, so the
sandbox has no shell.

Every one of those answers is already written down somewhere in this
repository - in `ci.yml`'s step comments, in `stage_*.sh` headers, in the
ingestion guide. The knowledge exists; only the *sequence* of it is the
user's problem, and a sequence is what a program is good at.

So this invents no check. Each one fronts a failure that has really
happened, and cites it. It is read-only by contract: it recommends
`stage_runtimes.sh`, it never runs it - a diagnostic that mutates the
thing it is diagnosing cannot be run twice with the same meaning.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import List, Optional

# Findings-style ids (UX-75), so a script can key on the check rather
# than on its prose.
OK = "ok"
FAIL = "fail"
WARN = "warn"
SKIP = "skip"

# BuildStream's own supported line for this project. Not a hard failure
# on mismatch - a newer bst may work fine - but a difference worth
# knowing when something else misbehaves.
SUPPORTED_BST = "2."


def _check(id, status, summary, remedy=None, detail=None) -> dict:
    return {"id": id, "status": status, "summary": summary,
            "remedy": remedy, "detail": detail or []}


def check_bst() -> dict:
    """`bst` on PATH, and which line it is."""
    path = shutil.which("bst")
    if not path:
        # UX-150 follow-up, found by the installed-capture job on its
        # first run: invoking `bga` by absolute path - `/venv/bin/bga` -
        # does *not* put that venv's `bin` on PATH, so a `bst` installed
        # right beside it is invisible to `shutil.which` and to every
        # subprocess the capture launches. "Not installed" and "installed
        # next to me and not on PATH" are different problems, and only
        # one of them is fixed by installing something.
        sibling = os.path.join(os.path.dirname(sys.executable), "bst")
        if os.access(sibling, os.X_OK):
            return _check(
                "bst-present", FAIL,
                f"bst is not on PATH, but there is one at {sibling}",
                remedy=f"that is the venv this `bga` lives in - activate it "
                       f"(`source {os.path.dirname(sys.executable)}/activate`) or "
                       f"put it on PATH. Running the console script by its full "
                       f"path does not do that, and the capture launches `bst` "
                       f"as a subprocess, so it needs PATH too")
        return _check(
            "bst-present", FAIL, "bst is not on PATH",
            remedy="pip install 'bga[bst]' (in a virtualenv - a distro-patched "
                   "setuptools breaks pluginbase, which is how three separate "
                   "environments for this project failed to install)")
    try:
        version = subprocess.run([path, "--version"], capture_output=True,
                                 text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        return _check("bst-present", FAIL, f"bst is on PATH but would not run: {error}",
                      remedy="reinstall BuildStream, ideally into a fresh virtualenv")
    if not version.startswith(SUPPORTED_BST):
        return _check(
            "bst-present", WARN,
            f"bst {version} is outside the {SUPPORTED_BST}x line this project is "
            f"verified against",
            remedy="nothing to do unless something else misbehaves - recorded so "
                   "a later surprise has a first suspect")
    return _check("bst-present", OK, f"bst {version}")


def check_bwrap() -> dict:
    """bubblewrap present **and functional**.

    Presence is not the check that matters. `bst-smoke` exists in CI
    because bwrap's own namespace setup succeeds and then the sandbox
    fails to bring up loopback - Ubuntu 24.04+ withholds CAP_NET_ADMIN in
    an unprivileged user namespace by default, so the failure appears
    deep inside a build rather than at any point a user would connect to
    a system setting.
    """
    path = shutil.which("bwrap")
    if not path:
        return _check("bwrap-present", FAIL, "bwrap is not on PATH",
                      remedy="apt-get install -y bubblewrap (or your distro's "
                             "bubblewrap package) - BuildStream's sandbox needs it")
    try:
        probe = subprocess.run(
            [path, "--dev-bind", "/", "/", "--unshare-pid", "--unshare-net",
             "/bin/sh", "-c", "exit 0"],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return _check("bwrap-works", FAIL, f"bwrap would not run: {error}")
    if probe.returncode == 0:
        return _check("bwrap-works", OK, "bwrap builds a sandbox and runs in it")

    message = (probe.stderr or "").strip()
    if "loopback" in message or "RTM_NEWADDR" in message:
        return _check(
            "bwrap-works", FAIL,
            "bwrap cannot configure loopback in its own network namespace",
            remedy="sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0 "
                   "- Ubuntu 24.04+ defaults this to 1, which withholds "
                   "CAP_NET_ADMIN inside an unprivileged user namespace. Confirmed "
                   "on a real GitHub Actions runner; see ci.yml's bst-smoke job.",
            detail=[message])
    return _check("bwrap-works", FAIL, "bwrap failed to build a sandbox",
                  remedy="run the command this printed by hand to see why",
                  detail=[message])


def check_compiler() -> dict:
    """A C compiler for the hook and the spine.

    The same check `compile_hook` performs, moved before the build rather
    than after twenty minutes of one.
    """
    cc = shutil.which("cc") or shutil.which("gcc")
    if not cc:
        return _check(
            "c-compiler", FAIL,
            "no C compiler (cc/gcc) on PATH - Plane 2 compiles its LD_PRELOAD "
            "hook and ptrace spine at capture time",
            remedy="apt-get install -y build-essential (Plane 1 and Plane 3 work "
                   "without it; only `bga capture` needs it)")

    # UX-153: probe, do not check - this file's own principle, applied to
    # itself. A compiler on PATH is not the question; the capture needs
    # two *capabilities* from it, and they fail separately. `-static` in
    # particular needs a static libc, which `build-essential` alone does
    # not provide - and the spine is the half that goes missing, silently,
    # on a machine where the hook compiles fine.
    missing = [name for name, argv in (
        ("-shared -fPIC (the LD_PRELOAD hook)", [cc, "-shared", "-fPIC",
                                                 "-o", "/dev/null", "-x", "c", "-"]),
        ("-static (the ptrace spine)", [cc, "-static",
                                        "-o", "/dev/null", "-x", "c", "-"]),
    ) if not _compiles(argv)]
    if missing:
        return _check(
            "c-compiler", WARN,
            f"{cc} cannot link: {', '.join(missing)}",
            remedy="apt-get install -y build-essential libc6-dev "
                   "(a static libc is a separate package on some distributions; "
                   "without it the hook still works and `--trace-spine` does not)",
            detail=[f"probed by compiling a trivial program with {cc}"])
    return _check("c-compiler", OK, f"C compiler at {cc} links shared and static")


def _compiles(argv: List[str]) -> bool:
    """Whether a trivial program links with these flags.

    Fed on stdin so nothing is written anywhere, and output goes to
    `/dev/null`: a diagnostic that leaves files behind cannot be run
    twice with the same meaning (`UX-125`).
    """
    try:
        return subprocess.run(
            argv, input="int main(void){return 0;}\n", text=True,
            capture_output=True, timeout=120).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def check_stale_casd() -> dict:
    """Is a `buildbox-casd` already running that a capture would reuse?

    `UX-161` item 3, and it exists because `--capture`'s own probe
    structurally cannot see this: that probe isolates `HOME`
    (`UX-84`'s lesson), which starts a *fresh* daemon with the shim
    already on `$PATH`. So the chain can pass while the user's next
    real capture reuses a daemon sitting right there - and a passing
    chain would be read as "your next capture will work".

    A warning rather than a failure: a running daemon is a fact about
    the machine, not a broken environment, and `UX-147`'s caution about
    claiming more than the evidence supports still stands.
    """
    from .bst_native_build_tracer import detect_stale_casd
    found = detect_stale_casd()
    if not found:
        return _check("casd-fresh", OK,
                      "no buildbox-casd is running that a capture would reuse")
    described = ", ".join(
        f"pid {entry['pid']}"
        + (f" ({entry['age_s'] / 60:.0f}m old)" if entry.get("age_s") else "")
        for entry in found
    )
    return _check(
        "casd-fresh", WARN,
        f"a buildbox-casd is already running ({described})",
        remedy=("it was started by a `bst` that never saw a capture's PATH, so a "
                "build reusing it can miss the shim and capture nothing. Stop it "
                "before capturing - `bst shutdown`, or kill it - and `bst` will "
                "start a fresh one. Note the `--capture` chain probe cannot see "
                "this: it isolates HOME and so starts its own daemon."))


def check_scratch(project_dir: Optional[str] = None) -> List[dict]:
    """Can bga execute the shim it writes, and is `TMPDIR` sane?

    UX-155, from a field report that took two steps and where bga
    supplied the second. The shim bga puts on `$PATH` has to be
    *executed*, and it used to be written wherever `TMPDIR` pointed - so
    a `noexec` temp mount failed the capture inside `buildbox-run`,
    which reports `returncode 1` with the stderr swallowed. It now lives
    under the project's `.bga/tmp`, which moves the question to a
    directory the user can see but does not remove it.

    The `TMPDIR` half is the one worth checking even though bga no
    longer uses it. A *relative* `TMPDIR` is invisible to Python -
    `tempfile` treats it as a candidate and falls back - and fatal to
    `buildbox-casd`, whose C++ `mkdtemp` resolves it after the daemon
    has changed directory. The user who reported this had been told to
    set `TMPDIR` by bga's own error text.
    """
    findings = []
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir and not os.path.isabs(tmpdir):
        findings.append(_check(
            "tmpdir-absolute", FAIL,
            f"TMPDIR is set to the relative path {tmpdir!r}",
            remedy=(f"use an absolute path (TMPDIR={os.path.abspath(tmpdir)}) or "
                    f"unset it. BuildStream's helper daemons resolve TMPDIR "
                    f"after changing directory, so a relative value fails as "
                    f"`error in mkdtemp, errno: no such file or directory` from "
                    f"buildbox-casd - while Python silently falls back, which is "
                    f"why bga itself appears to accept it.")))
    elif tmpdir:
        findings.append(_check("tmpdir-absolute", OK, f"TMPDIR is absolute ({tmpdir})"))

    if not tmpdir:
        findings.append(_check("tmpdir-absolute", OK, "TMPDIR is not set"))

    if not project_dir:
        findings.append(_check(
            "scratch-executable", SKIP,
            "no project given, so there is no .bga/tmp to test"))
        return findings
    if not os.path.isdir(project_dir):
        # Probing would `makedirs` the whole chain and leave a `.bga` in a
        # path that is not a project. `check_project_loads` reports the
        # real problem; this one has nothing to say about it.
        findings.append(_check(
            "scratch-executable", SKIP,
            f"{project_dir} is not a directory"))
        return findings

    # Deliberately *not* `capture_scratch`: that creates `.bga/` (and the
    # store's `.gitignore` inside it) and would leave both behind, and
    # doctor is read-only by contract - `TestItNeverChangesAnything`
    # caught exactly that. Exec permission is a property of the mount,
    # so probing a directory beside `.bga` answers the same question and
    # can be removed completely.
    try:
        scratch = tempfile.mkdtemp(dir=project_dir, prefix=".bga-doctor-")
    except OSError as error:
        return findings + [_check(
            "scratch-executable", FAIL,
            f"bga cannot create a scratch directory in {project_dir} "
            f"({error.strerror})",
            remedy=("a capture writes its shim under this project's `.bga/tmp`, "
                    "so it needs to be writable"))]
    try:
        probe = os.path.join(scratch, "probe")
        with open(probe, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\nexit 0\n")
        os.chmod(probe, 0o755)
        try:
            subprocess.run([probe], check=True, timeout=30,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as error:
            findings.append(_check(
                "scratch-executable", FAIL,
                f"bga cannot execute a file it wrote to {project_dir} "
                f"({error.strerror})",
                remedy=("bga puts a `bwrap` shim on $PATH from this project's "
                        "`.bga/tmp`, so a noexec mount or an AppArmor rule "
                        "covering it fails the capture inside the sandbox layer, "
                        "where the error is swallowed. Mount the project with "
                        "exec permitted, or check out somewhere that is.")))
        except subprocess.SubprocessError as error:
            findings.append(_check(
                "scratch-executable", FAIL,
                f"a file bga wrote to {project_dir} would not run: {error}"))
        else:
            findings.append(_check(
                "scratch-executable", OK,
                f"bga can write and execute from {project_dir}"))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return findings


def check_plane3(project_name: Optional[str] = None) -> dict:
    """Whether BuildStream has written logs this machine can mine.

    Plane 3 needs no capture at all, which makes "is there anything
    there?" the only question - and one nothing answered before.
    """
    from .bst_cache_logs import default_log_root, summarize_log_tree

    root = default_log_root()
    if not os.path.isdir(root):
        return _check(
            "plane3-logs", WARN, f"no BuildStream log tree at {root}",
            remedy="run any `bst build` - these logs are BuildStream's own, and "
                   "Plane 3 reads them with no capture needed")
    projects = summarize_log_tree(root)
    if not projects:
        return _check("plane3-logs", WARN, f"{root} exists but holds no element logs",
                      remedy="run any `bst build` first")
    if project_name:
        match = next((p for p in projects if p["project"] == project_name), None)
        if match:
            return _check(
                "plane3-logs", OK,
                f"{match['logs']} log(s) for {project_name} in {root}")
        return _check(
            "plane3-logs", WARN,
            f"{root} has logs, but none for {project_name}",
            remedy=f"build this project once; the tree holds "
                   f"{', '.join(p['project'] for p in projects[:4])}")
    return _check("plane3-logs", OK,
                  f"{len(projects)} project(s) with logs in {root}")


def check_project_loads(project_dir: str) -> List[dict]:
    """The project loads, and every plugin it names is installed.

    "No element plugin registered for kind cmake" is the failure this
    fronts, and it arrives at the *first element of that kind* - which on
    a large project can be minutes in.
    """
    conf = os.path.join(project_dir, "project.conf")
    if not os.path.isfile(conf):
        return [_check("project-loads", FAIL,
                       f"{project_dir} has no project.conf",
                       remedy="point this at a BuildStream project directory")]

    bst = shutil.which("bst")
    if not bst:
        return [_check("project-loads", SKIP,
                       "cannot load the project without bst")]

    # UX-142: whatever this project actually declares, not `all.bst`.
    # Every `examples/*` here ships one, and reading that fixture
    # convention back as a world fact made this check fail every real
    # project - freedesktop-sdk included - from the first command the
    # walkthrough teaches.
    targets = discover_elements(project_dir)
    if not targets:
        return [_check(
            "project-loads", WARN,
            f"no element found to probe under {element_path(project_dir)}/",
            remedy="this check loads one of the project's own elements; a "
                   "project with none cannot be probed, which is not the same "
                   "as one that fails to load")]

    result = None
    for target in targets[:_PROBE_LIMIT]:
        result = subprocess.run(
            [bst, "show", "--deps", "none", "--format", "%{name}", target],
            cwd=project_dir, capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            return [_check("project-loads", OK,
                           f"{project_dir} loads ({target})")]

    message = (result.stderr or result.stdout or "").strip()
    remedy = ("read the error below - `bst show` is what this ran, and it is "
              "the same thing a build starts with")
    if "plugin registered" in message:
        # Two different problems wear the same error, and the remedies
        # are opposites. Checking which one it is costs an import.
        remedy = (
            "pip install buildstream-plugins - it carries the `cmake`, `meson`, "
            "`autotools`, `make` and `git` kinds that are not in BuildStream "
            "core, and its absence surfaces only at the first element of such a "
            "kind"
            if not _plugins_package_installed() else
            "buildstream-plugins *is* installed, so this project has not "
            "declared it: add a `plugins:` block to project.conf naming the "
            "kinds it uses (origin: pip, package-name: buildstream-plugins). "
            "See examples/06-macro-micro-optimization/project.conf"
        )
    probed = ", ".join(targets[:_PROBE_LIMIT])
    return [_check("project-loads", FAIL,
                   f"the project does not load (tried {probed})", remedy=remedy,
                   detail=message.splitlines()[-6:])]


# How many of a project's own elements to try before calling it broken.
# One is not enough - a single element can fail on its own plugin while
# the project is fine - and every extra one costs a `bst` startup, which
# is the whole runtime of this check.
_PROBE_LIMIT = 5


def element_path(project_dir: str) -> str:
    """The project's declared `element-path`, or BuildStream's default.

    UX-153: one implementation, in the tracer, because the census there
    needs the same answer in seven places and two copies of a rule about
    project layout is how this became a finding twice.
    """
    from .bst_native_build_tracer import element_path as _element_path

    return _element_path(project_dir)


def discover_elements(project_dir: str) -> List[str]:
    """Element names this project declares, as `bst show` takes them.

    Sorted shallowest first, then by name: a top-level element is the
    likeliest to be a real target and the least likely to be an
    architecture-specific leaf, and stable order keeps the check's own
    output reproducible.
    """
    root = os.path.join(project_dir, element_path(project_dir))
    if not os.path.isdir(root):
        return []
    found = []
    for base, _dirs, files in os.walk(root):
        for name in files:
            if name.endswith(".bst"):
                found.append(os.path.relpath(os.path.join(base, name), root))
    return sorted(found, key=lambda name: (name.count(os.sep), name))


def _plugins_package_installed() -> bool:
    """Whether `buildstream-plugins` is importable.

    Its absence and a project failing to *declare* it produce the
    identical "No element plugin registered for kind" error, and the two
    remedies are opposites - install a package, or edit project.conf.
    Telling a user to install something they already have is how a
    diagnostic loses its reader.
    """
    import importlib.util

    return importlib.util.find_spec("buildstream_plugins") is not None


def check_staged_sources(project_dir: str) -> List[dict]:
    """What the census can say without building anything (`UX-105`).

    Two different problems, deliberately separate findings: a sandbox
    with **no shell** (the `stage_*.sh` trap, which fails a build with a
    cryptic exec error) and a project staging **static executables**
    (which builds fine and produces an empty Plane 2 capture).
    """
    from .bst_native_build_tracer import census_project

    # UX-153: the same `element-path` the load probe reads. This
    # hardcoded `elements/` and SKIPped when it was absent - so on a
    # project with a declared layout the check silently stopped running,
    # with `element_path()` sitting two functions away.
    elements_dir = os.path.join(project_dir, element_path(project_dir))
    if not os.path.isdir(elements_dir):
        return [_check("census", SKIP,
                       f"{project_dir} has no {element_path(project_dir)}/ "
                       f"directory to census")]
    # UX-160: recursive, via the tracer's one implementation - a
    # nested layout is the normal shape of a real project.
    from .bst_native_build_tracer import discover_element_names
    elements = discover_element_names(project_dir)
    if not elements:
        return [_check("census", SKIP, "the project declares no elements")]

    try:
        census = census_project(project_dir, elements)
    except (OSError, ValueError) as error:
        return [_check("census", SKIP, f"the census could not run: {error}")]

    findings = []
    per_element = census.get("per_element") or {}
    executables = sum(
        (entry.get("dynamic_executables") or 0) + (entry.get("static_count") or 0)
        for entry in per_element.values()
    )
    if executables == 0:
        findings.append(_check(
            "staged-sources", WARN,
            "this project's own sources stage no executable at all - a sandbox "
            "with no shell cannot run install-commands",
            remedy="examples/stage_runtimes.sh (busybox) or "
                   "examples/stage_cpp_toolchain.sh (a real gcc/cmake sysroot), "
                   "depending on the project. Both are gitignored by design and "
                   "must be run once per checkout."))
    else:
        findings.append(_check("staged-sources", OK,
                               f"{executables} executable(s) staged by this "
                               f"project's own sources"))

    at_risk = census.get("elements_at_risk") or []
    if at_risk:
        findings.append(_check(
            "static-blind-spot", WARN,
            f"{len(at_risk)} element(s) stage a statically-linked executable, "
            f"which the LD_PRELOAD hook structurally cannot see",
            remedy="capture with `--trace-spine=auto` - it pays the ptrace cost "
                   "only for the elements the census says the hook is blind for "
                   "(UX-105/UX-113)",
            detail=at_risk[:6]))
    else:
        findings.append(_check(
            "static-blind-spot", OK,
            "nothing this project stages is statically linked, so the hook is "
            "not blind to any of it"))
    return findings


def run_checks(project_dir: Optional[str] = None) -> List[dict]:
    checks = [check_bst(), check_bwrap(), check_compiler()]
    checks.append(check_stale_casd())
    checks.extend(check_scratch(project_dir))
    project_name = None
    if project_dir:
        from .bst_cache_logs import project_name_from_dir
        project_name = project_name_from_dir(project_dir)
        checks.extend(check_project_loads(project_dir))
        checks.extend(check_staged_sources(project_dir))
    checks.append(check_plane3(project_name))
    return checks


_MARK = {OK: "ok  ", FAIL: "FAIL", WARN: "warn", SKIP: "skip"}


def format_text(checks: List[dict], project_dir: Optional[str]) -> str:
    lines = ["=" * 60, "bga doctor", "=" * 60]
    if project_dir:
        lines.append(f"Project: {project_dir}")
        lines.append("")
    for check in checks:
        lines.append(f"  [{_MARK[check['status']]}] {check['id']}: {check['summary']}")
        for line in check["detail"]:
            lines.append(f"           {line}")
        if check["remedy"] and check["status"] != OK:
            lines.append(f"           -> {check['remedy']}")
    failed = [c for c in checks if c["status"] == FAIL]
    lines.append("")
    if failed:
        lines.append(f"  {len(failed)} check(s) failed. Each line above carries the "
                     f"remedy that actually fixed it.")
    else:
        warned = [c for c in checks if c["status"] == WARN]
        lines.append(
            "  Everything a capture needs is here."
            + (f" {len(warned)} warning(s) worth reading first." if warned else ""))
    if not project_dir:
        lines.append("  Pass a project directory to also check that it loads, that "
                     "its plugins are installed, and what it stages.")
    lines.append("=" * 60)
    return "\n".join(lines)


# UX-149: a one-element project whose build runs one command. Small
# enough to build in seconds, real enough that every link in the chain
# has to work for it to produce a record.
_PROBE_PROJECT = "name: bga-capture-probe\nmin-version: 2.0\nelement-path: elements\n"
_PROBE_ELEMENT = """kind: manual
depends:
- filename: base.bst
  type: build
config:
  install-commands:
  - |
    echo bga-capture-probe > %{install-root}/probe.txt
"""
_PROBE_BASE = "kind: import\nsources:\n- kind: local\n  path: files/root\n"


def _stage_probe_project(root: str, runtime: Optional[str]) -> None:
    """A project whose one element runs one command inside a sandbox.

    The runtime is borrowed from whatever the caller could find - this
    check cannot build a sysroot, and a sandbox with no shell is the
    `stage_*.sh` trap `check_staged_sources` already names.
    """
    os.makedirs(os.path.join(root, "elements"), exist_ok=True)
    os.makedirs(os.path.join(root, "files"), exist_ok=True)
    with open(os.path.join(root, "project.conf"), "w") as handle:
        handle.write(_PROBE_PROJECT)
    with open(os.path.join(root, "elements", "base.bst"), "w") as handle:
        handle.write(_PROBE_BASE)
    with open(os.path.join(root, "elements", "probe.bst"), "w") as handle:
        handle.write(_PROBE_ELEMENT)
    shutil.copytree(runtime, os.path.join(root, "files", "root"), symlinks=True)


def _find_stageable_runtime() -> Optional[str]:
    """A staged sysroot this repository already has, or None.

    Deliberately not built here: `examples/stage_runtimes.sh` exists and
    a diagnostic that builds a sysroot is not a diagnostic.
    """
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ("01-resource-contention", "02-cache-invalidation"):
        candidate = os.path.join(repo, "examples", name, "files", "runtime")
        if os.path.isfile(os.path.join(candidate, "bin", "sh")):
            return candidate
    return None


def check_capture_chain(project_dir: Optional[str] = None) -> List[dict]:
    """UX-149: run the whole chain on a canned workload.

    `bga doctor` proves the *parts* - bst runs, bwrap builds a sandbox
    with bga's own arguments, a compiler exists - and `--diagnose`
    instruments the user's real build, which costs a real build and
    yields its evidence only after the failure. Nothing ran the actual
    chain: bst -> buildbox-run -> the PATH shim -> the rewritten argv ->
    the hook loading inside the sandbox.

    That is the probe a helper wants a remote user to run first, and
    what it classifies is exactly `UX-147`'s three causes of a zero plus
    "the shim ran and the hook recorded nothing".
    """
    if not shutil.which("bst"):
        return [_check("capture-chain", SKIP, "cannot run a build without bst")]
    runtime = _find_stageable_runtime()
    if runtime is None:
        return [_check(
            "capture-chain", SKIP,
            "no staged runtime to build a probe project from",
            remedy="run examples/stage_runtimes.sh - the probe needs a sandbox "
                   "with a shell in it, and this check will not build one")]

    from .bst_native_build_tracer import (
        count_build_tasks, load_and_summarize, read_capture_diagnostics,
        run_traced_build,
    )

    findings = []
    with tempfile.TemporaryDirectory(prefix="bga-capture-probe-") as tmp:
        project = os.path.join(tmp, "project")
        _stage_probe_project(project, runtime)
        raw = os.path.join(tmp, "trace.log")
        plane1 = os.path.join(tmp, "build.log")
        diagnostics = os.path.join(tmp, "diagnostics.jsonl")
        home = os.path.join(tmp, "home")
        os.makedirs(home)
        previous = dict(os.environ)
        os.environ.update(_isolated_home(home))
        try:
            # `--trace-spine=auto` because that is what `bga snapshot`
            # uses, and because the only runtimes this repository can
            # stage a probe from are static busybox - where the hook is
            # structurally blind and the spine is the whole answer.
            # Probing with the hook alone would report a correct blind
            # spot as a broken chain, every time.
            code = run_traced_build(
                project, ["bst", "--no-colors", "build", "probe.bst"], raw,
                wrapped_log_path=plane1, trace_opens=True,
                diagnostics_path=diagnostics, trace_spine="auto")
        except Exception as error:  # noqa: BLE001 - reported as the finding
            return [_check("capture-chain", FAIL,
                           f"the probe capture could not start: {error}",
                           remedy="the message above is the first broken link")]
        finally:
            os.environ.clear()
            os.environ.update(previous)

        # 1. the shim was executable at all - `run_traced_build` probes
        #    this itself (UX-147) and raises above if it fails.
        findings.append(_check("chain-shim-exec", OK,
                               "the bwrap shim is executable and answers its probe"))

        # 2. did bst launch a sandbox?
        tasks = count_build_tasks(plane1) or 0
        if code != 0 and tasks == 0:
            findings.append(_check(
                "chain-build", FAIL,
                f"the probe build failed (exit {code}) before running any command",
                remedy="the probe project is one `manual` element; a failure here "
                       "is BuildStream or the sandbox, not bga",
                detail=_tail(plane1)))
            return findings
        findings.append(_check("chain-build", OK,
                               f"bst ran {tasks} sandboxed task(s)"))

        # 3. did buildbox-run reach the shim?
        records = read_capture_diagnostics(diagnostics)
        if not records:
            findings.append(_check(
                "chain-shim-reached", FAIL,
                "the shim was executable and bst launched a sandbox, but the "
                "shim was never called",
                remedy="buildbox-run resolved `bwrap` without going through "
                       "$PATH, or `bst` reused a buildbox-casd started before "
                       "this capture (stop it and let bst restart it), or "
                       "something in the chain sanitises $PATH"))
            findings.append(_check("chain-records", SKIP,
                                   "unreachable: the shim never ran"))
            return findings
        findings.append(_check(
            "chain-shim-reached", OK,
            f"buildbox-run reached the shim {len(records)} time(s) through $PATH"))

        # 4. did anything record a process from inside the sandbox?
        report = load_and_summarize(raw, project_dir=project)
        processes = report.get("process_count", 0)
        if not processes:
            findings.append(_check(
                "chain-records", FAIL,
                "the shim rewrote the argv and nothing recorded a process",
                remedy="neither the LD_PRELOAD hook nor the ptrace spine saw "
                       "anything inside a sandbox that ran a command - the "
                       "injection reached bwrap and did not survive into the "
                       "sandbox. Send the diagnostics record."))
            return findings

        by_coverage = {}
        for record in report.get("processes") or []:
            key = record.get("coverage") or "unknown"
            by_coverage[key] = by_coverage.get(key, 0) + 1
        hook_seen = sum(count for key, count in by_coverage.items() if "hook" in key)
        summary = ", ".join(f"{count} {key}" for key, count in sorted(by_coverage.items()))
        if not hook_seen:
            # A real and expected reading, not a fault: the only runtimes
            # this repository can stage a probe from are static busybox,
            # which the hook structurally cannot see. The spine answering
            # instead is the blind spot being covered, working.
            findings.append(_check(
                "chain-records", WARN,
                f"{processes} process(es) recorded, none by the LD_PRELOAD hook "
                f"({summary})",
                remedy="the probe's runtime is statically linked, so only the "
                       "ptrace spine can see it - which it did. On a dynamic "
                       "project the hook is what carries opened paths"))
        else:
            findings.append(_check(
                "chain-records", OK,
                f"{processes} process(es) recorded from inside the sandbox "
                f"({summary})"))
    return findings


def _isolated_home(home: str) -> dict:
    """`HOME` pointed at a throwaway, and `PYTHONPATH` kept honest.

    The probe needs a cache of its own or a warm hit makes it report "0
    sandboxed tasks", which is the wrong answer to the question it asks.
    But `HOME` is *how* Python finds the per-user `site-packages`, so
    replacing it unimports a `pip install --user` BuildStream and `bst`
    dies with `ModuleNotFoundError: No module named 'jinja2'` before
    reading the project.

    That is `UX-84` exactly, which `tests/unit/_bst_env.py` was written
    for - and this hit it again, in production code, the first time it
    ran. Carried across explicitly rather than rediscovered a third time.
    """
    import site
    import sys

    env = {"HOME": home}
    try:
        user_site = site.getusersitepackages() if site.ENABLE_USER_SITE else None
    except Exception:  # pragma: no cover - site is not required to work
        user_site = None
    if user_site and user_site in sys.path and os.path.isdir(user_site):
        existing = os.environ.get("PYTHONPATH")
        env["PYTHONPATH"] = (f"{user_site}{os.pathsep}{existing}"
                             if existing else user_site)
    return env


def _tail(path: str, lines: int = 6) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read().splitlines()[-lines:]
    except OSError:
        return []


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "project_dir", nargs="?", default=None,
        help="A BuildStream project to check as well as the environment: that it "
             "loads, that every plugin kind it names is installed, and what its "
             "sources stage.",
    )
    parser.add_argument(
        "--capture", action="store_true",
        help="UX-149: also run the whole capture chain - bst, buildbox-run, the "
             "PATH shim, the rewritten argv, the hook inside the sandbox - on a "
             "canned one-element probe build, and report per link in chain "
             "order. Takes a few seconds and needs a staged runtime; this is the "
             "check to run when a capture fails on a build plain `bst` completes.",
    )
    parser.add_argument("-f", "--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)

    checks = run_checks(args.project_dir)
    if args.capture:
        checks += check_capture_chain(args.project_dir)
    if args.format == "json":
        print(json.dumps({"project_dir": args.project_dir, "checks": checks}, indent=2))
    else:
        print(format_text(checks, args.project_dir))
    return 1 if any(c["status"] == FAIL for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
