"""UX-1119: docstrings follow the Google convention through the baseline
(`bga/`, `tools/`, `.claude/hooks/`; `tests/` stays out). D205/D209/D212 are
off: 1,226 layout hits that conflict with the house register."""
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import dev_baseline

MISSING_ARG = (
    "def f(a, b):\n"
    '    """Add.\n\n'
    "    Args:\n"
    "        a: the first.\n"
    '    """\n'
    "    return a + b\n")


def _section():
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    return text.split("[tool.ruff.lint.pydocstyle]")[1].split("\n[")[0]


def _check(root, source):
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "m.py").write_text(source, encoding="utf-8")
    (root / "pyright.json").write_text("[]", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        "[tool.ruff.lint.pydocstyle]" + _section(), encoding="utf-8")
    (root / "baseline.json").write_text(
        '{"families": [], "findings": []}\n', encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(REPO / "tools" / "dev_baseline.py"), "--check",
         "--root", str(root), "--paths", "pkg", "--baseline",
         str(root / "baseline.json"), "--pyright-from", str(root / "pyright.json")],
        capture_output=True, text=True, check=False)


class TestDocstringsFollowOneConvention:
    def test_pyproject_names_google(self):
        assert re.search(r'^convention = "google"$', _section(), re.M)

    def test_the_baseline_reads_the_docstring_families(self):
        assert {"D2", "D3", "D4"} <= set(dev_baseline.FAMILIES)
        assert set(dev_baseline.IGNORED) == {"D205", "D209", "D212"}

    def test_the_committed_baseline_carries_no_layout_rule_it_ignores(self):
        doc = json.loads((REPO / "tests" / "quality_baseline.json").read_text())
        rules = {f["rule"] for f in doc["findings"]}
        assert not rules & set(dev_baseline.IGNORED)

    def test_an_args_section_missing_a_parameter_is_red(self, tmp_path):
        done = _check(tmp_path, MISSING_ARG)
        assert done.returncode == 1, done.stdout + done.stderr
        assert "new: ruff D417" in done.stdout

    def test_the_same_function_documented_whole_is_clean(self, tmp_path):
        done = _check(tmp_path, MISSING_ARG.replace(
            "        a: the first.\n",
            "        a: the first.\n        b: the second.\n"))
        assert done.returncode == 0, done.stdout + done.stderr
