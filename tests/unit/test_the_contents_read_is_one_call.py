"""UX-518: `read_artifact_contents` asks for its elements together.

The cost of `bst artifact list-contents` is per *invocation*, not per
element. `examples/06-macro-micro-optimization`, 11 elements, all
cached, `bst` 2.7.0, same container, same minute, warm-up discarded:

```text
A. one call per element (11 calls): total 14.82s, median per call 1.34s
B. one call, all 11 elements:      1.59 / 1.59 / 1.61s, median 1.59s
                                                   ratio A/B = 9.3x
```

Eleven elements in one call cost what one costs. On the published
`captures/fdsdk/953683fb-incremental-b4j4-33302016575`, whose own
`graph.json` has 124 distinct build-dependency successors, that is ~2.8
minutes of BuildStream startups against ~1.6 seconds.

The function had **no guard at all** before this file, so the
"unchanged result" clause below compares the two shapes against each
other rather than against a stored expectation.

The batching is not free of a contract question, and the measurement
that settles it is the failure mode:

```text
core.bst all.bst                    rc=0    headings=['core.bst:', 'all.bst:']
core.bst nope-does-not-exist.bst    rc=255  stdout empty
```

A group is all-or-nothing. Since an unreadable element must map to an
**empty set the caller reads as "unknown"**, a naive batch would be
safe and lossy - it would downgrade every element sharing a group with
one bad name. Hence the per-element retry, and hence the clause that
holds it.
"""
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import bst_native_build_tracer as tracer            # noqa: E402


class _Bst:
    """A `bst artifact list-contents` double that records its calls.

    `staged` maps element to its artifact's paths; an element absent
    from it is one `bst` cannot resolve, which is the case that exits
    non-zero and takes its whole group down.
    """

    def __init__(self, staged, unresolvable=()):
        self.staged = staged
        self.unresolvable = set(unresolvable)
        self.calls = []

    def __call__(self, argv, cwd=None, capture_output=None, text=None):
        assert argv[:3] == ["bst", "artifact", "list-contents"], argv
        asked = argv[3:]
        self.calls.append(asked)
        if any(name in self.unresolvable for name in asked):
            return subprocess.CompletedProcess(
                argv, 255, stdout="",
                stderr="Could not find element ... in elements directory")
        out = []
        for name in asked:
            out.append(f"  {name}:")
            out += [f"\t{path}" for path in sorted(self.staged.get(name, ()))]
        return subprocess.CompletedProcess(argv, 0, stdout="\n".join(out) + "\n",
                                           stderr="")


STAGED = {
    "core.bst": {"usr/include/core.hpp", "usr/lib/libcore.a"},
    "lib-a.bst": {"usr/include/lib-a.hpp"},
    "codegen.bst": {"usr/include/codegen.hpp"},
}


def _read(monkeypatch, bst, elements):
    monkeypatch.setattr(tracer.subprocess, "run", bst)
    return tracer.read_artifact_contents("/project", elements)


