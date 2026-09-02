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
    _find_run_directory, check_homogeneity, exclude_refs, fetch_run_directory,
    format_set_text, list_capture_refs, refusal_remedy,
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
    """`target` did not exist in `capture-context.txt` until UX-96, so
    already-published refs lack it. Treating absence as a difference
    would make the existing history unusable on the day the field was
    added - so it is not a mismatch, but UX-114 no longer lets it be
    silence either (see below)."""
    result = check_homogeneity([
        _member('a', target='components/libxml2.bst'),
        _member('b'),  # published before the field existed
    ])
    assert result['mismatches'] == []


# --- UX-114: absence is per-field, and never silent ---------------------

def test_partial_coverage_of_an_ambiguous_field_is_reported_as_unverified():
    """`target` has no default to fall back on: a capture that did not
    record it might have built anything. "Checked and equal" and
    "checked on three of five" are different claims, and the skip made
    them print identically."""
    result = check_homogeneity([
        _member('a', target='components/libxml2.bst'),
        _member('b'),
        _member('c'),
    ])
    gap = next(g for g in result['coverage_gaps'] if g['field'] == 'target')
    assert gap['refs'] == ['b', 'c']
    assert '2 of 3' in gap['message']
    assert result['mismatches'] == []


def test_a_field_no_capture_records_is_not_a_coverage_gap():
    """Nothing was checked *against*, so there is no partial coverage to
    report - just a field the set is silent on, which the per-run listing
    already shows. Warning here would put a line on every set forever."""
    result = check_homogeneity([_member('a'), _member('b')])
    assert [g['field'] for g in result['coverage_gaps']] == []


def test_an_absent_spine_flag_means_off_and_mismatches_a_spine_capture():
    """The failure UX-114 was filed for. `trace_spine` has a defined
    default - `real-project-capture.yml` sets `TRACE_SPINE` to `false`
    when nothing asks otherwise - so a capture that recorded nothing was
    taken under it, and absent-vs-`true` is a real difference in
    instrumentation rather than a field to skip."""
    result = check_homogeneity([
        _member('spine', trace_spine='true'),
        _member('old-a'),
        _member('old-b'),
    ])
    mismatch = next(m for m in result['mismatches'] if m['field'] == 'trace_spine')
    assert mismatch['values'] == ['false', 'true']
    assert mismatch['assumed'] == 'false'
    assert mismatch['assumed_for'] == ['old-a', 'old-b']


def test_an_absent_spine_flag_agrees_with_a_recorded_off():
    """The other half of the same rule: absent and `false` are the same
    claim, so a set of old refs plus a new hook-only one is still a set."""
    result = check_homogeneity([
        _member('new', trace_spine='false'),
        _member('old'),
    ])
    assert [m['field'] for m in result['mismatches']] == []


def test_an_assumed_default_is_stated_even_when_it_changes_nothing():
    """Every capture published before the field existed is being taken
    at its default, and a reader is entitled to know that is an
    assumption rather than a reading. On the live five-ref fdsdk set this
    fires for four of five."""
    result = check_homogeneity([_member('old-a'), _member('old-b')])
    assumption = next(a for a in result['assumptions'] if a['field'] == 'trace_spine')
    assert assumption['assumed'] == 'false'
    assert assumption['refs'] == ['old-a', 'old-b']


def test_a_mismatch_does_not_also_print_the_assumption_underneath():
    """The mismatch line already carries "N recorded nothing and were
    taken as false"; a second block saying the same thing is the same
    sentence twice."""
    result = check_homogeneity([
        _member('spine', trace_spine='true'),
        _member('old'),
    ])
    assert [m['field'] for m in result['mismatches']] == ['trace_spine']
    assert 'trace_spine' not in [a['field'] for a in result['assumptions']]


def test_trace_opens_is_checked_at_all():
    """It was never in the field list, so two captures instrumented
    differently on the opens axis were a set. It has a default for the
    same reason `trace_spine` does."""
    result = check_homogeneity([
        _member('with-opens', trace_opens='true'),
        _member('without-opens', trace_opens='false'),
    ])
    assert [m['field'] for m in result['mismatches']] == ['trace_opens']


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


def test_a_spine_capture_does_not_silently_join_a_hook_only_band():
    """UX-108: the spine records more processes and costs wall clock, so
    a band mixing the two measures the tooling change rather than the
    build's noise."""
    from tools.bst_baseline_set import check_homogeneity

    members = [
        {"ref": {"ref": "captures/fdsdk/abc-incremental-b4j4-1"},
         "context": {"fdsdk_ref": "abc", "trace_spine": "false"}},
        {"ref": {"ref": "captures/fdsdk/abc-incremental-b4j4-2"},
         "context": {"fdsdk_ref": "abc", "trace_spine": "true"}},
    ]
    result = check_homogeneity(members)

    assert [m["field"] for m in result["mismatches"]] == ["trace_spine"]


# --- the refusal's remedy, and the option that carries it out -----------
#
# UX-96 round 76: the refusal named one remedy - narrow the glob - and
# the ref name carries only four of the seven homogeneous fields. On the
# seven published incrementals, all one tuple, the set refused on
# `trace_spine` and no glob could separate it.

def _ref(run_id, mode='incremental'):
    return {'ref': f'captures/fdsdk/953683fb-{mode}-b4j4-{run_id}',
            'run_id': run_id}


