"""UX-111 follow-through: a series is a series *of* something.

`bga compare` refuses a mismatched pair and `bga baseline` refuses a set
that is not internally comparable. `bga cache-trend` is the third
multi-run command, and it accepted anything handed to it - three
freedesktop-sdk runs with one `examples/06` run among them produced

    Every trended metric on the newest run sits inside the band its
    trailing window describes.

a confident verdict over a band containing a foreign project.
"""
from bga.cache_trend import _subject, _subject_label, build_trend, format_trend_text


class _Context:
    def __init__(self, identity):
        self.run_identity = identity


def _row(name, subject, hit=0.7, built=25, cached=65):
    return {
        'run': name, 'subject': subject, 'run_id': 'abc',
        'run_mode': 'incremental', 'total_duration_us': 1_000_000,
        'hit_share': hit, 'built_elements': built, 'cached_elements': cached,
        'transfer_us': None, 'transfer_per_artifact_us': None,
        'rebuild_us': 1_000_000, 'churn': None,
    }


FDSDK = ('.', ('components/libxml2.bst',))
EXAMPLE = ('examples/06-macro-micro-optimization', ('all.bst',))


class TestWhatASeriesIsOf:
    def test_the_subject_is_the_project_and_its_targets(self):
        subject = _subject(_Context({
            'project_identity': '.', 'targets': ['components/libxml2.bst'],
            'project_git_commit': '953683fb',
        }))

        assert subject == FDSDK

    def test_and_deliberately_not_the_commit(self):
        """The run-identity hash the other two commands key on includes
        `project_git_commit`. Keying on it here would refuse every trend
        that spans commits - which is the only kind of cache-health trend
        there is."""
        one = _subject(_Context({
            'project_identity': '.', 'targets': ['t.bst'],
            'project_git_commit': 'aaaaaaaa',
        }))
        two = _subject(_Context({
            'project_identity': '.', 'targets': ['t.bst'],
            'project_git_commit': 'bbbbbbbb',
        }))

        assert one == two

    def test_a_capture_that_records_no_identity_says_so(self):
        """Every run directory extracted before P1-37. `None` rather than
        a fabricated subject, so "not recorded" cannot be mistaken for
        "checked and matched"."""
        assert _subject(_Context({})) is None
        assert _subject(_Context(None)) is None
        assert _subject_label(None) == "no identity recorded"


class TestABandIsNotComputedOverUnlikeThings:
    def test_a_foreign_project_in_the_series_withholds_the_verdict(self):
        trend = build_trend([
            _row('a/run', FDSDK), _row('b/run', FDSDK),
            _row('c/run', EXAMPLE, hit=0.0, built=11, cached=0),
            _row('d/run', FDSDK),
        ])

        assert trend['heterogeneous'] is not None
        assert trend['findings'] == []
        # The rows survive - each is a real reading of its own run, and
        # only the band was cross-run.
        assert [row['run'] for row in trend['runs']] == [
            'a/run', 'b/run', 'c/run', 'd/run']
        # ...and one reason is given, not two.
        assert trend['insufficient_window'] is None

    def test_and_the_report_names_which_run_is_the_odd_one(self):
        trend = build_trend([
            _row('a/run', FDSDK), _row('b/run', FDSDK),
            _row('c/run', EXAMPLE), _row('d/run', FDSDK),
        ])
        text = format_trend_text(trend)

        assert "NOT COMPARABLE" in text
        assert "examples/06-macro-micro-optimization all.bst" in text
        assert "components/libxml2.bst" in text
        assert "sits inside the band" not in text

    def test_a_homogeneous_series_still_gets_its_verdict(self):
        trend = build_trend([_row(f'{n}/run', FDSDK) for n in "abcd"])

        assert trend['heterogeneous'] is None
        assert "sits inside the band" in format_trend_text(trend)

    def test_a_series_of_one_subject_and_one_unidentified_run_is_not_declared_clean(self):
        """A single run with no recorded identity cannot be confirmed to
        belong, so it is not counted as agreeing - but neither is it
        treated as a second subject, because absent is not different."""
        trend = build_trend([
            _row('a/run', FDSDK), _row('b/run', None),
            _row('c/run', FDSDK), _row('d/run', FDSDK),
        ])

        assert trend['heterogeneous'] is None


def test_the_exit_code_matches_the_rest_of_the_family(tmp_path):
    """`bga compare` returns 6 for a pair it will not compare. A CI job
    piping a heterogeneous series must not read a clean exit as a healthy
    cache."""
    from bga.cli import EXIT_CODE_MISMATCHED_RUNS

    assert EXIT_CODE_MISMATCHED_RUNS == 6
