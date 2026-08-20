"""UX-161: the stale casd is checkable before the build, and nobody looked.

UX-147 deferred its stale-daemon detection. The gap matters because a
`buildbox-casd` started before the capture was started by a `bst` that
never saw the capture's PATH, so a build reusing it can miss the shim
entirely - and the zero-invocation summary could then only list it as
one of three guesses, after the build had already run.

Detection is keyed on what casd's own argv actually carries, measured:

    ... --jobs=16 /tmp/x/cache/buildstream

the cache directory, as its last positional.
"""
import os

from tools.bst_native_build_tracer import (
    buildstream_cache_dir, detect_stale_casd, format_stale_casd_warning,
)


def _fake_proc(tmp_path, processes, uptime=10_000.0):
    """A `/proc` holding exactly the processes named.

    `processes` is `[(pid, comm, argv, start_ticks)]`.
    """
    root = tmp_path / "proc"
    root.mkdir()
    (root / "uptime").write_text(f"{uptime} 0.0\n")
    for pid, comm, argv, ticks in processes:
        entry = root / str(pid)
        entry.mkdir()
        (entry / "comm").write_text(comm + "\n")
        (entry / "cmdline").write_bytes(b"\0".join(a.encode() for a in argv) + b"\0")
        (entry / "stat").write_text(
            f"{pid} ({comm}) S 1 1 1 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 {ticks} 0\n")
    return str(root)


class TestDetection:
    def test_a_casd_serving_this_cache_is_found(self, tmp_path):
        proc = _fake_proc(tmp_path, [
            (4132, "buildbox-casd",
             ["buildbox-casd", "--jobs=16", "/cache/buildstream"], 0),
        ])
        found = detect_stale_casd("/cache/buildstream", proc_root=proc)
        assert [entry["pid"] for entry in found] == [4132]

    def test_a_casd_serving_a_different_cache_is_not(self, tmp_path):
        """Measured live: a daemon on another cache directory does not
        interfere, and warning about it would be the kind of alarm nobody
        reads by the third capture."""
        proc = _fake_proc(tmp_path, [
            (4132, "buildbox-casd",
             ["buildbox-casd", "--jobs=16", "/other/buildstream"], 0),
        ])
        assert detect_stale_casd("/cache/buildstream", proc_root=proc) == []

    def test_other_processes_are_ignored(self, tmp_path):
        proc = _fake_proc(tmp_path, [
            (10, "bst", ["bst", "build", "/cache/buildstream"], 0),
            (11, "python3", ["python3", "/cache/buildstream"], 0),
        ])
        assert detect_stale_casd("/cache/buildstream", proc_root=proc) == []

    def test_flags_are_not_mistaken_for_the_cache_directory(self, tmp_path):
        """`--bind=unix:/cache/buildstream/...` is a flag, not the positional
        that names the cache."""
        proc = _fake_proc(tmp_path, [
            (4132, "buildbox-casd",
             ["buildbox-casd", "--bind=unix:/cache/buildstream/x.sock",
              "/elsewhere/buildstream"], 0),
        ])
        assert detect_stale_casd("/cache/buildstream", proc_root=proc) == []

    def test_a_relative_or_unnormalised_path_still_matches(self, tmp_path):
        proc = _fake_proc(tmp_path, [
            (4132, "buildbox-casd",
             ["buildbox-casd", "/cache/./buildstream/"], 0),
        ])
        assert len(detect_stale_casd("/cache/buildstream", proc_root=proc)) == 1

    def test_a_quiet_machine_finds_nothing(self, tmp_path):
        assert detect_stale_casd("/cache/buildstream",
                                 proc_root=_fake_proc(tmp_path, [])) == []

    def test_a_process_that_exits_mid_scan_is_not_staleness(self, tmp_path):
        """`/proc` entries vanish under you constantly; that is not a
        finding."""
        proc = _fake_proc(tmp_path, [
            (4132, "buildbox-casd", ["buildbox-casd", "/cache/buildstream"], 0),
        ])
        os.remove(os.path.join(proc, "4132", "cmdline"))
        assert detect_stale_casd("/cache/buildstream", proc_root=proc) == []

    def test_the_age_is_reported(self, tmp_path):
        hz = os.sysconf("SC_CLK_TCK")
        proc = _fake_proc(tmp_path, [
            (4132, "buildbox-casd", ["buildbox-casd", "/cache/buildstream"],
             9_400 * hz),
        ], uptime=10_000.0)
        [entry] = detect_stale_casd("/cache/buildstream", proc_root=proc)
        assert abs(entry["age_s"] - 600.0) < 1.0


class TestTheCacheDirectoryIsResolvedTheWayBstDoes:
    def test_xdg_cache_home_wins_over_the_default(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "nonexistent"))
        assert buildstream_cache_dir() == str(tmp_path / "buildstream")

    def test_a_configured_cachedir_wins_over_both(self, monkeypatch, tmp_path):
        """Anyone with a project big enough to matter has moved the cache
        off the root filesystem, and this is how."""
        config = tmp_path / "config"
        config.mkdir()
        (config / "buildstream.conf").write_text("cachedir: /mnt/big/bstcache\n")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(config))
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        assert buildstream_cache_dir() == "/mnt/big/bstcache"

    def test_it_falls_back_to_the_documented_default(self, monkeypatch, tmp_path):
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "nonexistent"))
        assert buildstream_cache_dir().endswith("/.cache/buildstream")


class TestTheWarning:
    def test_it_is_silent_when_there_is_nothing_to_say(self):
        assert format_stale_casd_warning([]) is None

    def test_it_names_the_pid_and_the_remedy(self):
        text = format_stale_casd_warning(
            [{"pid": 4132, "age_s": 7200.0, "cache_dir": "/cache/buildstream"}])
        assert "pid 4132" in text
        assert "kill 4132" in text
        assert "120m ago" in text

    def test_a_young_daemon_is_reported_in_seconds(self):
        text = format_stale_casd_warning(
            [{"pid": 9, "age_s": 14.0, "cache_dir": "/c"}])
        assert "14s ago" in text


class TestDoctorReportsItsOwnBlindSpot:
    def test_a_quiet_machine_passes(self, monkeypatch):
        import tools.bga_doctor as doctor
        monkeypatch.setattr(
            "tools.bst_native_build_tracer.detect_stale_casd", lambda *a, **k: [])
        assert doctor.check_stale_casd()["status"] == doctor.OK

    def test_a_running_daemon_warns_and_names_the_capture_probes_blind_spot(
            self, monkeypatch):
        """`doctor --capture` isolates HOME (UX-84), so it starts a *fresh*
        daemon and structurally cannot reproduce this. A passing chain
        must not be read as "your next real capture will work"."""
        import tools.bga_doctor as doctor
        monkeypatch.setattr(
            "tools.bst_native_build_tracer.detect_stale_casd",
            lambda *a, **k: [{"pid": 4132, "age_s": 3600.0, "cache_dir": "/c"}])
        found = doctor.check_stale_casd()
        assert found["status"] == doctor.WARN
        assert "4132" in found["summary"]
        assert "isolates HOME" in found["remedy"]
