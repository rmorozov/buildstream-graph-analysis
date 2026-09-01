"""UX-465: the spec-to-project generator, and that `bst` accepts it.

Two halves, and only one of them needs `bst`.

The half that does not is the emitter's own contract: a spec that names
a reserved element or a dangling edge is refused with a sentence, and
the YAML it writes **parses as YAML**. That last one is not
ceremonial - the first version wrote install-commands inside double
quotes, the process-storm command contains a `sh -c "..."`, and bst
refused the whole project with `did not find expected key`. A
generator whose output only sometimes parses is worse than no
generator, because the failure lands on whoever runs it next.

The half that does is the point of the item: `bst build` accepts what
this writes. It skips where `bst` and `bwrap` are absent, which is CI's
`test` job; `bst-examples` is where it runs.
"""
import json
import pathlib
import shutil
import subprocess

import pytest
import yaml

from tools import bga_gen_project as gen

REPO = pathlib.Path(__file__).resolve().parents[2]
SPECS = REPO / "tests/fixtures/specs"
BST_AVAILABLE = shutil.which("bst") is not None
BWRAP_AVAILABLE = shutil.which("bwrap") is not None
BUSYBOX_AVAILABLE = shutil.which("busybox") is not None


def _spec(name):
    return json.loads((SPECS / name).read_text(encoding="utf-8"))


class TestTheSpecIsChecked:
    def test_a_reserved_uid_is_refused(self):
        """`runtime.bst` and `all.bst` are the generator's own. A spec
        that declares one would have it silently overwritten."""
        spec = _spec("shared-base-wide.json")
        spec["graph"]["elements"].append({"uid": "all.bst"})
        with pytest.raises(gen.SpecError, match="all.bst"):
            gen.validate(spec)

    def test_an_edge_to_nothing_is_refused(self):
        spec = _spec("shared-base-wide.json")
        spec["graph"]["dependencies"].append(
            {"predecessor": "ghost.bst", "successor": "mod0.bst"})
        with pytest.raises(gen.SpecError, match="ghost.bst"):
            gen.validate(spec)

    def test_the_wrong_version_is_refused(self):
        with pytest.raises(gen.SpecError, match="spec_version"):
            gen.validate({"spec_version": 99})

    def test_the_committed_specs_validate(self):
        found = sorted(p.name for p in SPECS.glob("*.json"))
        assert found, "no spec is committed, so the acceptance test cannot run"
        for name in found:
            gen.validate(_spec(name))


class TestTheWorkBecomesRealCommands:
    def test_a_failure_runs_last(self):
        """A build that fails at once exercises none of the capture.
        `UX-463`'s axis D wants a build that did its work and *then*
        failed."""
        commands = gen._commands({"seconds": 2.0, "fails": True})
        assert commands[-1] == "exit 1"
        assert any("sleep" in c for c in commands[:-1])

    def test_processes_and_files_are_commands_not_annotations(self):
        """Axis F cannot be asserted into existence: the hook sees
        processes and staging because the sandbox really ran them."""
        commands = gen._commands({"seconds": 1.0, "processes": 8, "files": 200})
        joined = " ".join(commands)
        assert "seq 1 200" in joined
        assert "touch" in joined
        assert joined.count("&") >= 1 and "wait" in joined

    def test_an_element_with_no_work_still_has_a_command(self):
        """`install-commands: []` is not a manual element bst will run."""
        assert gen._commands({}) == ["sleep 0.10"]
        assert gen._commands({"seconds": 0}) == ["true"]