class TestTheRefusalNamesARemedyThatCanBeCarriedOut:
    """Input classes: the differing field is one the ref name carries ·
    one it cannot · both at once."""

    def test_a_ref_name_field_still_says_narrow_the_glob(self):
        members = [_member('a', capture_mode='incremental'),
                   _member('b', capture_mode='cold')]
        remedy = refusal_remedy(check_homogeneity(members)['mismatches'], members)
        assert remedy.startswith('Narrow --glob')
        assert '--exclude' not in remedy

    def test_a_field_the_ref_name_cannot_carry_says_exclude(self):
        members = [_member('a', trace_spine='false'),
                   _member('b', trace_spine='true')]
        remedy = refusal_remedy(check_homogeneity(members)['mismatches'], members)
        assert '--exclude' in remedy
        assert 'not in the ref name' in remedy

    def test_the_remedy_names_the_minority_capture(self):
        """A caller who is told to exclude something needs to know what.
        The minority is a suggestion - the majority is not automatically
        the right population - but naming nothing is not advice."""
        members = [
            _member('captures/fdsdk/953683fb-incremental-b4j4-1', trace_spine='false'),
            _member('captures/fdsdk/953683fb-incremental-b4j4-2', trace_spine='false'),
            _member('captures/fdsdk/953683fb-incremental-b4j4-3', trace_spine='true'),
        ]
        remedy = refusal_remedy(check_homogeneity(members)['mismatches'], members)
        assert remedy.endswith('Here that is 3.')

    def test_a_ref_name_field_and_an_invisible_one_together_say_exclude(self):
        """The glob cannot fix the invisible half, so the remedy that
        can is the one printed."""
        members = [_member('a', capture_mode='cold', trace_spine='true'),
                   _member('b', capture_mode='incremental', trace_spine='false')]
        remedy = refusal_remedy(check_homogeneity(members)['mismatches'], members)
        assert '--exclude' in remedy

    def test_two_invisible_fields_read_as_a_plural(self):
        members = [_member('a', trace_spine='true', trace_opens='false'),
                   _member('b', trace_spine='false', trace_opens='true')]
        remedy = refusal_remedy(check_homogeneity(members)['mismatches'], members)
        assert 'are not in the ref name' in remedy


class TestExcludeNarrowsTheSetBeforeTheNewestNAreTaken:
    """Input classes: no patterns · a run id · a ref glob · a pattern
    matching nothing. Order matters - excluding after `-n` would leave
    the set short instead of reaching further back."""

    def test_no_patterns_is_the_whole_list(self):
        refs = [_ref('3'), _ref('2'), _ref('1')]
        assert exclude_refs(refs, []) == refs

    def test_a_bare_run_id_drops_that_capture(self):
        refs = [_ref('3'), _ref('2'), _ref('1')]
        assert [r['run_id'] for r in exclude_refs(refs, ['2'])] == ['3', '1']

    def test_a_glob_over_the_ref_name_drops_a_class(self):
        refs = [_ref('3', 'cold'), _ref('2'), _ref('1', 'cold')]
        kept = exclude_refs(refs, ['*-cold-*'])
        assert [r['run_id'] for r in kept] == ['2']

    def test_a_pattern_matching_nothing_changes_nothing(self):
        refs = [_ref('3'), _ref('2')]
        assert exclude_refs(refs, ['99999']) == refs

    def test_patterns_accumulate(self):
        refs = [_ref('3'), _ref('2'), _ref('1')]
        assert [r['run_id'] for r in exclude_refs(refs, ['2', '1'])] == ['3']

    def test_the_exclusion_happens_before_the_newest_n_are_taken(self, monkeypatch):
        """Excluding after `-n` would hand back a set one short instead
        of reaching one further into the history. Driven through `main`,
        because the order of those two lines is the claim."""
        import tools.bst_baseline_set as module

        monkeypatch.setattr(module, 'list_capture_refs',
                            lambda *a, **k: [_ref('3'), _ref('2'), _ref('1')])
        fetched = []

        def _fetch(remote, ref, dest, cwd=None):
            fetched.append(ref['run_id'])
            return {'ref': ref, 'run_dir': dest, 'context': _context()}

        monkeypatch.setattr(module, 'fetch_run_directory', _fetch)
        code = module.main(['--glob', 'captures/fdsdk/*', '-n', '2',
                            '--exclude', '3', '-f', 'json'])
        assert code == 0
        assert fetched == ['2', '1']


class TestASetNarrowedByHandSaysSo:
    """A band over a population the caller edited is a different claim
    from a band over everything published, so the listing says which."""

    @staticmethod
    def _one():
        name = 'captures/fdsdk/953683fb-incremental-b4j4-1'
        member = _member(name)
        member['ref'] = {'ref': name, 'commit': '953683fb',
                         'mode': 'incremental', 'builders': '4', 'max_jobs': '4'}
        return [member]

    def test_the_listing_states_how_many_were_dropped(self):
        members = self._one()
        text = format_set_text(members, check_homogeneity(members), excluded=2)
        assert '--exclude dropped 2 capture(s)' in text

    def test_an_unnarrowed_set_says_nothing(self):
        members = self._one()
        text = format_set_text(members, check_homogeneity(members))
        assert '--exclude' not in text
