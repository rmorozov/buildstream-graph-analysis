"""UX-116: the founding question, answered rather than assembled.

`UX-09` asked in week one whether `--builders` and `--max-jobs` compete
for the same cores and what to set them to. Every round since added one
more input — the sweep's knee, measured cores-busy, pinning detection,
the memory envelope — and none of them added the sentence that
intersects them. A reader had four blocks and no recommendation.

These cover the intersection itself: that the *binding* constraint is
the one named, that a constraint nobody measured never becomes an
unbounded ceiling, and that the block declines to speak at all on the
same bar `UX-83` uses.
"""
from bga.correlate import compute_capacity_recommendation
from bga.findings import _capacity_recommendation_finding


def _plane2(cores_busy=2.0, host=4, pinned=()):
    return {'cores_busy': cores_busy, 'host_cpu_count': host,
            'saturated': False, 'pinned_elements': list(pinned)}


def _envelope(fits_up_to, measured=None, host_mb=16000):
    measured = measured or fits_up_to
    return {
        'host_memory_mb': host_mb,
        'elements_measured': measured,
        'largest_element_peak_mb': 1000,
        'projections': [
            {'builders': n, 'envelope_mb': 1000 * n,
             'share_of_host': 1000 * n / host_mb, 'fits': n <= fits_up_to}
            for n in range(1, measured + 1)
        ],
    }


class TestWhichConstraintBinds:
    def test_cpu_binds_when_it_is_the_smallest(self):
        """UX-116's own worked example: the graph could use five builders,
        the host's cores cannot feed them, and memory is nowhere near."""
        recommendation = compute_capacity_recommendation(
            _plane2(cores_busy=3.4, host=4), _envelope(11), knee=5,
            builders=4, native_max_jobs=4,
        )

        assert recommendation['binding_constraint'] == 'CPU'
        assert recommendation['recommended_builders'] == 4
        assert recommendation['change'] == 0

    def test_the_graph_binds_when_the_schedule_runs_out_first(self):
        """More builders than the graph has parallelism for is capacity
        that cannot be spent, whatever the host could feed."""
        recommendation = compute_capacity_recommendation(
            _plane2(cores_busy=0.5, host=16), _envelope(11), knee=2,
            builders=4, native_max_jobs=1,
        )

        assert recommendation['binding_constraint'] == 'graph'
        assert recommendation['recommended_builders'] == 2

    def test_memory_binds_before_either(self):
        """UX-104's whole point: advice that clears CPU and fails memory
        is advice to build into swap."""
        recommendation = compute_capacity_recommendation(
            _plane2(cores_busy=0.5, host=16), _envelope(fits_up_to=2, measured=11),
            knee=8, builders=4, native_max_jobs=1,
        )

        assert recommendation['binding_constraint'] == 'memory'
        assert recommendation['recommended_builders'] == 2

    def test_room_to_grow_is_reported_as_a_change(self):
        recommendation = compute_capacity_recommendation(
            _plane2(cores_busy=1.0, host=8), _envelope(11), knee=6,
            builders=2, native_max_jobs=2,
        )

        assert recommendation['recommended_builders'] == 6
        assert recommendation['change'] == 4

    def test_the_cpu_ceiling_is_derived_from_the_measured_draw(self):
        """Not a rule of thumb: `cores_busy / builders` is what one
        concurrently-building element actually drew, and the ceiling is
        how many of those the host's cores can feed."""
        recommendation = compute_capacity_recommendation(
            _plane2(cores_busy=2.0, host=8), _envelope(64), knee=64,
            builders=4, native_max_jobs=4,
        )

        cpu = next(c for c in recommendation['constraints'] if c['name'] == 'CPU')
        # 0.5 cores per element, 8 cores -> 16.
        assert cpu['allows'] == 16
        assert "0.50 core(s) per concurrent element" in cpu['reason']


