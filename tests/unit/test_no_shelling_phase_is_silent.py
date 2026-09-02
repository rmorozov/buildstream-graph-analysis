"""UX-519: the artifact-contents phase drew nothing, and nothing said so.

Measured on `examples/06-macro-micro-optimization`, 11 elements, all
cached, `bst` 2.7.0:

```text
read_artifact_contents: 2.79s over 11 elements, 8413 paths
stderr bytes drawn: 0
```

`UX-518` made the phase one `bst` invocation per 200 elements, so the
unit that can be counted is the batch. The threshold this file states:
**a loop that shells out to `bst` costs 1.34s median per invocation**
(`UX-518`'s measurement), so any such loop passes 10s at eight
iterations - which is why the enumeration below is "a loop that spawns
a subprocess", not a list of phase names somebody maintains.

`test_progress_never_touches_the_pipe.py` already holds that *some*
`progress.ticker(` call appears per module. That guard passes on a
ticker created and never fed; these read what the phase draws.
"""
import ast
import io
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import progress                                       # noqa: E402
from tools import bst_native_build_tracer as tracer            # noqa: E402

#: The capture-side modules that drive `bst`. `bga/run_store.py` walks a
#: directory tree and spawns nothing, so it is not in this population.
SHELLING_MODULES = ("tools/bst_native_build_tracer.py",
                    "tools/bst_show_to_graph.py")


def _calls(node):
    for inner in ast.walk(node):
        if isinstance(inner, ast.Call):
            yield ast.unparse(inner.func)


def _spawners(functions):
    """Every function that reaches `subprocess`, directly or through
    another function in the same module. Measured: a scan for
    `subprocess.` written *inside the loop body* finds zero phases here,
    because `read_artifact_contents` calls `_list_contents` and
    `_list_contents` calls `bst`."""
    found = set()
    growing = True
    while growing:
        growing = False
        for name, node in functions.items():
            if name in found:
                continue
            if any(c.startswith("subprocess.") or c in found
                   for c in _calls(node)):
                found.add(name)
                growing = True
    return found


def loops_that_shell_out(path):
    """`{function name: line}` for every function whose *loop body*
    spawns a subprocess - the shape that costs one `bst` startup per
    iteration."""
    tree = ast.parse((REPO / path).read_text(encoding="utf-8"))
    functions = {n.name: n for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef)}
    spawners = _spawners(functions)
    found = {}
    for name, node in functions.items():
        loops = [n for n in ast.walk(node) if isinstance(n, (ast.For, ast.While))]
        if any(c.startswith("subprocess.") or c in spawners
               for loop in loops for c in _calls(loop)):
            found[name] = node.lineno
    return found


def _feeds_a_ticker(path, function):
    """The function binds a ticker *and* advances it from inside a loop.

    A ticker constructed and never stepped draws nothing, which is the
    state this item found the phase in."""
    tree = ast.parse((REPO / path).read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name == function)
    if not any("progress.ticker" in c for c in _calls(node)):
        return False
    loops = [n for n in ast.walk(node) if isinstance(n, (ast.For, ast.While))]
    return any(c.endswith(".step") or c.endswith(".note")
               for loop in loops for c in _calls(loop))


class TestEveryLoopThatShellsOutIsNarrated:
    """The coverage claim, and the reason it is not a list of labels: a
    phase added next round arrives in this population by construction."""

    @pytest.mark.parametrize("module", SHELLING_MODULES)
    def test_it_feeds_a_ticker(self, module):
        silent = [f"{module}:{line} {name}"
                  for name, line in sorted(loops_that_shell_out(module).items())
                  if not _feeds_a_ticker(module, name)]
        assert not silent, (
            "one `bst` invocation is 1.34s, so a loop over elements passes "
            "10s at eight of them - and these draw nothing:\n  "
            + "\n  ".join(silent))

    def test_the_detector_sees_a_phase_shaped_like_the_real_one(self, tmp_path):
        """The clause that keeps the one above from passing vacuously: an
        enumeration that found nothing would be green and mean nothing.

        The subject is a written-down module, not the tracer, so the two
        answers stay distinguishable - and it is written the way the real
        phase is, with the loop calling a helper and the helper calling
        `bst`, because a scan of loop bodies for `subprocess.` itself
        finds nothing in this repository."""
        module = tmp_path / "sample.py"
        module.write_text(
            "import subprocess\n"
            "def _one(name):\n"
            "    return subprocess.run(['bst', 'x', name])\n"
            "def silent(names):\n"
            "    for name in names:\n"
            "        _one(name)\n"
            "def narrated(names):\n"
            "    tick = progress.ticker('x', total=len(names))\n"
            "    for index, name in enumerate(names, 1):\n"
            "        tick.step(index)\n"
            "        _one(name)\n",
            encoding="utf-8")
        found = loops_that_shell_out(module)
        assert set(found) == {"silent", "narrated"}, found
        assert not _feeds_a_ticker(module, "silent")
        assert _feeds_a_ticker(module, "narrated")


