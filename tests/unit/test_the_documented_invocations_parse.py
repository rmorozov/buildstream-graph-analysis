"""UX-327: a command in a guide has to be a command.

`test_docs_links_and_commands.py` has checked since `UX-77` that every
`bga <name>` a guide prints is a real command. It checks the **name**.
Round 45's stranger followed the guides verbatim and the things that
broke were one level down: a flag that had never existed on the command
it was written against, and a positional whose meaning had moved. A
guard on names cannot see either.

So this one parses the whole invocation - including the part past a
line-wrapping backslash, which `UX-516` found the scan was dropping:
`shlex` refuses a trailing backslash, so 17 of 220 invocations were read
as nothing and every flag below their wrap was unchecked.

**How the inventory is built.** Native subcommands come from
`cli.create_parser()`, which is the real thing. The `tools/` aliases
build their parsers inside `main()`, and calling that would *run the
tool* - the `UX-326` lesson, where appending `--help` to a REMAINDER
argv started a real build. So an alias's flags are read from its module
by **AST**: every string literal beginning with `-` passed to
`add_argument`, and every `add_parser("name")`. No import side effects,
no execution, and it cannot drift from the source because it is read
from the source.

**What is deliberately not checked.** Argument *values* (a path in a
guide is illustrative), invocations carrying an ellipsis (elided on
purpose), and anything after a `--` (that is the wrapped build's own
argv, not bga's). Positional *counts* are not checked either: several
commands take optional positionals and a guide legitimately shows the
short form.
"""
import ast
import pathlib
import re
import shlex
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import cli
from bga.tools_dispatch import TOOL_ALIASES

# The same set `test_docs_links_and_commands.py` calls instructional:
# guides and READMEs, where a command is an instruction. Case studies
# and audit rounds record what was run at the time (`UX-139`), and
# holding those to today's parser would be rewriting history.
INSTRUCTIONAL = ("README.md", "docs/README.md", "docs/contributing", "docs/guides")

_FENCE = re.compile(r"^\s*```")
_PROMPT = re.compile(r"^\s*\$?\s*(bga\b.*)$")
# A guide writes `…` or `...` where it elides. Those lines are prose
# with a command shape, not commands.
_ELIDED = ("…", "...")


def _instructional_files():
    files = []
    for entry in INSTRUCTIONAL:
        path = REPO / entry
        if path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
        elif path.exists():
            files.append(path)
    return files


def _join_continuations(lines, index):
    """The whole logical command starting at `lines[index]`, and the
    index of its last physical line. A guide wraps at 80 columns with
    a trailing `\\`; read one line only and `shlex` rejects it."""
    command = _PROMPT.match(lines[index]).group(1)
    while command.rstrip().endswith("\\") and index + 1 < len(lines):
        index += 1
        command = command.rstrip()[:-1] + " " + lines[index].strip()
    return command, index


def documented_invocations():
    """`(path, line number, argv)` for every `bga …` inside a fence."""
    out = []
    for path in _instructional_files():
        lines = path.read_text(encoding="utf-8").splitlines()
        fenced = False
        index = 0
        while index < len(lines):
            line = lines[index]
            if _FENCE.match(line):
                fenced = not fenced
                index += 1
                continue
            if not fenced or not _PROMPT.match(line):
                index += 1
                continue
            number = index + 1
            command, index = _join_continuations(lines, index)
            index += 1
            # Strip a trailing shell comment, then everything from `--`
            # on: that is the wrapped build's argv and belongs to `bst`.
            command = command.split("#", 1)[0]
            # A guide pipes and redirects like a shell does; everything
            # past the first of those belongs to another program.
            command = re.split(r"\s(?:\||>|>>|&&|;)\s?", command, maxsplit=1)[0]
            command = re.split(r"\s--\s", command, maxsplit=1)[0]
            if any(mark in command for mark in _ELIDED):
                continue
            try:
                argv = shlex.split(command)
            except ValueError:
                continue
            if len(argv) >= 2:
                out.append((path.relative_to(REPO), number, argv))
    return out


