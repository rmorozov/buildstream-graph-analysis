"""UX-1132/UX-1284: examples/14-17 each hold the property they were built for,
and every surface that runs them names them.

`check_shape_property.py` is read on synthetic captures (no `bst` here);
the projects, the staging clone lists, the Graviton legs and the two
workflows are read as committed text.
"""

import importlib.util
import json
import pathlib
import re
import subprocess

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
EXAMPLES = REPO / "examples"
_SPEC = importlib.util.spec_from_file_location("check_shape_property", EXAMPLES / "check_shape_property.py")
check = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check)

#: example directory -> (Graviton leg, the check it runs on bst-examples)
SHAPES = {
    "14-two-giants": ("twogiants", "two-giants"),
    "15-wide-chain": ("widechain", "wide-chain"),
    "16-memory-bound-giant": ("memgiant", "memory-giant"),
    "17-late-peak-giant": ("latepeak", "late-peak"),
}
ARMS = EXAMPLES / "11-serial-giant" / "graviton_arms.sh"


def _write(tmp_path, widths, spans=(), rss=None):
    plane2, trace = tmp_path / "plane2.json", tmp_path / "trace.json"
    report = {"per_element_parallelism": [{"element": e, "peak_work_concurrency": w} for e, w in widths.items()]}
    if rss is not None:
        report["peak_memory"] = {"per_element": {e: {"peak_rss_kb": kb} for e, kb in rss.items()}}
        report["jobserver_pool"] = {"memory": {"psi_memory_withdraws": 0, "psi_memory_present": True}}
    plane2.write_text(json.dumps(report), encoding="utf-8")
    trace.write_text(
        json.dumps({"spans": [{"task_key": f"{e}|BUILD|BUILD|0", "ts_us": t, "dur_us": d} for e, t, d in spans]}),
        encoding="utf-8",
    )
    return str(plane2), str(trace)


class TestTheCheck:
    def test_two_wide_overlapping_giants_hold(self, tmp_path):
        plane2, trace = _write(
            tmp_path,
            {"giant-a.bst": 4, "giant-b.bst": 3},
            [("giant-a.bst", 0, 10_000_000), ("giant-b.bst", 1_000_000, 10_000_000)],
        )
        ok, line = check.two_giants(plane2, trace, "giant-a.bst", "giant-b.bst")
        assert ok, line

    def test_a_notparallel_second_giant_fails(self, tmp_path):
        """The Acceptance Test's mutation, as the capture would read it."""
        plane2, trace = _write(
            tmp_path,
            {"giant-a.bst": 4, "giant-b.bst": 1},
            [("giant-a.bst", 0, 10_000_000), ("giant-b.bst", 1_000_000, 10_000_000)],
        )
        ok, line = check.two_giants(plane2, trace, "giant-a.bst", "giant-b.bst")
        assert not ok, line

    def test_two_giants_one_after_the_other_fail(self, tmp_path):
        plane2, trace = _write(
            tmp_path,
            {"giant-a.bst": 4, "giant-b.bst": 4},
            [("giant-a.bst", 0, 10_000_000), ("giant-b.bst", 10_000_000, 10_000_000)],
        )
        ok, line = check.two_giants(plane2, trace, "giant-a.bst", "giant-b.bst")
        assert not ok, line

    def test_a_narrow_link_fails_the_chain(self, tmp_path):
        widths = {"wide-1.bst": 4, "wide-2.bst": 4, "wide-3.bst": 1, "wide-4.bst": 4}
        plane2, _ = _write(tmp_path, widths)
        assert not check.wide_chain(plane2, *widths)[0]
        widths["wide-3.bst"] = 2
        plane2, _ = _write(tmp_path, widths)
        assert check.wide_chain(plane2, *widths)[0]

    def test_the_memory_giant_is_floored_per_job(self, tmp_path):
        plane2, _ = _write(tmp_path, {"giant.bst": 4}, rss={"giant.bst": 549 * 1024})
        ok, line = check.memory_giant(plane2, "giant.bst", "200")
        assert ok and "peak_rss_per_job=549MB" in line, line
        plane2, _ = _write(tmp_path, {"giant.bst": 4}, rss={"giant.bst": 83 * 1024})
        assert not check.memory_giant(plane2, "giant.bst", "200")[0]

    @staticmethod
    def _log(tmp_path, link_mb):
        """Hook END lines: three cc1 at <= 150 MB, then a make, then the link's lto1."""
        rows = [(1.0, 140, "/nix/store/x-gcc/libexec/gcc/cc1"), (2.0, 150, "cc1"), (3.0, 120, "cc1")]
        rows += [(0.5, 900, "/usr/bin/other"), (4.0, link_mb, "/nix/store/x-gcc/libexec/gcc/lto1"), (5.0, 9, "make")]
        log = tmp_path / "trace.log"
        log.write_text(
            "".join(
                f"END pid={n} ppid=1 ts={ts} element=giant.bst inv=none utime=1.0 maxrss_kb={mb * 1024} cmd={b} -O0\n"
                for n, (ts, mb, b) in enumerate(rows)
            )
            + "END pid=99 ppid=1 ts=6.0 element=other.bst inv=none maxrss_kb=99999999 cmd=lto1\n",
            encoding="utf-8",
        )
        return str(log)

    def test_a_link_at_four_compiles_holds_the_late_peak(self, tmp_path):
        ok, line = check.late_peak(self._log(tmp_path, 600), "giant.bst", "4")
        assert ok and "cc1_peak=150MB late_peak=600MB(lto1) ratio=4.0" in line, line

    def test_a_link_no_bigger_than_a_compile_fails_it(self, tmp_path):
        """The shape's mutation: a late step at 1x, and a peak before the last cc1 does not count."""
        ok, line = check.late_peak(self._log(tmp_path, 150), "giant.bst", "2")
        assert not ok and "ratio=1.0" in line, line


