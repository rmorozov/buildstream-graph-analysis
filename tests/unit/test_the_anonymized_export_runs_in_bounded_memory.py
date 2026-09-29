"""UX-1069: the anonymized export runs in bounded memory.

A generated capture at N and 4N records (plane2 `binary_cost.{A}.by_cpu[]`
plus host-samples lines) exports with a `tracemalloc` peak that grows by
under a quarter of the bytes it gained; a legacy plane2 whose bulk is an
unnamed `processes[]` refuses under the same bound. The reader and residue
chunks are shrunk to 4 KiB so N stays in the unit tier: the chunk sets the
constant, the guard reads the growth. The archive waits 0600 beside the
destination until approval, and a refusal leaves that directory as it was.
"""

import json
import os
import pathlib
import stat
import tracemalloc

import pytest

from bga import anonymize, bundle, disclosure, jsonstream, run_store

REPO = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures"
STAMP = "20260902T101112Z"
KEY = bytes(range(32))
ELEMENTS = 8
N = 1000
BOUND = 0.25


def _capture(root: pathlib.Path, n: int, legacy: bool = False, context=None) -> str:
    snapshot = pathlib.Path(run_store.runs_dir(str(root))) / STAMP
    (snapshot / "run").mkdir(parents=True)
    uids = [f"acme-lib-{i}.bst" for i in range(ELEMENTS)]
    (snapshot / "run" / "graph.json").write_text(json.dumps({"elements": [{"uid": u} for u in uids]}))
    (snapshot / "run" / "trace.json").write_text('{"spans": []}')
    (snapshot / "run" / "run-context.json").write_text(json.dumps(context or {"host": "runner-7"}))
    half = n // 2
    if legacy:
        plane2 = {
            "process_count": n,
            "processes": [
                {"pid": 1000 + k, "cmd": f"gcc -c acme-{k}.c", "cpu_us": 1234 + k, "element": uids[k % ELEMENTS]}
                for k in range(n)
            ],
        }
    else:
        plane2 = {
            "process_count": n,
            "binary_cost": {
                uid: {
                    "available": True,
                    "measured_cpu_us": 10**6,
                    "by_cpu": [
                        {"binary": "gcc", "count": k, "cpu_us": 1000 + k, "cpu_share": 0.0125, "wall_s": 1.5 + k / 1000}
                        for k in range(i, half, ELEMENTS)
                    ],
                }
                for i, uid in enumerate(uids)
            },
        }
    (snapshot / "plane2.json").write_text(json.dumps(plane2))
    lines = [
        {
            "schema": "host-samples/v1",
            "interval_s": 2.0,
            "clock": "CLOCK_MONOTONIC",
            "wall_at_start": 1788644102.9,
            "monotonic_at_start": 5287.01,
            "available": True,
        }
    ]
    lines += [
        {"mem_free_kb": 9131492 - k, "cores": 4, "load1": 0.02, "t": 5287.02 + 2 * k, "cpu_busy_cores": 1.787}
        for k in range(0 if legacy else n - half)
    ]
    (snapshot / "host-samples.jsonl").write_text("".join(json.dumps(line) + "\n" for line in lines))
    return str(snapshot)


def _export(tmp_path: pathlib.Path, snapshot: str, approve=lambda screen: True):
    pmap = anonymize.PseudonymMap(str(tmp_path / "anon" / "map.json"))
    (tmp_path / "out").mkdir(exist_ok=True)
    return bundle.export_anonymized(snapshot, KEY, pmap, str(tmp_path / "out" / "bundle.tar.gz"), approve=approve)


def _peak(tmp_path: pathlib.Path, n: int, legacy: bool) -> tuple[int, int, str]:
    snapshot = _capture(tmp_path / "project", n, legacy)
    size = sum(p.stat().st_size for p in pathlib.Path(snapshot).rglob("*") if p.is_file())
    tracemalloc.start()
    try:
        _export(tmp_path, snapshot)
        outcome = "exported"
    except bundle.BundleError as error:
        outcome = str(error)
    finally:
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    return peak, size, outcome


@pytest.fixture
def small_chunks(monkeypatch):
    monkeypatch.setattr(jsonstream, "CHUNK", 4096)
    monkeypatch.setattr(bundle, "RESIDUE_CHUNK", 4096)


