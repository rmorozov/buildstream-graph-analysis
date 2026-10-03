"""UX-1307: a flag a user can pass is named in `docs/guides/cli.md`.

The inventory is `test_the_documented_invocations_parse`'s own (native
parser plus AST over the tool aliases), reused rather than copied. A
`--flag` of any subcommand that `cli.md` does not name is red. The audited
flags are also pinned to their own command's section, so an env-table
mention elsewhere does not count.
"""

import functools
import re

import pytest

from bga.tools_dispatch import TOOL_ALIASES
from tests.unit.test_the_documented_invocations_parse import REPO, _known, _native_actions

CLI_MD = (REPO / "docs/guides/cli.md").read_text(encoding="utf-8")

# (command, flag): must sit inside that command's own `## bga <command>` section.
PINNED = [
    *[
        (c, f)
        for c in ("extract",)
        for f in (
            "--build-type",
            "--variant",
            "--cache-usage",
            "--memory-budget-mb",
            "--estimated-job-memory-mb",
            "--native-max-jobs",
            "--trace-epsilon-us",
            "--start-time",
            "--interrupted",
            "--strict",
            "--bst-bin",
        )
    ],
    *[
        ("run-context", f)
        for f in (
            "--build-type",
            "--variant",
            "--memory-budget-mb",
            "--estimated-job-memory-mb",
            "--native-max-jobs",
            "--trace-epsilon-us",
            "--start-time",
        )
    ],
    ("graph-from-show", "--bst-bin"),
    ("log-to-chrome", "--start-time"),
    ("view", "--compare"),
    ("view", "--port"),
    ("baseline", "--remote"),
    ("baseline", "--workdir"),
    ("rebuild-set", "--cut"),
    ("rebuild-set", "--count-only"),
    ("capture", "--host-samples"),
    ("baseline", "--exclude"),
    ("baseline", "--repo"),
    ("baseline", "--band-k"),
    ("baseline", "--count"),
    ("compare", "--band-k"),
    ("checkout-cost", "--individual"),
    ("checkout-cost", "--consolidated"),
    ("release-notes", "--from"),
    ("release-notes", "--to"),
    *[
        ("gen-synthetic", f)
        for f in ("--layers", "--width", "--run-id", "--store", "--runs", "--workload", "--builders")
    ],
    ("snapshot", "--prune"),
    ("view", "--no-browser"),
    ("view", "--perfetto"),
    ("whatif", "--element"),
    ("analyze", "--explain"),
]

# One paragraph in `bga analyze`'s section names every command that takes `--explain`.
SHARED_EXPLAIN = ("graph", "floors", "replay", "utilisation", "diagnostics", "correlate")


def _names(text, flag):
    return re.search(re.escape(flag) + r"(?![\w-])", text) is not None


def _section(command):
    match = re.search(rf"^## `bga {re.escape(command)}`.*?(?=^## )", CLI_MD, re.S | re.M)
    assert match, f"cli.md has no `## bga {command}` section"
    return match.group(0)


def _stub_commands():
    """Commands whose own section says 'every flag is in `bga X --help`': all their flags belong there."""
    return sorted(
        c
        for c in set(_flags_by_command())
        if re.search(rf"^## `bga {re.escape(c)}`[^\n]*\n+[^\n]*every flag is in", CLI_MD, re.M)
    )


@functools.cache
def _flags_by_command():
    out = {}
    for command in sorted(set(_native_actions()) | set(TOOL_ALIASES)):
        out[command] = {f for f in _known(command)[0] if f.startswith("--") and f not in ("--help", "--schema")}
    return out


def _flags():
    out = {}
    for command, flags in _flags_by_command().items():
        for flag in flags:
            out.setdefault(flag, set()).add(command)
    return out


def test_every_flag_is_named_in_cli_md():
    flags = _flags()
    assert len(flags) >= 120, f"only {len(flags)} flags found; the inventory has moved"
    missing = {f: sorted(c) for f, c in flags.items() if not _names(CLI_MD, f)}
    assert not missing, f"cli.md names none of: {missing}"


def test_a_stub_commands_flags_are_all_in_its_own_section():
    stubs = _stub_commands()
    assert len(stubs) >= 10, f"only {stubs} read as stub sections; the phrase has moved"
    missing = {c: sorted(f for f in _flags_by_command()[c] if not _names(_section(c), f)) for c in stubs}
    missing = {c: v for c, v in missing.items() if v}
    assert not missing, f"not in their own cli.md section: {missing}"


@pytest.mark.parametrize("command", SHARED_EXPLAIN)
def test_explain_is_named_for_each_command_that_takes_it(command):
    assert command in _flags()["--explain"], f"`bga {command}` no longer takes --explain"
    paragraph = next(p for p in _section("analyze").split("\n\n") if p.startswith("`--explain`"))
    assert re.search(rf"`(bga )?{re.escape(command)}`", paragraph), f"`{command}` not in the --explain paragraph"


@pytest.mark.parametrize(("command", "flag"), PINNED)
def test_an_audited_flag_is_in_its_commands_own_section(command, flag):
    assert command in _flags()[flag], f"`bga {command}` has no {flag}"
    assert _names(_section(command), flag), f"{flag} not in cli.md's `bga {command}` section"
