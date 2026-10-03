"""UX-1303: cli.md's `.bga/config` section has a row for every key the code reads from that file."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEADING = "## `.bga/config`"
IMPORT = re.compile(r"run_store\.read_config|from\s+(?:bga\.|\.)?run_store\s+import\s+[^\n]*read_config")


def _section() -> str:
    text = (ROOT / "docs/guides/cli.md").read_text(encoding="utf-8")
    assert HEADING in text, "cli.md lost its .bga/config section"
    return text.split(HEADING, 1)[1].split("\n## ", 1)[0]


def _called(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) == name


def _const(arg: ast.AST, consts: dict):
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    return consts.get(arg.id) if isinstance(arg, ast.Name) else None


def _keys_in(path: Path) -> set:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    consts = {
        target.id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    # names bound from a read_config(...) call, plus the snapshot's `config`, which write_config persists
    bound = {"config"} if "write_config" in source else set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _called(node.value, "read_config"):
            bound |= {t.id for t in node.targets if isinstance(t, ast.Name)}

    def reads(receiver: ast.AST) -> bool:
        return _called(receiver, "read_config") or (isinstance(receiver, ast.Name) and receiver.id in bound)

    keys = set()
    for node in ast.walk(tree):
        if _called(node, "get") and node.args and reads(node.func.value):
            keys.add(_const(node.args[0], consts))
        if isinstance(node, ast.Subscript) and reads(node.value):
            keys.add(_const(node.slice, consts))
        if isinstance(node, ast.FunctionDef) and any(_called(n, "write_config") for n in ast.walk(node)):
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "defaults" for t in inner.targets)
                    and isinstance(inner.value, ast.Dict)
                ):
                    keys |= {k.value for k in inner.value.keys if isinstance(k, ast.Constant)}
    keys.discard(None)
    return keys


def _keys_the_code_reads() -> set:
    keys = set()
    for path in [*(ROOT / "bga").rglob("*.py"), *(ROOT / "tools").rglob("*.py")]:
        if IMPORT.search(path.read_text(encoding="utf-8")) or path.name == "run_store.py":
            keys |= _keys_in(path)
    return keys


def test_the_collector_finds_the_keys_known_to_be_read():
    assert {"builds_per_day", "public_junctions", "trace_opens", "trace_spine"} <= _keys_the_code_reads()


def test_every_key_the_code_reads_has_a_row():
    rows = set(re.findall(r"^\| `([a-z_]+)` \|", _section(), flags=re.M))
    missing = _keys_the_code_reads() - rows
    assert not missing, f"cli.md's .bga/config section misses: {sorted(missing)}"


def test_no_row_names_a_key_nothing_reads():
    rows = set(re.findall(r"^\| `([a-z_]+)` \|", _section(), flags=re.M))
    assert rows <= _keys_the_code_reads()