class TestTheElementsAreAskedForTogether:
    """Input classes: none, one, many - and the chunk boundary."""

    def test_no_elements_spawns_nothing(self, monkeypatch):
        bst = _Bst(STAGED)
        assert _read(monkeypatch, bst, []) == {}
        assert bst.calls == [], "an empty set still shelled out"

    def test_one_element_is_one_call(self, monkeypatch):
        bst = _Bst(STAGED)
        got = _read(monkeypatch, bst, ["core.bst"])
        assert bst.calls == [["core.bst"]]
        assert got == {"core.bst": {"/usr/include/core.hpp", "/usr/lib/libcore.a"}}

    def test_many_elements_are_one_call(self, monkeypatch):
        """The whole point. Three elements, one BuildStream startup."""
        bst = _Bst(STAGED)
        elements = ["core.bst", "lib-a.bst", "codegen.bst"]
        got = _read(monkeypatch, bst, elements)
        assert bst.calls == [elements], (
            f"{len(bst.calls)} call(s) for 3 elements - the cost is per "
            f"invocation, so this is the 10.8x this item measured")
        assert got == {
            "core.bst": {"/usr/include/core.hpp", "/usr/lib/libcore.a"},
            "lib-a.bst": {"/usr/include/lib-a.hpp"},
            "codegen.bst": {"/usr/include/codegen.hpp"},
        }

    def test_the_batched_result_equals_the_per_element_result(self, monkeypatch):
        """The claim the speed-up must not cost: same answer, fewer
        calls. Read once as a batch, then once per element, and compare
        - which is the assertion this function never had."""
        elements = sorted(STAGED)
        batched = _read(monkeypatch, _Bst(STAGED), elements)
        alone = {}
        for element in elements:
            alone.update(_read(monkeypatch, _Bst(STAGED), [element]))
        assert batched == alone

    def test_a_long_list_is_chunked_rather_than_one_enormous_call(
            self, monkeypatch):
        """`LIST_CONTENTS_CHUNK` bounds what is held in memory. The
        invocation count still collapses - 500 elements is 3 calls, not
        500 - which is the property that matters."""
        elements = [f"e{n}.bst" for n in range(500)]
        bst = _Bst({name: {"usr/x"} for name in elements})
        got = _read(monkeypatch, bst, elements)
        assert len(bst.calls) == 3, [len(c) for c in bst.calls]
        assert all(len(call) <= tracer.LIST_CONTENTS_CHUNK for call in bst.calls)
        assert set(got) == set(elements)


class TestAHeadingIsTheRecordSeparator:
    def test_paths_are_attributed_to_their_own_element(self, monkeypatch):
        """The parser used to *discard* the `<element>:` heading, which
        was right with one element per call and loses everything with
        many. A batch that merged the paths would pass every clause
        above and be wrong here."""
        bst = _Bst(STAGED)
        got = _read(monkeypatch, bst, ["core.bst", "lib-a.bst"])
        assert "/usr/include/lib-a.hpp" not in got["core.bst"]
        assert "/usr/include/core.hpp" not in got["lib-a.bst"]

    def test_a_staged_path_ending_in_a_colon_does_not_open_a_record(
            self, monkeypatch):
        """A heading is recognised by naming an element that was asked
        for, not by its trailing colon - so a file called `weird:` stays
        a file."""
        staged = {"core.bst": {"usr/share/weird:", "usr/lib/libcore.a"}}
        bst = _Bst(staged)
        got = _read(monkeypatch, bst, ["core.bst"])
        assert got["core.bst"] == {"/usr/share/weird:", "/usr/lib/libcore.a"}


class TestAFailedGroupIsRetriedElementByElement:
    """`UX-518`'s contract clause. Measured: one unresolvable name exits
    255 with an empty stdout and takes its whole group. Today's
    per-element loop lost only the bad element, and that must not
    regress - an element wrongly mapped to an empty set reads as
    "staged nothing", which makes every dependency look unused."""

    def test_a_bad_name_does_not_cost_its_group(self, monkeypatch):
        bst = _Bst(STAGED, unresolvable={"gone.bst"})
        got = _read(monkeypatch, bst,
                    ["core.bst", "gone.bst", "lib-a.bst"])
        assert got["core.bst"] == {"/usr/include/core.hpp", "/usr/lib/libcore.a"}
        assert got["lib-a.bst"] == {"/usr/include/lib-a.hpp"}
        assert got["gone.bst"] == set(), "the unreadable element lost its key"

    def test_the_retry_is_one_call_per_element_of_that_group_only(
            self, monkeypatch):
        """The fallback pays the old cost, and only when something is
        wrong. One failed batch of three is 1 + 3 calls, not 3 for every
        group in the run."""
        bst = _Bst(STAGED, unresolvable={"gone.bst"})
        _read(monkeypatch, bst, ["core.bst", "gone.bst", "lib-a.bst"])
        assert bst.calls == [
            ["core.bst", "gone.bst", "lib-a.bst"],
            ["core.bst"], ["gone.bst"], ["lib-a.bst"]]

    def test_a_healthy_run_never_falls_back(self, monkeypatch):
        """The clause that keeps the one above from being free: if the
        fallback ran always, the batching would buy nothing and every
        other clause here would still pass."""
        bst = _Bst(STAGED)
        _read(monkeypatch, bst, sorted(STAGED))
        assert len(bst.calls) == 1, bst.calls


if __name__ == "__main__":                       # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