class TestWhatItRefusesToSay:
    def test_no_plane_2_cpu_measurement_means_no_block(self):
        """The same bar UX-83 uses. A recommendation resting on a missing
        `cores_busy` is a guess wearing a measurement's clothes."""
        assert compute_capacity_recommendation(
            {'cores_busy': None, 'host_cpu_count': 4}, _envelope(11),
            knee=5, builders=4) == {}

    def test_no_host_core_count_means_no_block(self):
        assert compute_capacity_recommendation(
            {'cores_busy': 2.0, 'host_cpu_count': None}, _envelope(11),
            knee=5, builders=4) == {}

    def test_no_builders_value_means_no_block(self):
        """The whole derivation is per-builder; without the denominator
        there is nothing to divide."""
        assert compute_capacity_recommendation(
            _plane2(), _envelope(11), knee=5, builders=None) == {}

    def test_an_unmeasured_memory_envelope_is_not_an_unbounded_ceiling(self):
        """Absent must not read as "memory allows anything" - the
        constraint is simply not listed, and the binding one is chosen
        from what was measured."""
        recommendation = compute_capacity_recommendation(
            _plane2(cores_busy=1.0, host=8), {}, knee=6, builders=2)

        assert [c['name'] for c in recommendation['constraints']] == ['graph', 'CPU']
        assert recommendation['binding_constraint'] == 'graph'

    def test_a_knee_at_the_top_of_the_swept_range_says_so(self):
        """The sweep is bounded for cost, so a knee sitting at the ceiling
        of the range is a lower bound on what the graph wants, not the
        answer."""
        recommendation = compute_capacity_recommendation(
            _plane2(cores_busy=0.5, host=16), _envelope(11), knee=8,
            knee_range_top=8, builders=4)

        graph = next(c for c in recommendation['constraints'] if c['name'] == 'graph')
        assert "the top of the range swept" in graph['reason']

    def test_the_contention_caveat_is_inherited_not_reinvented(self):
        """UX-14: the sweep replays observed durations and does not model
        contention. A recommendation built on a knee carries that."""
        recommendation = compute_capacity_recommendation(
            _plane2(), _envelope(11), knee=5, builders=4)

        assert "does not model contention (UX-14)" in recommendation['caveat']
        assert "no configuration was tried" in recommendation['caveat']


class TestTheFinding:
    def _result(self, recommendation):
        return type('_R', (), {'capacity_recommendation': recommendation})()

    def test_no_recommendation_emits_no_finding(self):
        assert _capacity_recommendation_finding(self._result({})) == []

    def test_the_title_names_the_setting_the_constraint_and_the_verdict(self):
        recommendation = compute_capacity_recommendation(
            _plane2(cores_busy=3.4, host=4), _envelope(11), knee=5,
            builders=4, native_max_jobs=4)

        finding = _capacity_recommendation_finding(self._result(recommendation))[0]

        assert finding['id'] == 'capacity-recommendation'
        assert "builders 4 x max-jobs 4 on 4 core(s)" in finding['title']
        assert "CPU binds at exactly 4" in finding['title']

    def test_an_unrecorded_max_jobs_is_named_rather_than_dropped(self):
        """The question is the joint one. "builders 4" reads as a complete
        setting; it is not one."""
        recommendation = compute_capacity_recommendation(
            _plane2(), _envelope(11), knee=5, builders=4, native_max_jobs=None)

        finding = _capacity_recommendation_finding(self._result(recommendation))[0]

        assert "max-jobs unrecorded" in finding['title']

    def test_every_constraint_is_shown_beneath_the_verdict(self):
        """The binding one is the answer; the others are why it binds, and
        a reader who disagrees needs to see them to argue."""
        recommendation = compute_capacity_recommendation(
            _plane2(cores_busy=3.4, host=4), _envelope(11), knee=5, builders=4)

        detail = "\n".join(
            _capacity_recommendation_finding(self._result(recommendation))[0]['detail'])

        assert "graph allows 5" in detail
        assert "CPU allows 4" in detail
        assert "memory allows 11" in detail

    def test_pinning_is_offered_as_free_capacity_when_cpu_binds(self):
        """`UX-31`/`UX-83`: an element that asked its own build for `-j1`
        is capacity already paid for and not used, and it beats raising
        anything."""
        recommendation = compute_capacity_recommendation(
            _plane2(cores_busy=3.4, host=4, pinned=['core.bst']), _envelope(11),
            knee=5, builders=4)

        finding = _capacity_recommendation_finding(self._result(recommendation))[0]

        assert any("core.bst" in line and "-j1" in line for line in finding['detail'])
        assert finding['elements'] == ['core.bst']

    def test_pinning_is_offered_when_the_graph_binds_too(self):
        """First written as "only when CPU binds", and the reconstructed
        macro-fixed capture of `examples/06` disproved it: `core.bst` is
        pinned there, the graph binds at 6, and suppressing the line hid
        the one fix that was actually available. A pinned element holds a
        builder slot while drawing one core - the slot is the waste when
        CPU binds, and the element's own length is the waste when the
        graph does."""
        recommendation = compute_capacity_recommendation(
            _plane2(cores_busy=2.11, host=4, pinned=['core.bst']),
            _envelope(9), knee=6, builders=4)

        finding = _capacity_recommendation_finding(self._result(recommendation))[0]

        assert recommendation['binding_constraint'] == 'graph'
        assert any("core.bst" in line and "-j1" in line for line in finding['detail'])

    def test_a_run_already_at_its_ceiling_is_info_not_a_problem(self):
        recommendation = compute_capacity_recommendation(
            _plane2(cores_busy=3.4, host=4), _envelope(11), knee=5, builders=4)

        finding = _capacity_recommendation_finding(self._result(recommendation))[0]

        assert finding['severity'] == 'info'
        assert "already at the setting its own measurements support" in finding['title']

    def test_a_setting_above_what_the_run_supports_is_the_loudest(self):
        """Configured higher than anything measured supports is the one
        shape of this finding that is actively costing something."""
        recommendation = compute_capacity_recommendation(
            _plane2(cores_busy=0.5, host=16), _envelope(11), knee=2, builders=4)

        finding = _capacity_recommendation_finding(self._result(recommendation))[0]

        assert finding['severity'] == 'high'
        assert "contend rather than overlap" in finding['title']


