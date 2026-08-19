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
    return _check("c-compiler", OK, f"C compiler at {cc}")


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

    Read straight out of `project.conf`, for the same reason
    `project_name_from_dir` is: this has to work on a project whose
    plugins are *not* installed, which is one of the failures this check
    exists to name.
    """
    conf = os.path.join(project_dir, "project.conf")
    try:
        with open(conf, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if line.startswith("element-path:"):
                    return line.split(":", 1)[1].strip() or "elements"
    except OSError:
        pass
    return "elements"


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

    elements_dir = os.path.join(project_dir, "elements")
    if not os.path.isdir(elements_dir):
        return [_check("census", SKIP, f"{project_dir} has no elements/ directory")]
    elements = sorted(n for n in os.listdir(elements_dir) if n.endswith(".bst"))
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
    parser.add_argument("-f", "--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)

    checks = run_checks(args.project_dir)
    if args.format == "json":
        print(json.dumps({"project_dir": args.project_dir, "checks": checks}, indent=2))
    else:
        print(format_text(checks, args.project_dir))
    return 1 if any(c["status"] == FAIL for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