def _native_actions():
    """`{subcommand: (flags, has_subparsers)}` from the real parser."""
    out = {}
    for action in cli.create_parser()._actions:
        choices = getattr(action, "choices", None)
        if not choices or action.dest != "command":
            continue
        for name, subparser in choices.items():
            flags = set()
            for sub in subparser._actions:
                flags |= set(sub.option_strings)
            out[name] = flags
    return out


def _alias_flags(module_name: str):
    """Every option string and subcommand name in a tool module, by AST.

    Read rather than executed, deliberately: an alias builds its parser
    inside `main()`, and several of them start a build.
    """
    path = REPO / (module_name.replace(".", "/") + ".py")
    if not path.exists():
        return set(), set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    flags, subcommands = set(), set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        literals = [a.value for a in node.args
                    if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if node.func.attr == "add_argument":
            flags |= {text for text in literals if text.startswith("-")}
        elif node.func.attr == "add_parser" and literals:
            subcommands.add(literals[0])
    return flags, subcommands


# `--schema` is not an argparse flag on anything: `cli._maybe_print_schema`
# reads it out of `argv` before the parser runs, because it answers about
# a shape rather than about a run and must not need the run directory the
# command would otherwise demand (`UX-190`). So no parser and no AST scan
# can see it, and the inventory below adds it from the same table the
# hook dispatches on - which also means a guide that prints `--schema` on
# a command the hook refuses is caught, rather than excused.
def _schema_answerable():
    return frozenset(cli._SCHEMA_BY_COMMAND)


def _known(command):
    """`(flags, subcommands)` for one `bga` command, native or alias.

    `(set(), set())` when the name is not a command at all - that is the
    name guard's business, and answering here would let a line of prose
    inside a fence be checked as an invocation.
    """
    native = _native_actions()
    extra = {"-h", "--help"}
    if command in _schema_answerable():
        extra.add("--schema")
    if command in native:
        return native[command] | extra, set()
    if command not in TOOL_ALIASES:
        return set(), set()
    flags, subcommands = _alias_flags(TOOL_ALIASES[command][0])
    return flags | extra, subcommands


class TestEveryDocumentedInvocationParses:

    def test_the_scan_finds_the_commands_the_guides_teach(self):
        """A scan that matched nothing would pass every clause below -
        which is how a name-only guard let four invocations through."""
        found = documented_invocations()
        assert len(found) >= 40, (
            f"only {len(found)} `bga …` invocations found in the guides; "
            "there were 80-odd when this was written, so the fence or "
            "prompt pattern has moved")
        commands = {argv[1] for _, _, argv in found}
        assert {"analyze", "snapshot", "compare"} <= commands, (
            f"the guides no longer teach the basic loop: {sorted(commands)}")

    def test_a_wrapped_invocation_is_read_past_its_backslash(self):
        """`UX-516`: the CI owner's step 2 wraps over two lines, so the
        scan saw a trailing `\\`, `shlex` refused it, and `--candidate`
        and `--exclude` were never checked against the parser. Read from
        the source, not restated: for every invocation whose own line is
        continued, the next line's first token must be in the argv."""
        breaks = re.compile(r"[#|;]|>|&&|\s--\s")
        wrapped = []
        for path, number, argv in documented_invocations():
            lines = (REPO / path).read_text(encoding="utf-8").splitlines()
            head = lines[number - 1]
            if not head.rstrip().endswith("\\") or breaks.search(head):
                continue
            tail = lines[number].strip().rstrip("\\")
            try:
                tokens = shlex.split(tail)
            except ValueError:
                continue
            if not tokens or tokens[0] in ("--", "|", ">", ">>", "&&", ";"):
                continue
            wrapped.append(f"{path}:{number}")
            assert tokens[0] in argv, (
                f"{path}:{number}: the scan stopped at the backslash - "
                f"{tokens[0]!r} is on the next line and not in {argv}")
        assert len(wrapped) >= 8, (
            f"only {len(wrapped)} wrapped invocation(s) reached the check; "
            "there were 11 when this was written, so the join or the "
            "guides' wrapping has moved")

    def test_no_documented_flag_is_one_the_command_does_not_have(self):
        """`bga cache-logs . --native-report @last` is the shape: a real
        command, a real-looking flag, and nothing that checked."""
        offenders = []
        for path, number, argv in documented_invocations():
            command = argv[1]
            if command.startswith("-"):
                continue
            flags, _ = _known(command)
            if not flags:
                continue  # not a command; the name guard owns that
            for token in argv[2:]:
                if not token.startswith("-") or token == "--":
                    continue
                name = token.split("=", 1)[0]
                if name not in flags:
                    offenders.append(
                        f"{path}:{number}: `bga {command} {name}` - no such flag")
        assert not offenders, (
            "documented flag(s) the command does not have:\n  "
            + "\n  ".join(offenders))

    def test_no_documented_subcommand_is_one_the_command_does_not_have(self):
        """`bga capture census` is the shape this checks - a second word
        under a command that dispatches on it."""
        offenders = []
        for path, number, argv in documented_invocations():
            command = argv[1]
            _, subcommands = _known(command)
            if not subcommands or len(argv) < 3:
                continue
            word = argv[2]
            if word.startswith("-"):
                continue
            if word not in subcommands:
                offenders.append(
                    f"{path}:{number}: `bga {command} {word}` - {command} "
                    f"dispatches on {sorted(subcommands)}")
        assert not offenders, (
            "documented subcommand(s) that do not exist:\n  "
            + "\n  ".join(offenders))

    def test_the_flag_inventory_is_really_read_from_the_source(self):
        """The AST reader is the load-bearing half for every alias, and
        a reader that returned nothing would make the clause above
        vacuous for all nineteen of them."""
        flags, subcommands = _alias_flags("tools.bst_native_build_tracer")
        assert "--wrapped-log" in flags, sorted(flags)[:20]
        assert {"run", "report", "census", "replay-sandbox"} <= subcommands, (
            f"`bga capture` dispatches on {sorted(subcommands)}")


class TestTheHelpDoesNotCiteWhatIsNotThere:

    def test_every_doc_path_a_help_string_names_exists(self):
        """`bga snapshot --help` ended with "Full background:
        docs/guides/local-loop.md", and that file has never existed. A
        help string is a document a reader is being sent to."""
        pattern = re.compile(r"docs/[a-z0-9/_-]+\.md")
        missing = []
        for path in sorted((REPO / "tools").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for match in pattern.findall(text):
                if not (REPO / match).exists():
                    missing.append(f"{path.relative_to(REPO)} -> {match}")
        for path in sorted((REPO / "bga").rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for match in pattern.findall(text):
                if not (REPO / match).exists():
                    missing.append(f"{path.relative_to(REPO)} -> {match}")
        assert not missing, (
            "source names documentation that does not exist:\n  "
            + "\n  ".join(sorted(set(missing))))


class TestTheMisuseErrorSaysWhatWouldHaveWorked:
    """`UX-327`'s other half. A guide that is right is not enough if the
    command's own refusal cannot get a reader from what they typed to
    what works."""

    def _cache_logs(self, tmp_path, *argv):
        import subprocess

        return subprocess.run(
            [sys.executable, "-m", "bga.cli", "cache-logs", *argv],
            capture_output=True, text=True, cwd=str(tmp_path), timeout=120,
            env={**__import__("os").environ, "PYTHONPATH": str(REPO)})

    def test_a_log_root_with_nothing_in_it_names_the_two_ways_out(self, tmp_path):
        done = self._cache_logs(tmp_path, ".")
        assert done.returncode == 1, done.stdout
        message = done.stderr
        assert str(tmp_path) in message, (
            f"the error says where it looked as `.`, which only the reader "
            f"can resolve:\n{message}")
        assert "--project" in message, (
            f"the error names neither of the arguments that would have "
            f"worked:\n{message}")
        assert "PROJECT_DIR" in message, message
        assert "--list" in message, message

    def test_a_project_directory_still_gets_the_project_shaped_error(
            self, tmp_path):
        """The negative: `UX-127`'s better message must not be replaced
        by the generic one."""
        (tmp_path / "project.conf").write_text("name: ux327\n", encoding="utf-8")
        done = self._cache_logs(tmp_path, str(tmp_path))
        assert done.returncode == 1
        assert "for project 'ux327'" in done.stderr, done.stderr
        assert "declares `name: ux327`" in done.stderr, done.stderr