class TestTheYamlItWritesIsYaml:
    def test_a_command_holding_double_quotes_survives(self):
        """The bug this file was written after. The process-storm
        command contains `sh -c "sleep 0.30"`; inside a double-quoted
        scalar the inner quote closes it and bst refuses the project."""
        body = gen._element_yaml(
            "x.bst", "manual", ["runtime.bst"],
            {"seconds": 1.0, "processes": 4})
        parsed = yaml.safe_load(body)

        commands = parsed["config"]["install-commands"]
        assert any('sh -c "' in c for c in commands), commands

    def test_a_command_holding_single_quotes_survives(self):
        """The other half of the escape. No knob writes a single
        quote today, so this goes through `_scalar` directly - the
        clause that keeps it honest when one does."""
        command = """echo 'hi' && sh -c "true" """.strip()
        body = ("kind: manual\nconfig:\n  install-commands:\n"
                f"  - {gen._scalar(command)}\n")

        parsed = yaml.safe_load(body)
        assert parsed["config"]["install-commands"] == [command]

    def test_every_element_of_every_committed_spec_parses(self, tmp_path):
        for spec_file in sorted(SPECS.glob("*.json")):
            out = gen.write_project(_spec(spec_file.name),
                                    tmp_path / spec_file.stem,
                                    busybox=shutil.which("busybox") or __file__)
            for element in sorted((out / "elements").glob("*.bst")):
                parsed = yaml.safe_load(element.read_text(encoding="utf-8"))
                assert isinstance(parsed, dict), f"{spec_file.name}:{element.name}"
                assert "kind" in parsed


class TestTheTwoHalvesSpeakOneLanguage:
    def test_a_topology_becomes_a_spec(self):
        """`UX-465`'s one-language rule: the spec's graph is
        `tests/fixtures/topologies.py`'s graph verbatim, so the curated
        fixture and the generated project describe one shape."""
        from tests.fixtures import topologies

        topology = topologies.shared_base_wide()
        spec = gen.spec_from_topology(topology, "t")

        assert spec["graph"] is topology[1]
        assert spec["work"]["toolchain.bst"]["seconds"] == pytest.approx(0.2)
        assert spec["work"]["mod0.bst"]["seconds"] == pytest.approx(6.0)

    def test_the_committed_spec_is_that_shape_at_a_tenth_the_seconds(self):
        """The acceptance spec is `shared_base_wide` scaled, not a
        second hand-written graph - if they drifted apart the curated
        and generated halves would stop being the same case."""
        from tests.fixtures import topologies

        spec = _spec("shared-base-wide.json")
        uids = {e["uid"] for e in topologies.shared_base_wide()[1]["elements"]}

        assert {e["uid"] for e in spec["graph"]["elements"]} == uids
        assert spec["work"]["mod0.bst"]["seconds"] == pytest.approx(0.6)


@pytest.mark.bst
@pytest.mark.skipif(
    not (BST_AVAILABLE and BWRAP_AVAILABLE and BUSYBOX_AVAILABLE),
    reason="bst/bwrap/busybox not all found on PATH - "
           "see docs/spec/ingestion-pipeline.md",
)
class TestBstAcceptsWhatItWrites:
    def test_the_acceptance_spec_builds(self, tmp_path):
        """`UX-465`'s Acceptance Test, minus the capture - the capture
        is `bga snapshot`'s own guard, and this one is about whether
        `bst` accepts a generated project at all."""
        out = gen.write_project(_spec("shared-base-wide.json"),
                                tmp_path / "project")
        done = subprocess.run(
            ["bst", "build", "all.bst"], cwd=str(out),
            capture_output=True, text=True,
            env=_isolated(tmp_path))

        assert done.returncode == 0, done.stderr[-2000:]
        assert "Build Queue: processed 9" in done.stderr, done.stderr[-2000:]

    def test_the_failing_spec_really_fails(self, tmp_path):
        """Axis D. A spec that says an element fails must produce a
        build that fails - not one that errors before starting, which
        would exercise none of the capture."""
        out = gen.write_project(_spec("a-build-that-fails.json"),
                                tmp_path / "project")
        done = subprocess.run(
            ["bst", "build", "all.bst"], cwd=str(out),
            capture_output=True, text=True,
            env=_isolated(tmp_path))

        assert done.returncode != 0
        assert "mod2.bst" in done.stderr
        assert "Command failed" in done.stderr, done.stderr[-2000:]


def _isolated(tmp_path):
    """A bst that keeps its caches inside `tmp_path`, so the two builds
    above are cold and do not touch the developer's own store."""
    import os

    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return dict(os.environ, XDG_CACHE_HOME=str(home / "cache"),
                XDG_CONFIG_HOME=str(home / "config"),
                XDG_DATA_HOME=str(home / "data"))
