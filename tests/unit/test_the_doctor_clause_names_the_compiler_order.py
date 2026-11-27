"""UX-1380: `cli.md`'s `c-compiler` clause names the compilers `native_prebuilt.compiler()` tries, in its order."""

import pathlib
import re

from tools.native_trace import prebuilt

CLI_MD = pathlib.Path(__file__).resolve().parents[2] / "docs/guides/cli.md"


def _clause() -> str:
    text = CLI_MD.read_text(encoding="utf-8")
    match = re.search(r"`c-compiler` resolves ([^.]*?), exactly as `compile_hook` does", text)
    assert match, "cli.md has no `c-compiler` resolves ... exactly as `compile_hook` does clause"
    return match.group(1)


def test_the_clause_names_the_candidates_in_the_functions_order():
    names = re.findall(r"`([A-Za-z$]+)`", _clause())
    assert [n for n in names if n in prebuilt.CANDIDATES] == list(prebuilt.CANDIDATES)
    assert [n for n in names if n not in prebuilt.CANDIDATES] == ["$CC", "PATH"]


def test_the_clause_puts_cc_the_variable_first():
    assert _clause().lstrip().startswith("`$CC`")


def test_the_clause_states_the_prebuilt_case():
    text = CLI_MD.read_text(encoding="utf-8")
    assert "match their stamp" in text and "answers `ok` with no compiler" in text
