"""UX-1070: the policy names what the *current* producers write.

`disclosure.gaps` refused a real `plane2.json` from a compiled hook and
spine on a `dd` workload with 9 gaps (measured, `UX-1070`'s Outcome) -
the policy was shaped by `tests/fixtures/`, which predate several
producer fields. This exercises the real producers, not a fixture.
"""

import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import disclosure, suspend
from tools import _run_context_common as run_context_common
from tools.bst_extract_run import _read_bga_jobserver_env
from tools.bst_native_build_tracer import compile_hook, compile_spine, load_and_summarize

needs_cc = pytest.mark.skipif(
    shutil.which("cc") is None and shutil.which("gcc") is None, reason="no C compiler on PATH"
)

WORKLOAD = "dd if=/dev/urandom of={path} bs=1M count=8 2>/dev/null; sync"


def _plane2_report(tmp_path):
    """A real `plane2.json` shape: both planes, a project with a
    binary an element names and never runs (`commands_not_observed`)."""
    build = tmp_path / "build"
    build.mkdir()
    spine = compile_spine(str(build))
    hook = compile_hook(str(build))
    project = tmp_path / "project"
    (project / "elements").mkdir(parents=True)
    (project / "elements" / "probe.bst").write_text(
        "kind: manual\nconfig:\n  build-commands:\n    - never-run-binary --flag\n"
    )
    log = tmp_path / "plane2.log"
    env = dict(
        os.environ, BST_TRACE_LOG=str(log), BST_TRACE_ELEMENT="probe.bst", BST_TRACE_INVOCATION="inv", LD_PRELOAD=hook
    )
    done = subprocess.run(
        [spine, "--", "sh", "-c", WORKLOAD.format(path=tmp_path / "probe.bin")],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert done.returncode == 0, done.stderr[-400:]
    return load_and_summarize(str(log), project_dir=str(project))


@needs_cc
def test_a_real_plane2_report_has_no_disclosure_gaps(tmp_path):
    report = _plane2_report(tmp_path)
    # The fields this task exists for really are on the report.
    assert report["schema"]
    assert report["resource_pressure"]["available"]
    assert report["process_outcomes"]["available"]
    assert "never-run-binary" in report["commands_not_observed"]["per_element"]["probe.bst"]["named_not_observed"]
    found = disclosure.gaps("plane2.json", "plane2/v3", [report])
    assert found == []


def test_run_context_with_every_optional_flag_has_no_disclosure_gaps(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "project.conf").write_text("name: probe\nvariables:\n  bga-jobserver-env: MYJOBS=-j\n")
    run_context: dict = {}
    run_context_common.add_cpu_capacity_fields(run_context, cpu_budget=4)
    run_context_common.add_memory_capacity_fields(run_context, memory_budget_mb=4096, estimated_job_memory_mb=512)
    run_context_common.add_build_class(
        run_context, build_type="review", variant={"arch": "aarch64", "sanitizer": "address"}
    )
    run_context["jobserver_env"] = _read_bga_jobserver_env(str(project))
    assert run_context["jobserver_env"] == [{"name": "MYJOBS", "prefix": "-j"}]
    run_context["jobserver"] = {
        "mode": "n",
        "ceiling": 4,
        "seed": 3,
        "auth": "fd",
        "project_max_jobs": 8,
    }
    from bga import artifact_weight

    run_context["artifact_weights"] = artifact_weight.weigh_elements(
        str(tmp_path / "cache"), "probe", [("probe.bst", "abc123")]
    )
    run_context["project_refs_provenance"] = {
        "path": "project.refs",
        "sha256": "0" * 64,
    }
    suspended = suspend.slept({"wall": 0.0, "monotonic": 0.0}, {"wall": 30.0, "monotonic": 0.0})
    assert suspended is not None
    run_context["build_outcome"] = {"suspended": suspended}

    found = disclosure.gaps("run-context.json", "run-context/v9", [run_context])
    assert found == []


def test_a_two_dimension_build_class_variant_pseudonymizes_not_none(tmp_path):
    """UX-1070 verify: `build_class.variant`'s map key is class A, and an
    F/G-classed map key drops its whole entry - `bga/bundle.py`'s
    `_rename` used to stringify `_leaf`'s `None` into the literal key
    `"None"` for either."""
    from bga import anonymize
    from bga.bundle import _Anonymizer

    trie = disclosure.compile_policy(disclosure.POLICIES["run-context/v9"])
    document = {"build_class": {"type": "night", "variant": {"arch": "aarch64", "sanitizer": "address"}}}
    pmap = anonymize.PseudonymMap(str(tmp_path / "map.json"))
    walk = _Anonymizer(b"k" * 32, pmap)
    out = walk.rewrite("run-context/v9", trie, document)
    variant = out["build_class"]["variant"]
    assert "None" not in variant
    assert len(variant) == 2
    for key, value in variant.items():
        assert key not in ("arch", "sanitizer")
        assert value not in ("aarch64", "address")
    # Stable: the same key pseudonymizes the same way twice.
    again = _Anonymizer(b"k" * 32, pmap).rewrite("run-context/v9", trie, document)
    assert again["build_class"]["variant"] == variant


def test_a_class_f_or_g_map_key_drops_the_whole_entry(tmp_path):
    """The general mechanism, independent of any live policy: a map key
    the policy classes F or G carries nothing an export can keep as a
    key, so the entry is dropped rather than surfacing as `"None"`."""
    from bga import anonymize
    from bga.bundle import _Anonymizer

    trie = disclosure.compile_policy({"foo.{G}": "C"})
    document = {"foo": {"aws-secret-key-abcdef": 5, "another": 6}}
    pmap = anonymize.PseudonymMap(str(tmp_path / "map.json"))
    walk = _Anonymizer(b"k" * 32, pmap)
    out = walk.rewrite("synthetic/v1", trie, document)
    assert out == {"foo": {}}


def test_a_class_c_map_key_that_is_not_a_number_is_a_gap():
    """`process_outcomes.killed_by_signal`'s map key is class C - a
    signal number - and must look like one, fail-closed against a
    secret smuggled in as a key."""
    numeric = {
        "process_outcomes": {
            "available": True,
            "unknown": 0,
            "exited_zero": 1,
            "exited_nonzero": 0,
            "killed": 1,
            "killed_by_signal": {"9": 1},
            "note": "x",
        }
    }
    assert disclosure.gaps("plane2.json", "plane2/v3", [numeric]) == []
    not_numeric = {
        "process_outcomes": {
            "available": True,
            "unknown": 0,
            "exited_zero": 1,
            "exited_nonzero": 0,
            "killed": 1,
            "killed_by_signal": {"aws-secret-key-abcdef": 1},
            "note": "x",
        }
    }
    found = disclosure.gaps("plane2.json", "plane2/v3", [not_numeric])
    assert found == [
        disclosure.Gap(
            "process_outcomes.killed_by_signal.aws-secret-key-abcdef",
            "key 'aws-secret-key-abcdef' is not on its allowlist",
        )
    ]
