"""UX-191: tab completion without a rewrite.

Field feedback: *"maybe it's good idea to bring autocompletion for
command line... it looks like migration to python3 click from native
argparse can simplify support of such scenario. it will greatly improve
UX on commands like bga cache-trend."*

The need is real - eleven subcommands, seventeen aliases, sticky flags
and `@`-run-references are exactly what completion is for. (The task
file says fifteen and ten; those are the filing's estimates, and
`test_every_alias_completes` below counts the real ones.) The migration is
not: `argcomplete` completes an argparse program as it stands. That
decision, and its reasons, are recorded in the task file; what is
guarded here is that the completion actually answers.

The completions are driven through the real `argcomplete` entry point
where possible, and through the completer functions directly where the
answer depends on a project on disk.
"""
import io
import json
import os
import shutil
import subprocess
import sys

import pytest

from bga import cli

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"


def _project(tmp_path, snapshots=("20260101T000000Z", "20260102T000000Z")):
    """A project with a `.bga` store holding `snapshots`."""
    (tmp_path / "project.conf").write_text("name: completions\nmin-version: 2.0\n")
    for stamp in snapshots:
        run = tmp_path / ".bga" / "runs" / stamp / "run"
        run.parent.mkdir(parents=True)
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
    return tmp_path


class TestTheCommandNames:
    def test_subcommands_complete(self):
        assert "analyze" in cli._command_completer("ana", None)
        assert "compare" in cli._command_completer("comp", None)

    def test_every_alias_completes(self):
        """The `UX-67` aliases are not argparse subparsers - registering
        them would import every tool to build the parser, on every `bga
        analyze`. A completion that offered only half the tool would be
        worse than none.

        Every one of them, read from `TOOL_ALIASES` rather than a list
        written out here: a hand-written sample passed while the prose
        around it claimed a count (ten) that the real mapping (17) had
        outgrown.
        """
        from bga.tools_dispatch import TOOL_ALIASES

        offered = set(cli._command_completer("", None))
        missing = sorted(set(TOOL_ALIASES) - offered)
        assert not missing, f"not completable: {missing}"

    def test_it_offers_nothing_for_a_prefix_nothing_matches(self):
        assert cli._command_completer("zzz", None) == []

    def test_a_broken_completer_answers_nothing_rather_than_raising(
            self, monkeypatch):
        """A dead TAB is worse than no answer: an exception here reaches
        the user's shell as a traceback in the middle of a command
        line."""
        monkeypatch.setattr(cli, "create_parser",
                            lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert cli._command_completer("a", None) == []


class TestTheRunReferences:
    """The completion the feedback named: *"bga cache-trend"*, whose
    argument is a run."""

    def test_the_aliases_are_offered(self, tmp_path, monkeypatch):
        monkeypatch.chdir(_project(tmp_path))
        offered = cli._snapshot_completer("@", None)
        assert "@last" in offered and "@prev" in offered

    def test_the_stores_own_stamps_are_offered(self, tmp_path, monkeypatch):
        monkeypatch.chdir(_project(tmp_path))
        offered = cli._snapshot_completer("@2026", None)
        assert "@20260101T000000Z" in offered
        assert "@20260102T000000Z" in offered

    def test_outside_a_project_only_the_aliases_are_offered(
            self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert cli._snapshot_completer("@", None) == ["@last", "@prev"]

    def test_an_unreadable_store_answers_nothing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(_project(tmp_path))
        monkeypatch.setattr("bga.run_store.list_runs",
                            lambda _p: (_ for _ in ()).throw(OSError("nope")))
        assert cli._snapshot_completer("@", None) == []

    def test_every_run_shaped_argument_has_it(self):
        """Driven off the same lists `_resolve_run_aliases` uses, so an
        argument that learns to take an alias gets completion for it
        without a second edit."""
        parser = cli.create_parser()
        attached = {}

        def walk(node, command="bga"):
            for action in node._actions:
                if getattr(action, "choices", None) and hasattr(action.choices, "keys"):
                    for name, sub in action.choices.items():
                        if sub is not None:
                            walk(sub, name)
                elif getattr(action, "completer", None):
                    attached.setdefault(command, set()).add(action.dest)

        walk(parser)
        assert "directory" in attached["analyze"]
        assert {"baseline", "candidate"} <= attached["compare"]
        assert "target" in attached["blast"]


class TestElementNames:
    def test_they_come_from_the_project(self, tmp_path, monkeypatch):
        project = _project(tmp_path)
        elements = project / "elements"
        elements.mkdir()
        for name in ("base.bst", "lib.bst", "app.bst"):
            (elements / name).write_text("kind: manual\n")
        monkeypatch.chdir(project)

        offered = cli._element_completer("li", None)
        assert offered == ["lib.bst"]

    def test_no_project_means_no_walk_at_all(self, tmp_path, monkeypatch):
        """Not merely an empty answer - no walk.

        Falsifying the first version of this guard found it toothless:
        deleting the `project is None` branch, so the completer walked
        the current directory instead, left it green, because a `tmp_path`
        holds no `.bst` files either way. But the directory a user TABs
        in outside a project is `$HOME` or `/`, and a recursive walk of
        that on every keypress is the dead TAB this completer's whole
        design avoids. So the guard pins the call, not the answer.
        """
        monkeypatch.chdir(tmp_path)
        walked = []
        monkeypatch.setattr(
            "tools.bst_native_build_tracer.discover_element_names",
            lambda project: walked.append(project) or [])

        assert cli._element_completer("", None) == []
        assert walked == [], f"walked {walked} with no project to walk"


class TestTheIntegrationIsInert:
    """Nothing about this may change what the CLI does when the shell
    hook is not active - which is every invocation in CI, in a script,
    and in this suite."""

    def test_the_marker_line_is_present(self):
        """`register-python-argcomplete` and the global hook both look
        for it in the first kilobyte of the entry point."""
        source = open("bga/cli.py", encoding="utf-8").read(1024)
        assert "PYTHON_ARGCOMPLETE_OK" in source

    def test_autocomplete_is_called(self):
        source = open("bga/cli.py", encoding="utf-8").read()
        assert "argcomplete.autocomplete(create_parser())" in source

    def test_a_missing_argcomplete_is_not_an_error(self, monkeypatch):
        real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) \
            else __builtins__.__import__

        def refuse(name, *args, **kwargs):
            if name == "argcomplete":
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", refuse)
        cli._maybe_complete()   # must not raise

    def test_help_output_is_unchanged(self):
        """`UX-158`'s caps: completion must not have grown the help by a
        line."""
        result = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main(['analyze','--help']))"],
            capture_output=True, text=True, cwd=os.getcwd())
        assert len(result.stdout.splitlines()) <= 45

    def test_the_command_still_runs_without_the_shell_hook(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main("
             "['analyze', %r, '--format', 'json']))" % GOLDEN],
            capture_output=True, text=True, cwd=os.getcwd())
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["schema"] == "analyze/v4"


