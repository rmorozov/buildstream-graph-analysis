"""UX-186: what machine measured this, and whether two runs share one.

Field feedback: *"generally we can compare builds only built on current
host — maybe we need some kind of sbom capture with information to
enable comparison of runs from different build hosts, to compare
comparable."*

The tool's own history agrees twice over. `UX-92` measured a **33%**
spread across five captures of one unchanged commit on nominally
identical CI runners; and before this module `run-context.json` recorded
`host_cpu_count` and `host_memory_mb` and nothing else - two numbers
that call a laptop and a build runner with the same core count the same
machine. `bga compare` performed no host check of any kind, so a
baseline from machine A gated a candidate from machine B with no
caveat, and `UX-78`'s refusal grammar - written for exactly this class
of not-a-measurement - never fired.

**Scope.** This manifests the *measuring machine*, not the build's
contents: an SBOM of the artifacts is a different document with a
different purpose. It is also deliberately not a *normalisation* model.
Durations are not scaled across hosts here, and should not be: `UX-129`
is the standing lesson that a model dressed as a measurement is worse
than a refusal. Refusal and honesty first.

Everything here is offline and cheap - `/proc/cpuinfo`, `/proc/meminfo`,
`os.uname`, `/etc/os-release` - except the toolchain versions, which are
the same short subprocess calls `UX-151`'s capture fingerprint already
makes, each with a timeout and each degrading to `None`.
"""
import os
import shutil
import subprocess
from typing import Dict, List, Optional

SCHEMA = "host/v1"

# The fields a difference in which moves durations, and therefore the
# fields a comparison is classified on. Kernel release, distro and
# toolchain versions are recorded because a human reading a refusal
# wants them, but they do not by themselves make two runs incomparable:
# a point release of `bwrap` is not the reason a build took 12% longer,
# and refusing on it would make the check noise that gets switched off.
COMPARED_FIELDS = ("cpu_model", "cpu_count", "memory_mb")

_FIELD_LABELS = {
    "cpu_model": "CPU model",
    "cpu_count": "CPU count",
    "memory_mb": "memory",
}


def _cpu_model() -> Optional[str]:
    """The CPU's own name for itself.

    `/proc/cpuinfo` rather than `platform.processor()`, which on Linux
    returns the architecture (`x86_64`) - true of every x86 machine ever
    built, and therefore useless for telling two of them apart.
    """
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith(("model name", "Model")):
                    _label, _colon, value = line.partition(":")
                    value = value.strip()
                    if value:
                        return value
    except OSError:
        pass
    return None


def _distro_id() -> Optional[str]:
    """`id version` from `/etc/os-release`, e.g. `debian 12`."""
    fields = {}
    try:
        with open("/etc/os-release", "r", encoding="utf-8") as handle:
            for line in handle:
                key, _sep, value = line.partition("=")
                fields[key.strip()] = value.strip().strip('"')
    except OSError:
        return None
    name = fields.get("ID")
    if not name:
        return None
    version = fields.get("VERSION_ID")
    return f"{name} {version}" if version else name


def _version_line(argv: List[str]) -> Optional[str]:
    """The first line of a `--version`, or None.

    Same shape as `UX-151`'s fingerprint probe, including reading
    stderr: several of these tools print their version there.
    """
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    text = (result.stdout or result.stderr or "").strip()
    return text.splitlines()[0] if text else None


def _toolchain() -> Dict[str, Optional[str]]:
    """The programs whose version changes what a build does.

    `cc` is included because the compiler is usually the largest single
    consumer of a build's wall clock, and a compiler upgrade is a
    perfectly ordinary reason for a 10% shift that has nothing to do
    with the change under test.
    """
    probes = {
        "bst": ["bst", "--version"],
        "bwrap": ["bwrap", "--version"],
        "buildbox-run": ["buildbox-run", "--version"],
        "cc": ["cc", "--version"],
    }
    found = {}
    for name, argv in probes.items():
        found[name] = _version_line(argv) if shutil.which(argv[0]) else None
    return found


