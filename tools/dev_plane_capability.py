#!/usr/bin/env python3
"""UX-470: what a plane can observe, against what it records.

`UX-466`'s census answers "what the planes *do* capture and the trace
drops". This one answers the half it declared and declined to guess at:
**what the planes could capture and do not**. `UX-379` is why the gap
is worth an instrument - the hook was already reading `rusage` fields
it did not record, and a round found that by reading the source.

How it avoids being a text scan
-------------------------------
The Required Fix expects a scan and warns about it, because a text
scan cannot tell code from prose (fixing guide §5). Almost none of
this is one, because both sides can be *run*:

- **What the hook can observe** is the `struct rusage` this kernel
  fills, read through CPython's `resource` module - the same struct
  `hook.c` calls `getrusage` into, not a list of field names copied
  out of a header.
- **What the hook records** comes from compiling `hook.c` and running
  a real process under it. The keys are read off the record it writes.
- **Which symbols it interposes** is `nm -D` over that compiled
  object - the dynamic symbol table, not a grep for `int open(`.
- **What the spine can observe** is the `/proc/<pid>` fields this
  kernel exposes for a live process, read here.
- **What the spine records** comes from compiling `spine.c` and
  tracing a real process with it.

The one declaration this module holds is the **name map**: that the
record's `maxrss_kb` is `ru_maxrss` and its `inblock` is `ru_inblock`.
That is a mapping between two vocabularies and no measurement can
supply it - so it is written down here, and every entry of it is
checked against a real record (`_check_map`), which fails loudly if a
key it names is not one the hook actually writes.

The verdict a field can get
---------------------------
- **recorded** - the record carries it.
- **gap** - this kernel maintains the field (the probe moved it) and
  no record carries it. The output a round is meant to act on.
- **unmaintained** - the probe below *exercised* the field and this
  kernel left it at zero. Not a gap: Linux documents several `rusage`
  fields as unmaintained, and a record for them would carry zeros.
- **unexercised** - the probe does not try to move it, so this cannot
  judge it. `ru_nswap` is the case: forcing a host to swap is not
  something an instrument should do.

Usage
-----
    python3 tools/dev_plane_capability.py
    python3 tools/dev_plane_capability.py --format json
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.bst_native_build_tracer import (            # noqa: E402
    compile_hook, compile_spine)

#: The record key each `rusage` field is written under, where one is.
#: The one declaration in this module - a mapping between the kernel's
#: vocabulary and the record's, which nothing can measure. `None` means
#: "no key claims to carry it", which is what the census is looking for.
#:
#: `_check_map` holds every non-`None` value here against the keys a
#: real record carries, so a rename on either side reddens rather than
#: turning a recorded field into a reported gap.
RUSAGE_KEYS = {
    "ru_utime": "utime",
    "ru_stime": "stime",
    "ru_maxrss": "maxrss_kb",
    "ru_inblock": "inblock",
    "ru_oublock": "oublock",
    "ru_majflt": "majflt",
    "ru_minflt": "minflt",
    "ru_nvcsw": "nvcsw",
    "ru_nivcsw": "nivcsw",
    "ru_ixrss": None,
    "ru_idrss": None,
    "ru_isrss": None,
    "ru_nswap": None,
    "ru_msgsnd": None,
    "ru_msgrcv": None,
    "ru_nsignals": None,
}

#: Fields the probe below makes no attempt to move, and why. Reported
#: `unexercised` rather than `unmaintained`: this instrument may not
#: say a kernel does not maintain a counter it never asked it to.
NOT_EXERCISED = {
    "ru_nswap": "moving it means forcing the host to swap, which an "
                "instrument must not do to the machine it runs on",
}

#: A child that would move every `rusage` field this kernel maintains:
#: CPU, resident memory it touches, a `O_DIRECT` read that reaches the
#: device, an fsync'd write, delivered signals, socket messages and
#: yields. Run as a real process, and its own `getrusage` is printed -
#: so "the kernel left this at zero after the thing that should move
#: it" is a measurement rather than an assumption.
RUSAGE_PROBE = '''
import mmap, os, resource, signal, socket, sys

path = sys.argv[1]
buf = bytearray(64 * 1024 * 1024)
for i in range(0, len(buf), 4096):
    buf[i] = 1
with open(path, "wb") as fh:
    fh.write(os.urandom(8 << 20))
    fh.flush()
    os.fsync(fh.fileno())
fd = os.open(path, os.O_RDONLY | os.O_DIRECT)
try:
    os.preadv(fd, [mmap.mmap(-1, 1 << 20)], 0)
finally:
    os.close(fd)
signal.signal(signal.SIGUSR1, lambda *a: None)
for _ in range(200):
    os.kill(os.getpid(), signal.SIGUSR1)
left, right = socket.socketpair()
for _ in range(200):
    left.send(b"x")
    right.recv(1)
for _ in range(200):
    os.sched_yield()

used = resource.getrusage(resource.RUSAGE_SELF)
print(json.dumps({n: getattr(used, n)
                  for n in dir(used) if n.startswith("ru_")})
      if (json := __import__("json")) else "")
'''

#: What `/proc/<pid>` offers about one process, and the record key the
#: spine writes it under. Same shape and same rule as `RUSAGE_KEYS`:
#: the *presence* of each is measured below, the mapping is declared.
PROC_KEYS = {
    ("stat", "utime"): "utime",
    ("stat", "stime"): "stime",
    ("status", "VmHWM"): "maxrss_kb",
    ("stat", "minflt"): None,
    ("stat", "majflt"): None,
    ("io", "read_bytes"): None,
    ("io", "write_bytes"): None,
    ("io", "rchar"): None,
    ("io", "wchar"): None,
}

#: `/proc/<pid>/stat`'s fields are positional, so a name needs an
#: index. One-based, as `proc(5)` numbers them, and read for a live
#: process below rather than trusted.
STAT_FIELDS = {"minflt": 10, "majflt": 12, "utime": 14, "stime": 15}


#: A record line begins with its kind in capitals. The `OPENS` record
#: is followed by the paths it recorded, one per line, so "the first
#: token of every line" would report a path as a record kind - which is
#: how the first run of this module described 35 `.pyc` files as Plane
#: 2 record kinds.
_KIND = re.compile(r"^([A-Z]+) ")


def _kinds(lines):
    return {found.group(1): _record_keys(line)
            for line in lines for found in [_KIND.match(line)] if found}


def _record_keys(line):
    """The `key=` names one record line carries.

    `cmd=` is last and its value is a whole command line, so the scan
    stops there - anything after it is argv, not keys.
    """
    head = line.split(" cmd=", 1)[0]
    return set(re.findall(r"\b([a-z_]+)=", head))


def hook_records(build_dir):
    """A real record from a real process, under the compiled hook."""
    hook = compile_hook(build_dir)
    log = os.path.join(build_dir, "plane2.log")
    env = dict(os.environ, LD_PRELOAD=hook, BST_TRACE_LOG=log,
               BST_TRACE_ELEMENT="probe.bst",
               BST_TRACE_INVOCATION="inv-probe", BST_TRACE_OPENS="1")
    subprocess.run([sys.executable, "-c", "print(1)"], env=env,
                   capture_output=True, timeout=120)
    lines = pathlib.Path(log).read_text(encoding="utf-8").splitlines()
    return hook, _kinds(lines)


def spine_records(build_dir):
    """The same, for the ptrace spine.

    `(None, {})` where ptrace is unavailable - a container without
    `CAP_SYS_PTRACE` cannot run this half, and it says so rather than
    reporting every spine field as a gap.
    """
    spine = compile_spine(build_dir)
    log = os.path.join(build_dir, "plane3.log")
    env = dict(os.environ, BST_TRACE_LOG=log, BST_TRACE_ELEMENT="probe.bst",
               BST_TRACE_INVOCATION="inv-probe")
    done = subprocess.run([spine, "--", sys.executable, "-c", "print(1)"],
                          env=env, capture_output=True, text=True, timeout=120)
    if done.returncode != 0 or not os.path.exists(log):
        return None, {}
    lines = pathlib.Path(log).read_text(encoding="utf-8").splitlines()
    return spine, _kinds(lines)


def interposed(hook_so):
    """The symbols the compiled hook defines - what it interposes.

    The dynamic symbol table of the object that is actually preloaded,
    so a function added to `hook.c` and never exported does not count
    and one exported without a comment does.
    """
    if shutil.which("nm") is None:
        return None
    done = subprocess.run(["nm", "-D", "--defined-only", hook_so],
                          capture_output=True, text=True, timeout=60)
    if done.returncode != 0:
        return None
    return sorted(line.split()[-1] for line in done.stdout.splitlines()
                  if line.split()[1:2] in (["T"], ["W"]))


def rusage_probe(build_dir):
    """What this kernel actually fills in, measured in a real child."""
    script = os.path.join(build_dir, "rusage_probe.py")
    pathlib.Path(script).write_text(RUSAGE_PROBE, encoding="utf-8")
    done = subprocess.run(
        [sys.executable, script, os.path.join(build_dir, "probe.bin")],
        capture_output=True, text=True, timeout=300)
    if done.returncode != 0:
        raise SystemExit(f"the rusage probe failed:\n{done.stderr}")
    return json.loads(done.stdout.strip().splitlines()[-1])


def _check_map(name, mapping, carried):
    """Every key the map claims is a key a real record carries.

    Without this the map is the weak point: a renamed record key turns
    a recorded field into a reported gap, and the census would file a
    row about a field that has been recorded all along.
    """
    claimed = {key for key in mapping.values() if key is not None}
    missing = sorted(claimed - carried)
    if missing:
        raise SystemExit(
            f"{name}: the name map claims {missing} are record keys and no "
            f"real record carries them. Either a key was renamed or the map "
            f"is wrong - fix it before reading anything below")


def census(build_dir):
    """Both planes, as data."""
    hook_so, hook_kinds = hook_records(build_dir)
    carried = set().union(*hook_kinds.values()) if hook_kinds else set()
    _check_map("plane 2", RUSAGE_KEYS, carried)
    filled = rusage_probe(build_dir)

    plane2 = []
    for field in sorted(RUSAGE_KEYS):
        key = RUSAGE_KEYS[field]
        if key is not None:
            plane2.append((field, "recorded", key))
        elif field in NOT_EXERCISED:
            plane2.append((field, "unexercised", NOT_EXERCISED[field]))
        elif float(filled.get(field) or 0) > 0:
            plane2.append((field, "gap",
                           f"this kernel filled it ({filled[field]}) and no "
                           f"record key carries it"))
        else:
            plane2.append((field, "unmaintained",
                           "the probe exercised it and this kernel left it "
                           "at zero"))

    spine_bin, spine_kinds = spine_records(build_dir)
    spine_carried = (set().union(*spine_kinds.values())
                     if spine_kinds else set())
    plane3, offers = [], proc_offers()
    if spine_bin is None:
        plane3 = None
    else:
        _check_map("plane 3", PROC_KEYS, spine_carried)
        for where in sorted(PROC_KEYS):
            key = PROC_KEYS[where]
            name = f"/proc/<pid>/{where[0]}:{where[1]}"
            if key is not None:
                plane3.append((name, "recorded", key))
            elif offers.get(where) is not None:
                plane3.append((name, "gap",
                               f"exposed here (read as {offers[where]}) and "
                               f"no record key carries it"))
            else:
                plane3.append((name, "not offered",
                               "this kernel does not expose it for a live "
                               "process"))
    return {"hook": hook_so, "kinds": hook_kinds, "interposed": interposed(hook_so),
            "plane2": plane2, "spine_kinds": spine_kinds, "plane3": plane3}


def proc_offers():
    """Which `/proc/<pid>` quantities this kernel exposes, read here.

    Read for a live process - this one - so "the kernel offers it" is a
    fact about the machine the census ran on rather than about
    `proc(5)`.

    **Presence, not magnitude.** A `/proc` line exists only if the
    kernel exports it, so parsing one is the whole question; the value
    is printed beside it as evidence of the read and means nothing on
    its own. That is the opposite of `rusage`, where every field of the
    struct exists whether the kernel fills it or not and only a probe
    that moves it can tell - which is why the two halves of this census
    judge differently and say so.
    """
    offers = {}
    stat = pathlib.Path("/proc/self/stat").read_text(encoding="utf-8")
    fields = stat[stat.rfind(")") + 2:].split()
    for name, index in STAT_FIELDS.items():
        # Field 3 (state) is the first after the comm, so field N is at
        # offset N - 3 in what `fields` holds.
        offers[("stat", name)] = fields[index - 3] if index - 3 < len(fields) else None
    status = pathlib.Path("/proc/self/status").read_text(encoding="utf-8")
    found = re.search(r"^VmHWM:\s+(\d+)", status, re.M)
    offers[("status", "VmHWM")] = found.group(1) if found else None
    try:
        io = pathlib.Path("/proc/self/io").read_text(encoding="utf-8")
    except OSError:
        io = ""
    for name in ("read_bytes", "write_bytes", "rchar", "wchar"):
        found = re.search(rf"^{name}:\s+(\d+)", io, re.M)
        offers[("io", name)] = found.group(1) if found else None
    return offers


def render(report):
    lines = ["Plane 2 - the LD_PRELOAD hook", ""]
    lines.append(f"    interposes   {', '.join(report['interposed'] or ['?'])}")
    lines.append(f"    records      {', '.join(sorted(report['kinds']))}")
    lines.append("")
    for field, verdict, detail in report["plane2"]:
        lines.append(f"    {verdict:13} {field:12} {detail}")
    lines.append("")
    lines.append("Plane 3 - the ptrace spine")
    lines.append("")
    if report["plane3"] is None:
        lines.append("    unassessable  the spine could not trace a process "
                     "here (no CAP_SYS_PTRACE?)")
    else:
        lines.append(f"    records      {', '.join(sorted(report['spine_kinds']))}")
        lines.append("")
        for name, verdict, detail in report["plane3"]:
            lines.append(f"    {verdict:13} {name:28} {detail}")
    gaps = [f for f, v, _d in report["plane2"] if v == "gap"]
    gaps += [n for n, v, _d in (report["plane3"] or []) if v == "gap"]
    lines.append("")
    lines.append(f"{len(gaps)} gap(s): {', '.join(gaps) if gaps else 'none'}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory() as build:
        report = census(build)
    if args.format == "json":
        print(json.dumps({k: v for k, v in report.items() if k != "hook"},
                         indent=2, default=sorted))
    else:
        print(render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
