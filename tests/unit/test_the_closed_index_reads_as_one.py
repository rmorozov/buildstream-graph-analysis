"""UX-1120: the closed rows live in 128-row chunks and read as one list.

`closed_rows()` in `tools/dev_close_task.py` is the only reader; the
rows it yields are the ones `closed.md` held before the split, in order.
"""

import ast
import hashlib
import pathlib
import re
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_close_task as close_task

#: `UX-1120`: the first 1,039 rows of `closed.md` at d3ef4bf6, the
#: commit before the split, joined by newlines.
PRE_SPLIT_ROWS = 1039
PRE_SPLIT_SHA = "da6945848e500e8eee2738bf798d17fe77991eedf079036e0471b8b6ea6a0e5f"

_TASK = (
    "# UX-9911: a row this guard wrote\n\n"
    "**Priority:** Low | **Status:** \U0001f534 Not Started | "
    "**Serves:** nobody | **Topic:** guards | **Shape:** judgement | "
    "**Reading:** container\n\n## Outcome\n\nmeasured.\n"
)


def _sandbox(tmp_path):
    scenarios = tmp_path / "scenarios"
    shutil.copytree(REPO / "docs/backlog/scenarios", scenarios)
    (scenarios / "UX-9911-a-guard-row.md").write_text(_TASK, encoding="utf-8")
    readme = scenarios / "README.md"
    text = readme.read_text(encoding="utf-8")
    marker = "\n## UX-333"
    assert marker in text, "the open table's end moved"
    row = "| UX-9911 | [a guard row](UX-9911-a-guard-row.md) | guards | Low | — | \U0001f534 |\n"
    readme.write_text(text.replace(marker, "\n" + row + marker, 1), encoding="utf-8")
    return scenarios


def _move(scenarios):
    return subprocess.run(
        [
            sys.executable,
            str(REPO / "tools/dev_close_task.py"),
            "UX-9911",
            "--move",
            "--note",
            "found",
            "--scenarios",
            str(scenarios),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        timeout=120,
    )


def test_the_rows_read_back_as_the_pre_split_rows():
    rows = close_task.closed_rows()
    assert len(rows) >= PRE_SPLIT_ROWS, len(rows)
    head = "\n".join(rows[:PRE_SPLIT_ROWS])
    assert hashlib.sha256(head.encode()).hexdigest() == PRE_SPLIT_SHA


def test_the_chunks_are_the_backlog_after_the_index():
    assert list(close_task.backlog_files()[1:]) == close_task.closed_files()


def test_no_chunk_holds_more_than_its_size():
    for path in close_task.closed_files():
        count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("| UX-"))
        assert count <= close_task.CHUNK_ROWS, (path.name, count)


def test_a_close_appends_to_the_last_chunk(tmp_path):
    scenarios = _sandbox(tmp_path)
    last = close_task.closed_files(scenarios)[-1]
    lines = last.read_text(encoding="utf-8").splitlines(keepends=True)
    rows = [i for i, line in enumerate(lines) if line.startswith("| UX-")]
    if len(rows) >= close_task.CHUNK_ROWS:  # UX-1345: the live chunk can be full; the premise needs room
        del lines[rows[-1]]
        last.write_text("".join(lines), encoding="utf-8")
    before = [p.name for p in close_task.closed_files(scenarios)]
    done = _move(scenarios)
    assert done.returncode == 0, done.stdout + done.stderr
    after = [p.name for p in close_task.closed_files(scenarios)]
    assert after == before, "a close with room in the last chunk opened one"
    assert close_task.closed_rows(scenarios)[-1].startswith("| UX-9911 |")


def test_the_129th_row_opens_a_new_chunk(tmp_path):
    scenarios = _sandbox(tmp_path)
    last = close_task.closed_files(scenarios)[-1]
    text = last.read_text(encoding="utf-8")
    room = close_task.CHUNK_ROWS - sum(1 for line in text.splitlines() if line.startswith("| UX-"))
    filler = "".join(f"| UX-9{n:03d} | filler | Low | — | \U0001f7e2 Done | x |\n" for n in range(room))
    last.write_text(text + filler, encoding="utf-8")
    done = _move(scenarios)
    assert done.returncode == 0, done.stdout + done.stderr
    files = close_task.closed_files(scenarios)
    assert files[-1].name == f"{int(last.stem) + 1:04d}.md"
    assert close_task.closed_rows(scenarios)[-1].startswith("| UX-9911 |")
    assert "| UX-9911 |" not in last.read_text(encoding="utf-8")


def _opens_closed(tree):
    """A read call, or a module-level binding, that names a closed path."""

    def names(node):
        return any(
            isinstance(c, ast.Constant)
            and isinstance(c.value, str)
            and ("closed.md" in c.value or c.value == "closed" or "scenarios/closed" in c.value)
            for c in ast.walk(node)
        )

    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name in ("read_text", "read_bytes", "open") and names(node):
                hits.append(node.lineno)
    hits += [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and node.value is not None and names(node.value)
    ]
    return sorted(set(hits))


def test_no_reader_outside_the_tool_opens_a_closed_path():
    tracked = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.split()
    skip = {"tools/dev_close_task.py", "tests/unit/test_the_closed_index_reads_as_one.py"}
    bad = []
    for name in tracked:
        path = REPO / name
        if name in skip or not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        bad += [f"{name}:{line}" for line in _opens_closed(tree)]
    assert bad == [], f"read closed rows without closed_rows(): {bad}"


def test_the_guard_sees_a_direct_read():
    tree = ast.parse('P = REPO / "docs/backlog/scenarios/closed.md"\nx = (d / "closed.md").read_text()\n')
    assert _opens_closed(tree) == [1, 2]


def test_the_guard_sees_a_function_local_read():
    tree = ast.parse('def rows():\n    p = SCENARIOS / "closed.md"\n    return p.read_text()\n')
    assert _opens_closed(tree) == [2]


def test_an_appended_row_links_from_the_chunks_directory(tmp_path):
    scenarios = _sandbox(tmp_path)
    done = _move(scenarios)
    assert done.returncode == 0, done.stdout + done.stderr
    chunk = close_task.closed_files(scenarios)[-1]
    row = next(line for line in chunk.read_text(encoding="utf-8").splitlines() if line.startswith("| UX-9911 |"))
    targets = re.findall(r"\]\(([^)\s]+)\)", row)
    assert targets, row
    for target in targets:
        assert target.startswith("../"), target
        assert (chunk.parent / target).exists(), target
