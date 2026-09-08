"""UX-694: identity ignores the line number; the baseline only shrinks.

A temporary package and a temporary baseline, so these mutate the
tree - move lines, add and fix findings, shrink - without touching the
real `tests/quality_baseline.json`.
"""
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "dev_baseline.py"

VIOLATION = ("import subprocess\n\n\n"
             "def f():\n"
             "    cmd = []\n"
             "    subprocess.run(cmd, shell=True)\n")
CLEAN = "def f():\n    return 1\n"
# UX-697: pyright's own kind of finding - a type error basic mode reads
# without any config, so this needs no fixture beyond the module itself.
PYRIGHT_VIOLATION = 'def f() -> int:\n    return "x"\n'
# A module-level `return` - a real error pyright reports with no `rule`
# key at all; ruff's parser accepts the file, so nothing aborts.
PYRIGHT_NO_RULE_VIOLATION = "return 1\n"


def _run(root, baseline, *flags, env=None):
    cmd = [sys.executable, str(TOOL), "--root", str(root), "--paths", "pkg",
           "--baseline", str(baseline), *flags]
    return subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, check=True)


class TestIdentityIgnoresTheLineNumber:
    def test_a_line_inserted_above_still_matches(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, VIOLATION)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _write(module, "\n" + VIOLATION)
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 0, check.stdout


class TestNewAndStaleFindings:
    def test_a_new_finding_is_reported_and_reds(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, CLEAN)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _write(module, VIOLATION)
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 1
        assert "new: ruff S602" in check.stdout

    def test_a_fixed_finding_is_reported_as_stale(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, VIOLATION)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _write(module, CLEAN)
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 1
        assert "stale: ruff S602" in check.stdout


class TestShrinkOnlyShrinks:
    def test_shrink_removes_exactly_the_stale_entry(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, VIOLATION)
        _run(tmp_path, baseline, "--write")
        before = len(_load(baseline)["findings"])
        _write(module, CLEAN)
        shrink = _run(tmp_path, baseline, "--shrink")
        assert shrink.returncode == 0
        after = _load(baseline)["findings"]
        assert len(after) == before - 1
        assert _run(tmp_path, baseline, "--check").returncode == 0

    def test_shrink_never_adds(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, CLEAN)
        _run(tmp_path, baseline, "--write")
        before = _load(baseline)["findings"]
        _write(module, VIOLATION)
        shrink = _run(tmp_path, baseline, "--shrink")
        assert shrink.returncode == 1, shrink.stdout
        assert _load(baseline)["findings"] == before
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 1
        assert "new: ruff S602" in check.stdout

    def test_shrink_removes_stale_and_still_reds_a_new_one(self, tmp_path):
        """The verifier's mutation: `kept` gaining `new` inside the
        stale-removal branch, not just the no-stale one."""
        module = tmp_path / "pkg" / "m.py"
        other = tmp_path / "pkg" / "o.py"
        baseline = tmp_path / "baseline.json"
        _write(module, VIOLATION)
        _run(tmp_path, baseline, "--write")
        _write(module, CLEAN)
        _write(other, VIOLATION)
        shrink = _run(tmp_path, baseline, "--shrink")
        assert shrink.returncode == 1, shrink.stdout
        assert "new: ruff S602" in shrink.stdout
        files = {f["file"] for f in _load(baseline)["findings"]}
        assert files == set(), files


class TestOccurrenceDisambiguates:
    def test_the_same_line_twice_gives_two_identities(self, tmp_path):
        text = ("import subprocess\n\n\n"
                "def f():\n"
                "    subprocess.run(cmd, shell=True)\n\n\n"
                "def g():\n"
                "    subprocess.run(cmd, shell=True)\n")
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, text)
        _run(tmp_path, baseline, "--write")
        entries = [f for f in _load(baseline)["findings"] if f["rule"] == "S602"]
        assert sorted(f["nth"] for f in entries) == [1, 2]


class TestIdentityCollapsesInteriorWhitespace:
    def test_a_reformat_of_the_flagged_line_still_matches(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, VIOLATION)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        reformatted = VIOLATION.replace(
            "subprocess.run(cmd, shell=True)",
            "subprocess.run(cmd,   shell=True)")
        _write(module, reformatted)
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 0, check.stdout