def _element(shape, name):
    return yaml.safe_load((EXAMPLES / shape / "elements" / name).read_text(encoding="utf-8"))


def _deps(element):
    return {d["filename"] if isinstance(d, dict) else d for d in element.get("depends") or []}


class TestTheProjects:
    @pytest.mark.parametrize("name", ["giant-a.bst", "giant-b.bst"])
    def test_both_giants_are_parallel_and_ready_at_once(self, name):
        element = _element("14-two-giants", name)
        assert not (element.get("variables") or {}).get("notparallel"), name
        assert _deps(element) == {"toolchain.bst"}, _deps(element)

    def test_the_chain_is_a_chain_of_parallel_links(self):
        for n in range(1, 5):
            element = _element("15-wide-chain", f"wide-{n}.bst")
            assert not (element.get("variables") or {}).get("notparallel")
            assert _deps(element) == {"toolchain.bst"} | ({f"wide-{n - 1}.bst"} if n > 1 else set())

    def test_the_memory_giant_is_heavier_than_11s(self):
        conf = yaml.safe_load((EXAMPLES / "16-memory-bound-giant" / "project.conf").read_text(encoding="utf-8"))
        rungs = [int(v) for v in conf["options"]["mem_lines"]["values"]]
        assert min(rungs) >= 4 * 9800, rungs

    def test_the_late_peak_giant_links_its_lto_units_last(self):
        conf = yaml.safe_load((EXAMPLES / "17-late-peak-giant" / "project.conf").read_text(encoding="utf-8"))
        assert conf["options"]["late_k"]["values"] == ["2", "4"]
        script = "\n".join(_element("17-late-peak-giant", "giant.bst")["config"]["configure-commands"])
        for needle in ("-flto-partition=one", "add_dependencies(late giant)", "$((%{late_k} * %{unit_lines}))"):
            assert needle in script, needle

    def test_the_latepeak_leg_runs_the_measured_point(self):
        """unit_lines 20000, late_k 4: the one point the Outcome measured (4.43x)."""
        block = ARMS.read_text(encoding="utf-8").split('if [ "$MODE" = latepeak ]; then', 1)[1].split("\nfi\n", 1)[0]
        assert 'OPTS="--option unit_lines 20000 --option late_k 4"' in block, block


class TestTheWiring:
    @pytest.mark.parametrize("shape", SHAPES)
    def test_staging_clones_the_toolchain_and_generator_in(self, shape):
        text = (EXAMPLES / "stage_cpp_toolchain.sh").read_text(encoding="utf-8")
        assert f'"$HERE/{shape}/files/toolchain"' in text
        assert f'"$HERE/{shape}/files/gen/cmake"' in text

    @pytest.mark.parametrize("shape", SHAPES)
    def test_the_index_names_it(self, shape):
        assert f"\n## {shape}\n" in (EXAMPLES / "README.md").read_text(encoding="utf-8")

    @pytest.mark.parametrize("shape", SHAPES)
    def test_the_arms_script_has_its_leg(self, shape):
        leg = SHAPES[shape][0]
        text = ARMS.read_text(encoding="utf-8")
        assert re.search(rf'"\$MODE" [!=]+ {leg} \]\s*(\|\||; then)\s*PROJ=\$\(cd "\$PROJ/\.\./{shape}"', text), leg
        block = text[text.index("for i in 1 2 3; do") :]
        assert re.search(rf"^\s*[a-z0-9|]*\b{leg}\b[a-z0-9|]*\)", block, re.M), leg

    def test_the_arms_script_parses(self):
        assert subprocess.run(["sh", "-n", str(ARMS)], capture_output=True).returncode == 0

    def test_the_probe_runs_every_leg_and_keeps_the_captures(self):
        probe = yaml.safe_load((REPO / ".github/workflows/codspeed-probe.yml").read_text(encoding="utf-8"))
        job = probe["jobs"]["probe"]
        legs = job["strategy"]["matrix"]["leg"]  # a dispatch may pick legs; the default runs every shape
        default = json.loads(re.search(r"\|\| '(\[.*\])'", legs).group(1)) if isinstance(legs, str) else legs
        assert {leg for leg, _ in SHAPES.values()} <= set(default)
        uploads = [s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/upload-artifact")]
        assert uploads and uploads[0].get("if") == "always()", uploads
        assert "/arms" in uploads[0]["with"]["path"], uploads[0]

    @pytest.mark.parametrize("shape", SHAPES)
    def test_bst_examples_builds_and_checks_it(self, shape):
        ci = yaml.safe_load((REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
        steps = ci["jobs"]["bst-examples"]["steps"]
        runs = [s for s in steps if f"PROJ=examples/{shape}\n" in str(s.get("run", ""))]
        assert len(runs) == 1, shape
        assert f"check_shape_property.py {SHAPES[shape][1]} " in runs[0]["run"]
        notices = [s for s in steps if "::notice title=UX-1132" in str(s.get("run", ""))]
        assert notices and notices[0].get("if") == "always()" and shape in notices[0]["run"]
        assert steps.index(notices[0]) > steps.index(runs[0])
