"""UX-96: assembling a baseline set is one command, and it checks the
set it assembled.

The band arithmetic was verified in `UX-81` and is untouched here. What
these cover is everything around it that round 11 did by hand and that
nothing checked: ordering the refs, materialising two different
published layouts, and the two kinds of difference across a set - one
that makes it not a set at all, and one that is merely worth saying.
"""
import subprocess

import pytest

from tools.bst_baseline_set import (
    _find_run_directory, check_homogeneity, fetch_run_directory, list_capture_refs,
)


def _context(**overrides):
    base = {
        'fdsdk_ref': '953683fb', 'capture_mode': 'incremental',
        'builders': '4', 'max_jobs': '4', 'bga_ref': 'aaaaaaa',
    }
    base.update(overrides)
    return base


def _member(ref_name, **context):
    return {'ref': {'ref': ref_name}, 'context': _context(**context)}


# --- ref discovery ------------------------------------------------------

def _fake_ls_remote(monkeypatch, stdout):
    def _run(argv, **kwargs):
        assert argv[:2] == ['git', 'ls-remote']
        return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr='')
    monkeypatch.setattr(subprocess, 'run', _run)


def test_refs_come_back_newest_first_by_run_id(monkeypatch):
    """GitHub's run id increases monotonically, so the ref name orders
    itself - no commit dates to fetch and no clock to trust."""
    _fake_ls_remote(monkeypatch, "\n".join([
        "aaa\trefs/heads/captures/fdsdk/953683fb-incremental-b4j4-32064333551",
        "bbb\trefs/heads/captures/fdsdk/953683fb-incremental-b4j4-32122941503",
        "ccc\trefs/heads/captures/fdsdk/953683fb-incremental-b4j4-32113933158",
    ]) + "\n")
    refs = list_capture_refs('origin', 'captures/*')
    assert [r['run_id'] for r in refs] == ['32122941503', '32113933158', '32064333551']
    assert refs[0]['mode'] == 'incremental' and refs[0]['builders'] == '4'


def test_a_moving_pointer_ref_is_not_a_set_member(monkeypatch):
    """`captures/fdsdk-latest` follows the newest good capture. A
    baseline set containing it would change under whoever is reading
    it, so it is skipped rather than resolved."""
    _fake_ls_remote(monkeypatch, "\n".join([
        "aaa\trefs/heads/captures/fdsdk-latest",
        "bbb\trefs/heads/captures/fdsdk-cold-latest",
        "ccc\trefs/heads/captures/fdsdk/953683fb-incremental-b4j4-32122941503",
    ]) + "\n")
    refs = list_capture_refs('origin', 'captures/*')
    assert [r['run_id'] for r in refs] == ['32122941503']


# --- homogeneity --------------------------------------------------------

def test_a_set_spanning_two_modes_is_not_a_set():
    """A cold capture and an incremental one measure different builds of
    the same commit. `bga compare` already refuses the pair; this
    refuses before the fetch, where the error is cheap and legible."""
    result = check_homogeneity([
        _member('a', capture_mode='incremental'),
        _member('b', capture_mode='cold'),
    ])
    assert [m['field'] for m in result['mismatches']] == ['capture_mode']
    assert result['mismatches'][0]['values'] == ['cold', 'incremental']


def test_a_set_spanning_two_targets_is_not_a_set():
    """The ref name carries commit, mode, builders and max_jobs - not
    the target. Two captures of different targets are different builds,
    and before `UX-96` recorded the target nothing could tell them
    apart."""
    result = check_homogeneity([
        _member('a', target='components/libxml2.bst'),
        _member('b', target='components/glib.bst'),
    ])
    assert [m['field'] for m in result['mismatches']] == ['target']


def test_a_field_absent_from_an_older_capture_is_not_a_mismatch():
    """`target` did not exist in `capture-context.txt` until this task,
    so every already-published ref lacks it. Treating absence as a
    difference would make the existing history unusable on the day the
    field was added."""
    result = check_homogeneity([
        _member('a', target='components/libxml2.bst'),
        _member('b'),  # published before the field existed
    ])
    assert result['mismatches'] == []


def test_capture_tooling_drift_is_reported_and_not_refused():
    """The three real fdsdk captures were produced by three different
    `bga` revisions; each recorded the fact and nothing read it. It is a
    real risk to a band - and also completely normal in a repository
    under development, so refusing would disable the helper exactly when
    it is most needed."""
    result = check_homogeneity([
        _member('a', bga_ref='1c268de9'),
        _member('b', bga_ref='108be7b3'),
        _member('c', bga_ref='1143f2b2'),
    ])
    assert result['mismatches'] == []
    drift = result['revision_drift']
    assert drift['revisions'] == ['108be7b3', '1143f2b2', '1c268de9']
    assert 'widen or bias the band' in drift['message']


def test_one_revision_across_the_set_is_no_drift():
    assert check_homogeneity([_member('a'), _member('b')])['revision_drift'] is None


# --- materialising the two published layouts ----------------------------

def test_the_run_directory_is_found_inside_an_arbitrarily_nested_tarball(tmp_path):
    """The older refs carry only `capture.tar.gz`, and where the `run/`
    sits inside it is a property of how that tarball was made."""
    nested = tmp_path / "capture" / "deeper" / "run"
    nested.mkdir(parents=True)
    (nested / "run-context.json").write_text("{}")
    (nested / "graph.json").write_text("{}")
    assert _find_run_directory(str(tmp_path)) == str(nested)


def test_a_ref_carrying_neither_layout_is_an_error_not_an_empty_set(tmp_path, monkeypatch):
    """A ref with no run directory is a capture that failed to publish
    one. Returning an empty set would put it silently into a band."""
    def _run(argv, **kwargs):
        if argv[:2] == ['git', 'fetch']:
            return subprocess.CompletedProcess(argv, 0, stdout='', stderr='')
        if argv[:2] == ['git', 'show']:
            return subprocess.CompletedProcess(argv, 0, stdout='builders=4\n', stderr='')
        if argv[:2] == ['git', 'ls-tree']:
            return subprocess.CompletedProcess(argv, 0, stdout='README.md\n', stderr='')
        raise AssertionError(argv)
    monkeypatch.setattr(subprocess, 'run', _run)
    with pytest.raises(RuntimeError, match="neither run/ nor capture.tar.gz"):
        fetch_run_directory('origin', {'ref': 'captures/x'}, str(tmp_path / "dest"))
