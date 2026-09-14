"""UX-845 / Direction 20 argument 2: `PoolController` is a client of its
own FIFO, following `cpu_busy_cores` and PSI at 250ms rather than
`make -l`'s one-minute `/proc/loadavg` EMA read only at job start. This
drives `tick()` directly with a scripted `(busy_cores, psi)` series
against a real FIFO, never the daemon thread.
"""
import json
import os
import time

from tools import bst_native_build_tracer as tracer


def _controller(tmp_path, ceiling=4, capacity=4, **kwargs):
    path, fd, tokens = tracer.open_jobserver(ceiling, str(tmp_path))
    assert tokens == ceiling - 1
    ledger = str(tmp_path / "ledger.jsonl")
    pc = tracer.PoolController(fd, ceiling, capacity=capacity,
                               ledger_path=ledger, **kwargs)
    return pc, path, fd, ledger


def _rows(ledger):
    with open(ledger, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


class TestThePoolFollowsBusyCoresWithinOneTick:
    def test_an_overloaded_sample_withdraws_immediately(self, tmp_path):
        pc, path, fd, ledger = _controller(tmp_path)
        assert pc.pool == 3
        row = pc.tick(busy_cores=5.0)
        assert row["action"] == "withdraw"
        assert pc.pool == 2, "one tick, one token - not deferred"
        pc.stop()
        tracer.close_jobserver(path, fd)

    def test_two_low_samples_add_one_token(self, tmp_path):
        pc, path, fd, ledger = _controller(tmp_path)
        pc.tick(busy_cores=5.0)  # pool 3 -> 2, room to add back
        first = pc.tick(busy_cores=0.5)
        assert first["action"] == "hold", "first low sample only starts the streak"
        assert pc.pool == 2
        second = pc.tick(busy_cores=0.5)
        assert second["action"] == "add"
        assert pc.pool == 3, "the very next tick after the streak completes"
        pc.stop()
        tracer.close_jobserver(path, fd)


class TestThePoolNeverCrossesItsBounds:
    def test_withdrawal_never_goes_below_zero(self, tmp_path):
        pc, path, fd, ledger = _controller(tmp_path, ceiling=4)
        for _ in range(10):
            pc.tick(busy_cores=8.0)
        assert pc.pool == 0
        assert all(row["pool"] >= 0 for row in _rows(ledger))
        pc.stop()
        tracer.close_jobserver(path, fd)

    def test_addition_never_goes_above_ceiling_minus_one(self, tmp_path):
        pc, path, fd, ledger = _controller(tmp_path, ceiling=4)
        for _ in range(10):
            pc.tick(busy_cores=0.1)
        assert pc.pool == 3, "the ceiling is N-1, already the starting pool"
        assert all(row["pool"] <= 3 for row in _rows(ledger))
        pc.stop()
        tracer.close_jobserver(path, fd)


class TestTheTwoSampleHysteresisHoldsOnAnOscillatingSeries:
    def test_alternating_low_high_never_adds(self, tmp_path):
        """A streak that resets every other tick never reaches two -
        the defect a `make -l`-style immediate read would have."""
        pc, path, fd, ledger = _controller(tmp_path, ceiling=4)
        pc.tick(busy_cores=8.0)  # pool 3 -> 2
        series = [0.1, 8.0] * 8
        for busy in series:
            pc.tick(busy_cores=busy)
        actions = {row["action"] for row in _rows(ledger)}
        assert "add" not in actions, (
            "the oscillation never held low for two consecutive samples")
        pc.stop()
        tracer.close_jobserver(path, fd)


class TestAHeldTokenIsRecordedRatherThanCrashing:
    def test_an_empty_fifo_on_overload_is_withdraw_held(self, tmp_path):
        pc, path, fd, ledger = _controller(tmp_path, ceiling=4)
        # Drain every physically readable token - as if every client held
        # its own already, the pool's normal running state.
        while True:
            try:
                os.read(fd, 1)
            except BlockingIOError:
                break
        row = pc.tick(busy_cores=8.0)
        assert row["action"] == "withdraw_held"
        assert pc.pool == 3, "nothing was actually read back, so no change"
        pc.stop()
        tracer.close_jobserver(path, fd)

    def test_the_pool_shrinks_once_a_token_is_returned(self, tmp_path):
        """UX-845's Required Fix: a `withdraw_held` tick does nothing, and
        the read is retried next tick while the condition holds - once
        the FIFO has something to read, the withdrawal lands."""
        pc, path, fd, ledger = _controller(tmp_path, ceiling=4)
        while True:
            try:
                os.read(fd, 1)
            except BlockingIOError:
                break
        held = pc.tick(busy_cores=8.0)
        assert held["action"] == "withdraw_held"
        os.write(fd, b"+")  # a client returns its token
        retried = pc.tick(busy_cores=8.0)
        assert retried["action"] == "withdraw"
        assert pc.pool == 2
        pc.stop()
        tracer.close_jobserver(path, fd)


class TestTheLedgerRowsCarryTheSampleThatCausedEachMove:
    def test_busy_cores_and_psi_are_the_values_the_decision_used(self, tmp_path):
        pc, path, fd, ledger = _controller(tmp_path, ceiling=4)
        pc.tick(busy_cores=8.0, psi_some10=None)
        pc.tick(busy_cores=0.7, psi_some10=42.0)  # PSI alone forces a withdraw
        pc.stop()
        rows = _rows(ledger)
        assert rows[0]["busy_cores"] == 8.0 and rows[0]["psi_some10"] is None
        assert rows[0]["action"] == "withdraw"
        assert rows[1]["busy_cores"] == 0.7 and rows[1]["psi_some10"] == 42.0
        assert rows[1]["action"] == "withdraw", "PSI over the bound overrides a low busy reading"
        tracer.close_jobserver(path, fd)


class TestTheFloorNeverAttemptsAWithdrawal:
    """The verifier's edge: `self.pool == 0` must not read the FIFO at
    all, so a stray byte sitting in it (never counted by this
    controller) is neither consumed nor recorded as a move."""

    def test_a_stray_token_at_the_floor_is_left_untouched(self, tmp_path):
        pc, path, fd, ledger = _controller(tmp_path, ceiling=2)  # pool starts at 1
        pc.tick(busy_cores=8.0)  # the one real token withdraws - pool 0
        assert pc.pool == 0
        os.write(fd, b"+")  # a stray byte this controller never credited
        row = pc.tick(busy_cores=8.0)
        assert row["action"] == "hold"
        assert row["reason"] == "pool at floor"
        assert pc.pool == 0
        assert pc.moves == 1, "only the first, real withdrawal counts"
        assert os.read(fd, 1) == b"+", "the stray byte is still there, unread"
        pc.stop()
        tracer.close_jobserver(path, fd)


class TestStopActuallyWaitsForTheThread:
    """The verifier's second edge: a single bounded join can be outlived
    by a tick already in flight; `stopped` must reflect reality, not
    the first timeout."""

    def test_a_slow_tick_in_flight_is_still_caught_by_the_second_join(self, tmp_path):
        path, fd, tokens = tracer.open_jobserver(4, str(tmp_path))
        pc = tracer.PoolController(fd, 4, capacity=4)

        def slow_fake_sample():
            time.sleep(1.5)  # longer than the first join (interval_s + 1.0 = 1.25s)
            return 0.1

        pc._sample_busy_cores = slow_fake_sample
        pc.start()
        time.sleep(0.1)  # let the thread enter the slow tick
        pc.stop()
        assert pc.stopped is True
        assert not pc._thread.is_alive()
        tracer.close_jobserver(path, fd)