def collect(with_toolchain: bool = True) -> dict:
    """The manifest for the machine this is running on.

    `with_toolchain=False` skips the four subprocess calls - for callers
    that build a manifest in a tight loop, and for tests that would
    otherwise depend on what happens to be installed.

    Every field degrades to `None` rather than to a guess. A manifest of
    `None`s is still worth writing: it says a capture from this version
    of `bga` looked, which is different from a capture too old to have
    looked at all.
    """
    # `UX-325`: see `store_aggregate.read` - the same class, found by
    # sweeping for it rather than by a second stranger.
    from .tools_dispatch import _import_tool

    _common = _import_tool("tools._run_context_common")
    host_cpu_count = _common.host_cpu_count
    host_memory_mb = _common.host_memory_mb

    uname = os.uname() if hasattr(os, "uname") else None
    manifest = {
        "schema": SCHEMA,
        "cpu_model": _cpu_model(),
        "cpu_count": host_cpu_count(),
        "memory_mb": host_memory_mb(),
        "kernel_release": uname.release if uname else None,
        "distro_id": _distro_id(),
    }
    if with_toolchain:
        manifest["toolchain"] = _toolchain()
    return manifest


def differing_fields(baseline: Optional[dict],
                     candidate: Optional[dict]) -> List[str]:
    """Which of `COMPARED_FIELDS` the two manifests disagree on.

    A field missing from *both* is not a difference: two captures from a
    machine with no readable `/proc/cpuinfo` are as comparable as they
    ever were. A field present in one and absent in the other is a
    difference, because the absence is not evidence of a match.
    """
    if not baseline or not candidate:
        return []
    return [field for field in COMPARED_FIELDS
            if not (baseline.get(field) is None and candidate.get(field) is None)
            and baseline.get(field) != candidate.get(field)]


def classify(baseline: Optional[dict], candidate: Optional[dict]) -> dict:
    """`{"status": same|different|unknown, "differing": [...], ...}`.

    `unknown` is for a run captured before this manifest existed. Those
    keep comparing exactly as they did - a tool that refused every
    capture older than itself would be telling users to throw away the
    baselines they came with.
    """
    if not baseline or not candidate:
        which = []
        if not baseline:
            which.append("baseline")
        if not candidate:
            which.append("candidate")
        return {"status": "unknown", "differing": [], "missing": which}
    differing = differing_fields(baseline, candidate)
    return {
        "status": "different" if differing else "same",
        "differing": differing,
        "missing": [],
    }


def describe(classification: dict,
             baseline: Optional[dict],
             candidate: Optional[dict]) -> Optional[str]:
    """One sentence for the report, or None when the hosts match.

    Names the fields *and their values*: "different host" is a fact a
    reader can do nothing with, and "CPU model: Xeon E5-2680 vs Ryzen
    9 7950X" is the same fact plus the reason to believe it.
    """
    status = classification.get("status")
    if status == "same":
        return None
    if status == "unknown":
        missing = " and ".join(classification.get("missing") or ["one run"])
        return (f"Host unknown: the {missing} carries no host manifest (captured "
                f"before `UX-186`), so this comparison cannot tell whether both "
                f"runs were measured on the same machine.")
    parts = []
    for field in classification.get("differing") or []:
        label = _FIELD_LABELS.get(field, field)
        parts.append(f"{label}: {(baseline or {}).get(field)} vs "
                     f"{(candidate or {}).get(field)}")
    return ("Cross-host comparison: these runs were measured on different "
            "machines (" + "; ".join(parts) + "). Run-to-run noise on one "
            "machine already reaches 33% (`UX-92`); across machines the "
            "difference between the two runs is not evidence about the change.")


def homogeneous(manifests: List[Optional[dict]]) -> bool:
    """Whether every manifest in a baseline set describes one machine.

    `bga baseline` warns rather than refuses: a band assembled across
    machines is a real thing somebody may want to look at, and it is not
    the thing the band's arithmetic claims to be.
    """
    known = [manifest for manifest in manifests if manifest]
    if len(known) < 2:
        return True
    first = known[0]
    return all(not differing_fields(first, other) for other in known[1:])