@pytest.mark.parametrize("legacy", [False, True], ids=["by_cpu", "legacy_processes"])
def test_the_peak_grows_by_under_a_quarter_of_the_bytes(legacy, tmp_path, small_chunks):
    _peak(tmp_path / "warm", 10, legacy)  # first-call caches, so N pays none of them
    (peak_n, bytes_n, outcome_n), (peak_4n, bytes_4n, outcome_4n) = (
        _peak(tmp_path / "n", N, legacy),
        _peak(tmp_path / "4n", 4 * N, legacy),
    )
    for outcome in (outcome_n, outcome_4n):
        if legacy:
            assert "plane2.json: processes: not named by the policy" in outcome
        else:
            assert outcome == "exported"
    grew, gained = peak_4n - peak_n, bytes_4n - bytes_n
    assert gained > 200_000, gained
    assert grew < BOUND * gained, (peak_n, peak_4n, gained)


def _listing(directory: pathlib.Path) -> list:
    return sorted(str(p.relative_to(directory)) for p in directory.rglob("*"))


def test_the_archive_waits_0600_beside_the_destination_until_approval(tmp_path):
    out = tmp_path / "out"
    seen = []

    def approve(_screen):
        files = [p for p in out.rglob("*") if p.is_file()]
        seen.extend((p.parent.parent, p.name, stat.S_IMODE(p.stat().st_mode)) for p in files)
        return True

    path, _manifest = _export(tmp_path, _capture(tmp_path / "project", 40), approve)
    assert seen == [(out, "bundle.tar.gz", 0o600)]
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert _listing(out) == ["bundle.tar.gz"]


def _refuse(_screen):
    return False


@pytest.mark.parametrize("fault", ["refused", "gap", "residue"])
def test_a_refusal_leaves_the_directory_as_it_was(fault, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "earlier.txt").write_text("kept")
    context = {"host": "runner-7", "host_manifest": {"cpu_model": "Xeon acme-lib-1.bst edition"}}
    snapshot = _capture(
        tmp_path / "project", 40, legacy=fault == "gap", context=context if fault == "residue" else None
    )
    before = _listing(out)
    match = {"refused": "did not approve", "gap": "processes: not named", "residue": "residue scan"}[fault]
    with pytest.raises(bundle.BundleError, match=match):
        _export(tmp_path, snapshot, _refuse)
    assert _listing(out) == before
    assert not (tmp_path / "anon" / "map.json").exists()


MEMBERS = [
    ("macro_micro/plane2.json", "plane2/v3"),
    ("macro_micro/run/run-context.json", "run-context/v9"),
    ("macro_micro/run/graph.json", "graph/v9"),
    ("host_cpu/host-samples.jsonl", "host-samples/v1"),
]


def _tree(source: pathlib.Path, policy: str, trie: dict, walk) -> bytes:
    """Today's bytes: the whole member parsed, rewritten as a tree, dumped."""
    text = source.read_text(encoding="utf-8")
    documents = (
        [json.loads(line) for line in text.splitlines() if line.strip()]
        if source.suffix == ".jsonl"
        else [json.loads(text)]
    )
    for document in documents:
        walk.collect(policy, trie, document)
    lines = [json.dumps(walk.rewrite(policy, trie, d), ensure_ascii=False) for d in documents]
    return ("\n".join(lines) + "\n").encode("utf-8")


@pytest.mark.parametrize("chunk", [1, 7, 65536])
@pytest.mark.parametrize("member, policy", MEMBERS, ids=[m for m, _p in MEMBERS])
def test_the_streamed_bytes_are_the_tree_rewrites(member, policy, chunk, tmp_path, monkeypatch):
    source = FIXTURES / member
    trie = disclosure.compile_policy(disclosure.POLICIES[policy])
    expected = _tree(source, policy, trie, bundle._Anonymizer(KEY, anonymize.PseudonymMap(str(tmp_path / "a.json"))))
    walk = bundle._Anonymizer(KEY, anonymize.PseudonymMap(str(tmp_path / "b.json")))
    gaps, errors = bundle._scan(str(source), policy, trie, walk)
    assert (gaps, errors) == ([], [])
    target = tmp_path / "streamed"
    monkeypatch.setattr(jsonstream, "CHUNK", chunk)
    bundle._stream(str(source), policy, trie, walk, str(target))
    assert target.read_bytes() == expected
