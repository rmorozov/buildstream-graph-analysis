"""UX-385: a capture can detect the binary it never saw.

`UX-105` established that the LD_PRELOAD hook "cannot detect its own
absence" and `UX-376` stopped `--trace-spine=auto` from *assuming* it
could. Neither closes the case where the spine is off - by policy, by
`--trace-spine=off`, or on an older capture - and a statically linked
binary ran anyway.

It is detectable, and one capture holds both halves. An element's
`build-commands` name the binaries it invokes; its records name the
binaries the hook saw. On the fixture `UX-376` was built from, with the
spine off:

```text
consumer.bst build-commands name   codegen
consumer.bst records name          sh, mkdir
```

`codegen` is in the commands and in no record for that element. That is
the hook detecting its own absence, from data in the same capture.

**Evidence, not a verdict.** A command under a shell conditional that
did not fire, or one an element inherits from a `.bst` include, is
named and legitimately never ran - so the published key is
`named_not_observed`, and `commands_not_read` counts the lines whose
program name is assembled at runtime, which a leading-token comparison
cannot reach by construction. Calling any of it "missed" would be a
finding, and this is the measurement a finding would rest on.
"""
import pathlib
import sys
import textwrap

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.bst_native_build_tracer import (
    _named_binaries,
    detect_named_but_unobserved,
)


def _project(tmp_path, elements):
    """A project on disk with the given `{name: yaml}` elements."""
    (tmp_path / "project.conf").write_text(
        "name: fixture\nmin-version: 2.0\nelement-path: elements\n",
        encoding="utf-8")
    directory = tmp_path / "elements"
    directory.mkdir(exist_ok=True)
    (tmp_path / "files").mkdir(exist_ok=True)
    for name, body in elements.items():
        (directory / name).write_text(textwrap.dedent(body), encoding="utf-8")
    return str(tmp_path)


#: `UX-376`'s shape, with the commands it was always going to run:
#: `hosttool.bst` produces a tool and `consumer.bst` runs it.
RUNS_A_BUILT_TOOL = {
    "toolchain.bst": """
        kind: import
        sources:
        - kind: local
          path: files
        """,
    "hosttool.bst": """
        kind: manual
        depends:
        - filename: toolchain.bst
          type: build
        config:
          build-commands:
          - cc -static -o codegen codegen.c
        """,
    "consumer.bst": """
        kind: manual
        depends:
        - filename: toolchain.bst
          type: build
        - filename: hosttool.bst
          type: build
        config:
          build-commands:
          - mkdir -p out
          - codegen -o out/generated.c
        """,
}

#: What the hook saw with the spine off: the shell and the one dynamic
#: program. `codegen` is static, so it ran and left no record.
SPINE_OFF = {"consumer.bst": {"sh", "mkdir"},
             "hosttool.bst": {"sh", "cc"}}

#: What the spine saw. The same build, plus the process the hook could
#: not.
SPINE_ON = {"consumer.bst": {"sh", "mkdir", "codegen"},
            "hosttool.bst": {"sh", "cc"}}


