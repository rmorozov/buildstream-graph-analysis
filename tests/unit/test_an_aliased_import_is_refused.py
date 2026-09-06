"""`UX-721`: the export flattens the modules into one scope, so an
aliased import names nothing and the section dies in `UX-335`'s banner.

`UX-669` hit it live - `import { heading as headingOf }` rendered the
whole decision panel as `ReferenceError: headingOf is not defined` -
and renamed three locals to get out of it. The refusal is what tells
the next round it must.
"""
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.bga_view import _aliased_imports, _inline_module, _module_order

ALIASED = 'import { childNode, heading as headingOf, hintsOf } from "./format.js";\n'
PLAIN = 'import { childNode, heading, hintsOf } from "./format.js";\n'


class TestTheAliasIsRead:
    """The parse, before anything acts on it."""

    def test_a_renamed_binding_is_found_with_both_of_its_names(self):
        assert _aliased_imports(ALIASED) == [("heading", "headingOf")]

    def test_an_unaliased_import_yields_nothing(self):
        assert _aliased_imports(PLAIN) == []

    def test_a_name_merely_containing_as_is_not_a_rename(self):
        assert _aliased_imports('import { hasClass, asides } from "./a.js";\n') == []


class TestTheExportRefusesOne:
    """The bundler's own path, on a module written to a temporary
    asset directory - the real tree carries no alias, which is the
    state this refusal protects."""

    def _asset(self, tmp_path, monkeypatch, source):
        (tmp_path / "mod.js").write_text(source, encoding="utf-8")
        monkeypatch.setattr("tools.bga_view.ASSET_DIR", str(tmp_path))
        return "mod.js"

    def test_an_aliased_module_raises_naming_the_module_and_the_alias(
            self, tmp_path, monkeypatch):
        name = self._asset(tmp_path, monkeypatch, ALIASED + "export const q = 1;\n")
        with pytest.raises(RuntimeError) as raised:
            _inline_module(name)
        message = str(raised.value)
        assert "mod.js" in message
        assert "heading as headingOf" in message

    def test_the_same_module_unaliased_inlines(self, tmp_path, monkeypatch):
        name = self._asset(tmp_path, monkeypatch, PLAIN + "export const q = 1;\n")
        inlined = _inline_module(name)
        assert "import" not in inlined
        assert "const q = 1;" in inlined


class TestTheTreeItProtects:
    """Every module the export actually inlines, read - a clause that
    only tested a temporary file would pass on a tree that had drifted."""

    def test_no_module_the_export_inlines_renames_an_import(self):
        """The population is asserted in the same clause that reads it:
        an empty walk passes the `== {}` half on its own, which is the
        vacuity a mutation of this file found."""
        bundle = _module_order("app.js")
        offenders = {
            name: _aliased_imports(
                (REPO / "bga/viewer" / name).read_text(encoding="utf-8"))
            for name in bundle}
        assert len(offenders) == len(bundle) >= 20
        assert {"decision.js", "format.js"} <= set(offenders)
        assert {n: a for n, a in offenders.items() if a} == {}


class TestTheRefusalReachesTheCaller:
    """`UX-725`'s lesson: a refusal that exits zero and writes a file
    anyway is not a refusal."""

    def test_the_cli_exits_non_zero_and_writes_nothing(self, tmp_path):
        viewer = tmp_path / "viewer"
        viewer.mkdir()
        for module in _module_order("app.js"):
            source = (REPO / "bga/viewer" / module).read_text(encoding="utf-8")
            if module == "decision.js":
                source = source.replace(PLAIN.rstrip("\n"), ALIASED.rstrip("\n"), 1)
                assert "headingOf" in source, "the alias was not planted"
            (viewer / module).write_text(source, encoding="utf-8")
        script = (f"import sys; sys.path.insert(0, {str(REPO)!r});\n"
                  f"import tools.bga_view as v; v.ASSET_DIR = {str(viewer)!r};\n"
                  "v._inline_module('decision.js')\n")
        done = subprocess.run([sys.executable, "-c", script],
                              capture_output=True, text=True)
        assert done.returncode != 0
        assert "decision.js" in done.stderr and "headingOf" in done.stderr