class _Bst:
    """`bst artifact list-contents`, without a BuildStream. Same shape as
    `test_the_contents_read_is_one_call.py`'s double."""

    def __init__(self, unresolvable=()):
        self.unresolvable = set(unresolvable)
        self.calls = []

    def __call__(self, argv, cwd=None, capture_output=None, text=None):
        asked = argv[3:]
        self.calls.append(asked)
        if any(name in self.unresolvable for name in asked):
            return subprocess.CompletedProcess(argv, 255, stdout="", stderr="")
        out = []
        for name in asked:
            out += [f"  {name}:", "\tusr/lib/libx.a"]
        return subprocess.CompletedProcess(argv, 0, stdout="\n".join(out) + "\n",
                                           stderr="")


class _FakeTTY(io.StringIO):
    def isatty(self):
        return True


def _frames(text):
    """The drawn states, in order, with the padding and the erase
    removed - what a terminal would have shown one after another."""
    return [f.strip() for f in text.split("\r") if f.strip()]


def _draw(monkeypatch, elements, unresolvable=(), tty=True):
    bst = _Bst(unresolvable)
    stream = _FakeTTY() if tty else io.StringIO()
    monkeypatch.setattr(tracer.subprocess, "run", bst)
    monkeypatch.setattr(sys, "stderr", stream)
    # Every `step` draws: the 0.1s redraw throttle is a property of the
    # terminal, and a double answers in microseconds, so without this
    # the phase's later batches are indistinguishable from unfed.
    monkeypatch.setattr(progress, "_MIN_INTERVAL_S", 0.0)
    tracer.read_artifact_contents("/project", elements)
    return stream.getvalue()


class TestTheLineCountsTheBatchesItMakes:
    def test_a_batch_per_frame(self, monkeypatch):
        """500 elements at a 200-element chunk is three `bst` calls, so
        the line goes 1/3, 2/3, 3/3 - not 1/500."""
        drawn = _draw(monkeypatch, [f"e{n}.bst" for n in range(500)])
        assert _frames(drawn) == ["artifact contents: 1/3",
                                  "artifact contents: 2/3",
                                  "artifact contents: 3/3"], _frames(drawn)

    def test_the_retry_says_it_is_retrying(self, monkeypatch):
        """A failed group is one `bst` call per element (`UX-518`), which
        is the slowest this phase gets. The batch counter cannot move
        during it, so the line says what it is doing instead."""
        drawn = _draw(monkeypatch, ["a.bst", "gone.bst", "c.bst"],
                      unresolvable={"gone.bst"})
        assert [f for f in _frames(drawn) if "retry" in f] == [
            "artifact contents: 1/1 retry 1/3",
            "artifact contents: 1/1 retry 2/3",
            "artifact contents: 1/1 retry 3/3"], _frames(drawn)

    def test_nothing_reaches_a_pipe(self, monkeypatch):
        """`UX-183`'s rule, for this line: a redirected stderr is a log
        file, and a carriage return in one is somebody's cleanup job."""
        drawn = _draw(monkeypatch, [f"e{n}.bst" for n in range(500)],
                      tty=False)
        assert drawn == "", repr(drawn)


if __name__ == "__main__":                       # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
