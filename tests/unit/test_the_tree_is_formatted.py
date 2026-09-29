"""UX-1118: layout is `ruff format`'s, and the one commit that applied it is blame-ignored.

`dev_baseline.py --rekey` carried the finding baseline across that
commit: it accepts only a rename - equal `(tool, rule, file)` multisets -
and pairs old to new in source order, so a forced reason stays on its line.
"""

import argparse
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_baseline

FORMATTED = ("bga", "tools", "tests", ".claude/hooks")


def test_the_tree_is_formatted():
    run = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", *FORMATTED],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, f"`ruff format` would change the tree:\n{run.stdout}{run.stderr}"


def test_the_ignore_revs_name_commits_that_exist():
    lines = (REPO / ".git-blame-ignore-revs").read_text(encoding="utf-8").splitlines()
    shas = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    assert shas, "no revision to ignore"
    for sha in shas:
        assert re.fullmatch(r"[0-9a-f]{40}", sha), f"not a full sha: {sha!r}"
        found = subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", f"{sha}^{{commit}}"], check=False)
        assert found.returncode == 0, f"{sha} is not a commit in this repository"


def finding(rule, line, nth=1, file="pkg/m.py"):
    return {"tool": "ruff", "rule": rule, "file": file, "line": line, "nth": nth}


def rekey(tmp_path, current, baseline, forced=()):
    path = tmp_path / "baseline.json"
    dev_baseline.write_baseline(path, baseline, dev_baseline.FAMILIES, forced_batches=forced)
    before = path.read_text(encoding="utf-8")
    args = argparse.Namespace(baseline=path, root=tmp_path)
    code = dev_baseline.do_rekey(args, current, dev_baseline.load_baseline(path))
    return code, before, json.loads(path.read_text(encoding="utf-8"))


def test_a_rename_is_rekeyed_and_keeps_its_forced_reason(tmp_path):
    old = finding("S603", "out = subprocess.run(cmd, check=False)")
    new = finding("S603", "out = subprocess.run(")
    code, _, written = rekey(tmp_path, [new], [old], forced=[("UX-1", {dev_baseline.identity(old)})])
    assert code == 0
    assert written["findings"] == [new]
    assert written["forced"] == [{"reason": "UX-1", "identities": [list(dev_baseline.identity(new))]}]


def test_an_extra_finding_is_refused_and_nothing_is_written(tmp_path):
    old = finding("S603", "out = subprocess.run(cmd, check=False)")
    renamed = finding("S603", "out = subprocess.run(")
    extra = finding("S603", "again = subprocess.run(")
    code, before, _ = rekey(tmp_path, [renamed, extra], [old])
    assert code == 1
    assert (tmp_path / "baseline.json").read_text(encoding="utf-8") == before


def test_pairs_follow_the_source_order_not_the_text(tmp_path):
    """`z` sits above `a` in HEAD's file; the forced reason must follow `z`."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "m.py").write_text("z = run(1, 2)\na = run(3, 4)\n", encoding="utf-8")
    for cmd in (
        ["init", "-q"],
        ["add", "pkg/m.py"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", "commit", "-qm", "x"],
    ):
        subprocess.run(["git", "-C", str(tmp_path), *cmd], check=True)
    z_old, a_old = finding("S603", "z = run(1, 2)"), finding("S603", "a = run(3, 4)")
    z_new, a_new = finding("S603", "z = run("), finding("S603", "a = run(")
    code, _, written = rekey(
        tmp_path, [z_new, a_new], [a_old, z_old], forced=[("UX-1", {dev_baseline.identity(z_old)})]
    )
    assert code == 0
    assert written["forced"][0]["identities"] == [list(dev_baseline.identity(z_new))]
