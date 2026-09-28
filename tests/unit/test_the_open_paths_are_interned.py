"""UX-1076: `parse_open_lines` kept a fresh `str` per opened path, though
the same sysroot headers repeat across every element. On a real file
handle each repeated line is a distinct object, so the per-element sets
held one allocation per occurrence rather than per distinct path.

Measured against a *live* subprocess run rather than a fixed MB number:
`sys.intern` patched to identity reproduces the pre-fix shape exactly,
on this machine, in the same run - the 60% bound is the audit's own
ratio (261 / 552 MB, `docs/audits/perf-snapshot-view-2026-09-28.md`),
not a number carried over from a different container.
"""
import random
import subprocess
import sys
import textwrap

ELEMENTS, PROCESSES_PER_ELEMENT, PATHS_PER_PROCESS = 1202, 160, 50

_MEASURE = textwrap.dedent("""
    import sys
    if sys.argv[2] == "no-intern":
        sys.intern = lambda s: s
    sys.path.insert(0, sys.argv[3])
    from tools.bst_native_build_tracer import parse_open_lines
    with open(sys.argv[1]) as handle:
        report = parse_open_lines(handle)
    # VmHWM, not ru_maxrss: Linux carries ru_maxrss across exec, so a
    # child of a large xdist worker reads the worker's peak.
    with open('/proc/self/status') as status:
        rss = next(int(line.split()[1]) for line in status
                   if line.startswith('VmHWM:'))
    total = sum(len(v["paths"]) for v in report.values())
    print(rss, total, sorted(report), sep="|")
""")


def _write_scaled_log(path):
    """The audit's `genlog.py` shape: 1,202 elements x 160 processes x
    50 paths, drawn from a shared 3,000-header sysroot - the same scale
    that measured 552 MB uninterned, 261 MB interned."""
    rnd = random.Random(1)
    sysroot = [f"/usr/include/c++/13/bits/h{i:04d}.h" for i in range(3000)]
    with open(path, "w") as out:
        pid = 100000
        for e in range(ELEMENTS):
            element = f"e{e}.bst"
            for k in range(PROCESSES_PER_ELEMENT - 1):
                pid += 1
                paths = (rnd.sample(sysroot, PATHS_PER_PROCESS - 2)
                         + [f"/buildstream/elem{e}/u{k}.c",
                            f"/buildstream/elem{e}/u{k}.o"])
                out.write(f"OPENS pid={pid} element={element} "
                          f"unique={len(paths)} dropped=0\n")
                out.write("\n".join(paths) + "\n")


def _measure(log_path, repo_root, mode):
    out = subprocess.run(
        [sys.executable, "-c", _MEASURE, str(log_path), mode, str(repo_root)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    rss_kb, total, elements = out.split("|")
    return int(rss_kb), int(total), elements


def test_the_opens_pass_peaks_under_60_percent_of_the_uninterned_rss(tmp_path):
    log_path = tmp_path / "scaled.log"
    _write_scaled_log(log_path)
    repo_root = str(__file__).rsplit("/tests/", 1)[0]

    interned_rss, interned_total, interned_elements = _measure(
        log_path, repo_root, "intern")
    baseline_rss, baseline_total, baseline_elements = _measure(
        log_path, repo_root, "no-intern")

    # The report itself must be byte-identical either way.
    assert interned_total == baseline_total
    assert interned_elements == baseline_elements

    assert interned_rss < 0.6 * baseline_rss, (
        f"interned peak {interned_rss} KB is not under 60% of "
        f"uninterned peak {baseline_rss} KB")