class TestTheGitDiffShrinkGuard:
    def test_a_gained_entry_reds_check(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        other = tmp_path / "pkg" / "o.py"
        baseline = tmp_path / "baseline.json"
        _write(module, VIOLATION)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _git(tmp_path, "init", "-q")
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "add", "-A")
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "commit", "-q", "-m", "baseline")
        _write(other, VIOLATION)
        # `UX-745`: a forced write is *red until it is committed*, and the
        # message says who signed it. It used to be waived outright, which
        # is how a track shipped a growth with every gate green.
        assert _run(tmp_path, baseline, "--write", "--force", "--reason", "UX-1").returncode == 0
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 1, check.stdout
        assert "authorised by UX-1, red until committed" in check.stdout
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "commit", "-q", "-am", "UX-1 adds a finding")
        # Committed, it is HEAD's own line and costs nothing - which is
        # why this is free in CI, where the working file *is* HEAD.
        assert _run(tmp_path, baseline, "--check").returncode == 0
        _write(tmp_path / "pkg" / "p.py", VIOLATION)
        assert _run(tmp_path, baseline, "--write", "--force", "--reason", "UX-1").returncode == 0
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 1, check.stdout
        assert "ruff S602" in check.stdout

    def test_one_forced_line_does_not_waive_an_unrelated_gain(self, tmp_path):
        """`UX-745`, the measured hole: the waiver was the whole file. A
        `--force` whose reason differed from HEAD's returned no gains at
        all, so a line it never touched rode in beside the one it signed
        — and a *repeat* of HEAD's reason was checked more strictly than
        a novel one, which is backwards."""
        baseline = tmp_path / "baseline.json"
        _write(tmp_path / "pkg" / "m.py", VIOLATION)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _git(tmp_path, "init", "-q")
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "add", "-A")
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "commit", "-q", "-m", "baseline")
        _write(tmp_path / "pkg" / "signed.py", VIOLATION)
        assert _run(tmp_path, baseline, "--write", "--force",
                    "--reason", "UX-2").returncode == 0
        # A line the force never saw, hand-added to the list afterwards.
        document = json.loads(baseline.read_text(encoding="utf-8"))
        document["findings"].append({"file": "pkg/smuggled.py", "line": VIOLATION.strip(),
                                     "nth": 1, "rule": "S602", "tool": "ruff"})
        baseline.write_text(json.dumps(document), encoding="utf-8")
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 1, check.stdout
        assert "pkg/smuggled.py" in check.stdout, (
            f"the hand-added line rode in on the force's signature:\n"
            f"{check.stdout}")

    def test_force_without_a_reason_writes_nothing(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, VIOLATION)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        before = baseline.read_bytes()
        _write(tmp_path / "pkg" / "o.py", VIOLATION)
        done = _run(tmp_path, baseline, "--write", "--force")
        assert done.returncode == 2 and "--reason" in done.stdout
        assert baseline.read_bytes() == before

    def test_a_pure_shrink_leaves_check_clean(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, VIOLATION)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _git(tmp_path, "init", "-q")
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "add", "-A")
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "commit", "-q", "-m", "baseline")
        _write(module, CLEAN)
        assert _run(tmp_path, baseline, "--shrink").returncode == 0
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 0, check.stdout


class TestUnknownKeyIsRefused:
    def test_a_forced_by_key_reds_and_names_itself(self, tmp_path):
        """`UX-789`: `"forced_by"` was hand-written, never `--force`'s
        own vocabulary - `load_forced` never read it back."""
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, VIOLATION)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        document = json.loads(baseline.read_text(encoding="utf-8"))
        document["forced_by"] = "UX-712"
        baseline.write_text(json.dumps(document), encoding="utf-8")
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 2, check.stdout
        assert "forced_by" in check.stdout

    def test_a_stray_key_on_a_finding_reds_and_names_itself(self, tmp_path):
        """The same refusal one level down: a finding, not the document,
        carrying a key `identity`/`describe` never read."""
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, VIOLATION)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        document = json.loads(baseline.read_text(encoding="utf-8"))
        document["findings"][0]["line_no"] = 5
        baseline.write_text(json.dumps(document), encoding="utf-8")
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 2, check.stdout
        assert "line_no" in check.stdout


class TestUnparsableFileIsAnError:
    def test_invalid_syntax_exits_2_and_writes_nothing(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, VIOLATION)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        before = baseline.read_text(encoding="utf-8")
        _write(module, "def f(:\n    pass\n")
        shrink = _run(tmp_path, baseline, "--shrink")
        assert shrink.returncode == 2
        assert "m.py" in shrink.stdout
        assert baseline.read_text(encoding="utf-8") == before


class TestPyrightEntersTheSameList:
    def test_a_new_pyright_error_reds_check(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, CLEAN)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _write(module, PYRIGHT_VIOLATION)
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 1, check.stdout
        assert "new: pyright reportReturnType" in check.stdout

    def test_a_broken_pyright_exits_2_and_writes_nothing(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, CLEAN)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        before = baseline.read_text(encoding="utf-8")
        fake_bin = tmp_path / "fakebin"
        fake_pyright = fake_bin / "pyright"
        _write(fake_pyright, "#!/bin/sh\nexit 3\n")
        fake_pyright.chmod(0o755)
        env = dict(os.environ)
        env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
        done = _run(tmp_path, baseline, "--write", env=env)
        assert done.returncode == 2, done.stdout + done.stderr
        assert baseline.read_text(encoding="utf-8") == before

    def test_a_forced_pyright_finding_is_named_by_reason(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, CLEAN)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _git(tmp_path, "init", "-q")
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "add", "-A")
        _git(tmp_path, "-c", "user.email=t@example.com", "-c", "user.name=t",
             "commit", "-q", "-m", "baseline")
        _write(module, PYRIGHT_VIOLATION)
        assert _run(tmp_path, baseline, "--write", "--force",
                    "--reason", "UX-697").returncode == 0
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 1, check.stdout
        assert "authorised by UX-697, red until committed" in check.stdout
        assert "pyright reportReturnType" in check.stdout

    def test_a_rule_less_pyright_error_is_still_new(self, tmp_path):
        module = tmp_path / "pkg" / "m.py"
        baseline = tmp_path / "baseline.json"
        _write(module, CLEAN)
        assert _run(tmp_path, baseline, "--write").returncode == 0
        _write(module, PYRIGHT_NO_RULE_VIOLATION)
        check = _run(tmp_path, baseline, "--check")
        assert check.returncode == 1, check.stdout
        assert "new: pyright noRule" in check.stdout
