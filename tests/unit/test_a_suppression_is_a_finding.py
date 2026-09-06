"""UX-705: silencing a check is counted, so a burn-down cannot fake one.

The baseline (`UX-694`) is the number a delegated burn-down track is
judged by. Until this, `# noqa` was invisible to it, so a batch of
twenty findings closed by twenty annotations read exactly like twenty
fixes. The census makes a suppression a finding of its own: still
allowed, never free.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import dev_baseline as tool


def _census(tmp_path, files):
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (tmp_path / "pyproject.toml").touch()
    return tool.suppression_findings(tmp_path, ["src"])


class TestWhatCounts:
    def test_a_noqa_on_a_code_line_counts(self, tmp_path):
        found = _census(tmp_path, {"src/a.py": "import os  # noqa: S607\n"})
        assert [f["rule"] for f in found] == ["SUPPRESSION"], found

    def test_a_type_ignore_counts(self, tmp_path):
        found = _census(tmp_path, {"src/a.py": "x = 1  # type: ignore\n"})
        assert len(found) == 1, found

    def test_an_eslint_disable_counts(self, tmp_path):
        found = _census(tmp_path, {"src/a.js": "/* eslint-disable eqeqeq */\n"})
        assert len(found) == 1, found


class TestWhatDoesNot:
    """The three shapes that made the first census read itself."""

    def test_a_directive_inside_a_string_is_not_one(self, tmp_path):
        """The census's own pattern table is `re.compile(r"eslint-
        disable")`, and a text scan counted it."""
        found = _census(tmp_path, {"src/a.py": 'P = "# noqa: S607"\n'})
        assert found == [], found

    def test_a_directive_in_prose_is_not_one(self, tmp_path):
        """A comment-only line suppresses nothing - ruff reports an
        unused `noqa` there rather than honouring it. This file's own
        docstring quotes directives, and so did the census's."""
        found = _census(tmp_path, {"src/a.py": "# see: noqa is a directive\n"
                                               "# noqa: S607\n"})
        assert found == [], found

    def test_a_docstring_mentioning_one_is_not_one(self, tmp_path):
        found = _census(tmp_path, {"src/a.py": '"""Uses # noqa: F401."""\n'})
        assert found == [], found


class TestPerFileIgnores:
    def test_a_per_file_ignore_counts(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "pyproject.toml").write_text(
            '[tool.ruff.lint.per-file-ignores]\n"tools/**" = ["T201"]\n',
            encoding="utf-8")
        found = tool.suppression_findings(tmp_path, ["src"])
        assert len(found) == 1, found

    def test_the_same_shape_elsewhere_in_the_file_is_not_one(self, tmp_path):
        """`"key" = [...]` is ordinary TOML. Only the ignores table
        silences anything, so only it is read."""
        (tmp_path / "src").mkdir()
        (tmp_path / "pyproject.toml").write_text(
            '[project]\n"name" = ["bga"]\n', encoding="utf-8")
        assert tool.suppression_findings(tmp_path, ["src"]) == []


class TestTheRepoIsRecorded:
    def test_the_committed_baseline_carries_the_census(self):
        """Otherwise the guard runs and the ledger does not hold it, so
        `--check` has nothing to compare a new one against."""
        import json
        recorded = json.loads(
            (REPO / "tests/quality_baseline.json").read_text(encoding="utf-8"))
        rules = {f["rule"] for f in recorded["findings"]}
        assert "SUPPRESSION" in rules, (
            "the baseline records no suppression - run "
            "dev_baseline.py --write --force --reason UX-705")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