class TestThroughArgcompleteItself:
    """The real entry point, driven the way the shell drives it."""

    def _complete(self, line, tmp_path):
        argcomplete = pytest.importorskip("argcomplete")

        output = io.StringIO()
        environment = dict(
            os.environ,
            _ARGCOMPLETE="1",
            _ARGCOMPLETE_IFS="\013",
            COMP_LINE=line,
            COMP_POINT=str(len(line)),
            _ARGCOMPLETE_COMP_WORDBREAKS=" \t\n\"'><=;|&(:",
        )
        # argcomplete exits the process when it is done answering, which
        # is what the shell wants and not what a test does.
        with pytest.raises(SystemExit):
            _run(argcomplete, environment, output)
        return [item for item in output.getvalue().split("\013") if item]

    def test_bga_tab_lists_the_commands(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        completions = self._complete("bga ana", tmp_path)
        assert "analyze" in completions


def _run(argcomplete, environment, output):
    """`argcomplete.autocomplete` under a synthetic shell environment."""
    import os as _os

    saved = dict(_os.environ)
    _os.environ.update(environment)
    try:
        argcomplete.autocomplete(
            cli.create_parser(),
            exit_method=lambda _code=0: (_ for _ in ()).throw(SystemExit(0)),
            output_stream=_Bytes(output),
            append_space=False,
        )
    finally:
        _os.environ.clear()
        _os.environ.update(saved)


class _Bytes:
    """argcomplete writes bytes; the assertions want text."""

    def __init__(self, sink):
        self._sink = sink

    def write(self, data):
        self._sink.write(data.decode() if isinstance(data, bytes) else data)

    def flush(self):
        pass


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
