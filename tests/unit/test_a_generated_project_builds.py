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
import re
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
    above are cold and do not touch the developer's own store.

    `UX-760`: `XDG_CONFIG_HOME` pointed at `home / "config"` - a
    directory this never created, so `bst` found no file there and fell
    back to the 5% default reserve, unprotected. `_bst_env`'s shared,
    populated fixture replaces that hole.
    """
    import os

    from tests.unit._bst_env import BST_XDG_CONFIG_HOME

    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return dict(os.environ, XDG_CACHE_HOME=str(home / "cache"),
                XDG_CONFIG_HOME=str(BST_XDG_CONFIG_HOME),
                XDG_DATA_HOME=str(home / "data"))


# --- UX-775/UX-801: a third un-isolated CAS-writing file can't land silently

#: gate on `bst` but never write to CAS. `UX-801`'s verifier could not tell
#: from a bare filename whether that was still true, so each entry carries
#: the command the file actually runs - checked against below.
_NOT_CAS_WRITING = {
    "test_the_printed_sentences_are_contracts.py": "bga blast/correlate "
                                                     "argv only, no bst call",
}

#: writes to CAS and isolates, but predates `_bst_env.py` - its own
#: `BST_XDG_CONFIG_HOME` reads the same fixture `_bst_env.py` does.
_ISOLATES_ITS_OWN_WAY = {"test_the_journey_has_an_answer_key.py"}

_GATE = 'shutil.which(' + '"bst"' + ')'  # split so this clause doesn't self-match

#: a name this file bound from `shutil.which("bst")`/`which("bst")` - the
#: shape `tools/bga_doctor.py`'s own `bst = shutil.which("bst")` uses, so
#: `[bst, "show", ...]` names `bst` as a bare identifier, not a literal.
_BST_BINDING_RE = re.compile(r'''\b(\w+)\s*=\s*(?:shutil\.)?which\(\s*["']bst["']\s*\)''')

#: call sites that always shell to a CAS-writing subcommand without ever
#: spelling it as a literal argv token in the caller - `extract_graph`
#: (tools/bst_show_to_graph.py) hardcodes `bst show`, `check_project_loads`
#: (tools/bga_doctor.py) hardcodes `bst show --deps none`.
_KNOWN_CAS_WRITING_CALLS = {"extract_graph(": "show", "check_project_loads(": "show"}


def _cas_writing_subcommand(text):
    """The `bst` subcommand `text` calls that writes the CAS, or None.

    An argv list naming `bst` and, within a handful of tokens, one of the
    CAS-writing subcommands - the shape `subprocess.run(["bst", ...])` and
    `run_traced_build(..., ["bst", "--no-colors", "build", ...], ...)` use,
    where `bst` is either the literal string or a name this same file bound
    from `which("bst")`."""
    names = ['["\']bst["\']'] + [r'\b' + re.escape(n) + r'\b'
                                  for n in _BST_BINDING_RE.findall(text)]
    argv_re = re.compile(
        r'(?:' + '|'.join(names) + r')'
        r'''(?:\s*,\s*["'][^"']*["']){0,4}\s*,\s*["'](show|build|artifact)["']'''
    )
    match = argv_re.search(text)
    if match:
        return match.group(1)
    for call, subcommand in _KNOWN_CAS_WRITING_CALLS.items():
        if call in text:
            return subcommand
    return None


def _bst_gated_files():
    return [p for p in sorted((REPO / "tests").rglob("test_*.py"))
            if _GATE in p.read_text(encoding="utf-8")]


def test_every_cas_writing_bst_gated_file_reaches_the_isolation():
    """`UX-760` moved twelve bst-gated, CAS-writing files onto
    `_bst_env.py`'s isolated `HOME`; `UX-775`/`UX-801` the last five. A
    sixth landing without it fails only on a negative-margin host - this
    counts the population so it fails here instead."""
    gated = _bst_gated_files()
    assert len(gated) == 18, sorted(p.name for p in gated)  # UX-760's own count

    excluded = set(_NOT_CAS_WRITING) | _ISOLATES_ITS_OWN_WAY
    cas_writing = [p for p in gated if p.name not in excluded]
    assert len(cas_writing) == 16, sorted(p.name for p in cas_writing)

    missing = sorted(p.name for p in cas_writing
                      if "_bst_env" not in p.read_text(encoding="utf-8"))
    assert not missing, (
        f"{missing} shell out to a real bst without tests/unit/_bst_env.py's "
        "isolated HOME - either route the build through isolated_bst_env/"
        "bst_env, or add the file to this guard's named exclusions with why"
    )


def test_no_excluded_file_actually_writes_the_cas():
    """`UX-775`'s verifier named the gap: a file mislabelled into
    `_NOT_CAS_WRITING` this guard could not see. Each entry's own file is
    read back for a `bst` call whose subcommand writes the CAS."""
    offending = {}
    for name in _NOT_CAS_WRITING:
        text = (REPO / "tests/unit" / name).read_text(encoding="utf-8")
        subcommand = _cas_writing_subcommand(text)
        if subcommand:
            offending[name] = subcommand
    assert not offending, (
        f"{offending} run a CAS-writing bst subcommand while excluded from "
        "the isolation as _NOT_CAS_WRITING - move them onto _bst_env.bst_env "
        "instead of excluding them"
    )