class TestTheCaptureNamesWhatItDidNotSee:
    def test_the_spine_off_capture_names_the_tool(self, tmp_path):
        """The Falsification, first half."""
        project = _project(tmp_path, RUNS_A_BUILT_TOOL)
        found = detect_named_but_unobserved(
            project, sorted(RUNS_A_BUILT_TOOL), SPINE_OFF)
        entry = found["per_element"]["consumer.bst"]
        assert entry["named_not_observed"] == ["codegen"], entry
        assert found["elements_with_gap"] == ["consumer.bst"]

    def test_the_spine_on_capture_names_nothing(self, tmp_path):
        """The Falsification, second half - and the direction that
        makes this a measurement rather than a complaint about every
        element that runs anything."""
        project = _project(tmp_path, RUNS_A_BUILT_TOOL)
        found = detect_named_but_unobserved(
            project, sorted(RUNS_A_BUILT_TOOL), SPINE_ON)
        assert found["elements_with_gap"] == [], found["per_element"]

    def test_an_element_whose_commands_all_ran_is_clean(self, tmp_path):
        project = _project(tmp_path, RUNS_A_BUILT_TOOL)
        found = detect_named_but_unobserved(
            project, sorted(RUNS_A_BUILT_TOOL), SPINE_OFF)
        assert found["per_element"]["hosttool.bst"][
            "named_not_observed"] == []

    def test_it_publishes_both_sides_of_the_comparison(self, tmp_path):
        """A reader who disagrees with the verdict has to be able to
        check it, which means seeing what was named and what was seen -
        `UX-229`'s rule, one block down."""
        project = _project(tmp_path, RUNS_A_BUILT_TOOL)
        entry = detect_named_but_unobserved(
            project, sorted(RUNS_A_BUILT_TOOL), SPINE_OFF
        )["per_element"]["consumer.bst"]
        assert entry["named"] == ["codegen", "mkdir"]
        assert entry["observed"] == ["mkdir", "sh"]

    def test_without_a_project_it_says_so_rather_than_nothing(self):
        """`UX-107`'s rule: "nobody could look" must not read as
        "looked and found nothing"."""
        found = detect_named_but_unobserved(None, [], {})
        assert found["available"] is False
        assert "--project-dir" in found["note"]

    def test_the_note_says_it_is_evidence_and_not_a_verdict(self, tmp_path):
        project = _project(tmp_path, RUNS_A_BUILT_TOOL)
        note = detect_named_but_unobserved(
            project, sorted(RUNS_A_BUILT_TOOL), SPINE_OFF)["note"]
        assert "not a verdict" in note
        assert "conditional" in note, (
            "the note does not name the false positive a reader will "
            "meet first")


class TestWhatTheComparisonCanAndCannotRead:
    """The Out of Scope, made checkable. The leading token of each line
    is what this compares; a command assembled at runtime is out of
    reach by construction, and the published wording has to admit it."""

    @pytest.mark.parametrize("commands,named", (
        (["codegen --out x.c"], ["codegen"]),
        (["cd build && make -j4"], ["make"]),                # builtin, then
        (["for f in *.c; do gcc -c $f; done"], ["gcc"]),      # inside a loop
        (["if [ -f x ]; then codegen x; fi"], ["codegen"]),   # inside a test
        (["CC=clang cc -c x.c"], ["cc"]),                     # env prefix
        (["/usr/bin/protoc --cpp_out=. a.proto"], ["protoc"]),  # absolute
        (["echo hi", "set -e", "cd src"], []),                # builtins only
    ))
    def test_it_reads_the_program_out_of_each_shape(self, commands, named):
        assert _named_binaries(commands)[0] == named

    @pytest.mark.parametrize("line", (
        "%{make} install",
        "$(which codegen) x",
        "`cat toolname` --run",
    ))
    def test_a_name_it_cannot_resolve_is_counted_not_guessed(self, line):
        found, unread = _named_binaries([line])
        assert found == []
        assert unread == [line], (
            "a command whose program name is assembled at runtime was "
            "silently dropped instead of counted")

    def test_the_count_of_unreadable_lines_is_published(self, tmp_path):
        project = _project(tmp_path, {
            "one.bst": """
                kind: manual
                config:
                  build-commands:
                  - codegen a
                  - '%{make} install'
                """})
        entry = detect_named_but_unobserved(
            project, ["one.bst"], {})["per_element"]["one.bst"]
        assert entry["commands_not_read"] == 1
        assert entry["named_not_observed"] == ["codegen"], (
            "an unreadable line changed the answer for the lines that "
            "were readable")

    def test_a_loop_header_is_not_a_program(self):
        """`for f in *.c` names a variable and a word list. Reporting
        `f` as a binary nobody observed would put a finding on every
        element that writes a loop."""
        assert "f" not in _named_binaries(
            ["for f in *.c; do gcc -c $f; done"])[0]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