class TestRoomToGrowIsAHypothesis:
    """A real timing table refused the first wording.

    On a reconstructed macro-fixed `examples/06` the block said "room for
    2 more builder(s)"; builders 2/4/6/8 then measured 21.6 / 24.2 / 23.5
    / 23.3s - flat inside the run-to-run spread, with no ordering at all.
    The knee is a scheduling answer and `cores_busy` is a whole-run
    average, so both overstate what a contended window absorbs. The block
    keeps naming the constraint; it stopped naming a setting.
    """

    def _finding(self, recommendation):
        result = type('_R', (), {'capacity_recommendation': recommendation})()
        return _capacity_recommendation_finding(result)[0]

    def test_headroom_is_worded_as_a_hypothesis_not_a_setting(self):
        finding = self._finding(compute_capacity_recommendation(
            _plane2(cores_busy=1.0, host=8), _envelope(11), knee=6, builders=2))

        assert "hypothesis to time rather than a setting to apply" in finding['title']

    def test_headroom_carries_the_reason_both_ceilings_are_optimistic(self):
        finding = self._finding(compute_capacity_recommendation(
            _plane2(cores_busy=1.0, host=8), _envelope(11), knee=6, builders=2))

        assert any("Time it before keeping it" in line for line in finding['detail'])

    def test_no_headroom_does_not_carry_the_hedge(self):
        """A run already at its ceiling has no setting to try, so the line
        would be advice about nothing."""
        finding = self._finding(compute_capacity_recommendation(
            _plane2(cores_busy=3.4, host=4), _envelope(11), knee=5, builders=4))

        assert not any("Time it before keeping it" in line for line in finding['detail'])


class TestTheMemoryEnvelopeNoteDoesNotClaimADirectionItCannotShow:
    """UX-145, observed live: *"Memory envelope grew: 0.6 GB -> 0.6 GB
    (+0.0 GB, +0%)"*. A direction the numbers printed beside it do not
    show is the kind of sentence that teaches a reader to stop believing
    the others."""

    def test_a_zero_delta_is_unchanged(self):
        from bga.report.text import memory_envelope_direction

        assert memory_envelope_direction(0.0) == 'unchanged'

    def test_a_delta_that_rounds_to_zero_gb_is_unchanged_too(self):
        """The threshold is the precision the line prints at: claiming
        growth beside `+0.0 GB` is the observed defect."""
        from bga.report.text import memory_envelope_direction

        assert memory_envelope_direction(12.0) == 'unchanged'
        assert memory_envelope_direction(-12.0) == 'unchanged'

    def test_real_growth_and_shrinkage_still_read_as_themselves(self):
        from bga.report.text import memory_envelope_direction

        assert memory_envelope_direction(900.0) == 'grew'
        assert memory_envelope_direction(-900.0) == 'shrank'

    def test_the_renderer_uses_it(self):
        """Testing the rule is not testing that anything applies it."""
        import inspect

        from bga.report import text

        source = inspect.getsource(text)
        assert "memory_envelope_direction(memory_delta['delta_mb'])" in source
