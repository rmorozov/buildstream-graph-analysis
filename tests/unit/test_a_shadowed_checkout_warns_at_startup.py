"""A track's worktree and the editable install can disagree (UX-728).

`python -m bga.cli` resolves `bga` to whatever `sys.path` puts first,
which is the session's checkout unless cwd itself is the worktree. The
three cases below are three clauses of `_maybe_warn_wrong_checkout`:
warn on a real mismatch, stay silent when cwd and import agree, stay
silent when cwd is not a checkout of this repository at all.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Forces the module under test to load from REPO regardless of cwd, so
# a fixture cwd that also carries the marker files (needed to look like
# a checkout) cannot shadow the real package with its own empty stub.
_SCRIPT = (
    "import sys; sys.path.insert(0, sys.argv[1]); "
    "import bga.cli as c; sys.exit(c.main(['--version']))"
)


def _run_from(cwd: Path) -> str:
    proc = subprocess.run(
        [sys.executable, "-c", _SCRIPT, str(REPO)],
        cwd=cwd, capture_output=True, text=True, timeout=30,
    )
    assert proc.stdout.strip() == "bga 0.4.1", proc.stdout + proc.stderr
    return proc.stderr


def _make_fake_checkout(root: Path) -> Path:
    (root / "bga").mkdir(parents=True)
    (root / "bga" / "__init__.py").write_text("")
    (root / "pyproject.toml").write_text('[project]\nname = "bga"\n')
    return root


def test_warns_when_cwd_is_a_different_checkout(tmp_path):
    fake = _make_fake_checkout(tmp_path / "worktree")
    stderr = _run_from(fake)

    assert "UX-728" in stderr, stderr
    assert str(REPO) in stderr, stderr
    assert str(fake.resolve()) in stderr, stderr


def test_silent_when_cwd_and_import_agree():
    stderr = _run_from(REPO)

    assert stderr == "", stderr


def test_silent_when_cwd_is_not_a_checkout_at_all(tmp_path):
    stderr = _run_from(tmp_path)

    assert stderr == "", stderr
