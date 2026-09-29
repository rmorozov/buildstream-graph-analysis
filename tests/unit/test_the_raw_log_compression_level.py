"""UX-1075: the raw Plane 2 log compresses at gzip level 6, not the
default 9 - 3.1s vs 16.0s at 417MB for 3% more bytes (the audit).
"""

import gzip


class TestTheRawLogCompressesAtLevelSix:
    def test_compress_raw_log_passes_level_six(self, tmp_path, monkeypatch):
        from tools.bga_snapshot import _compress_raw_log

        seen = {}
        real_open = gzip.open

        def spy(*args, **kwargs):
            seen["compresslevel"] = kwargs.get("compresslevel")
            return real_open(*args, **kwargs)

        monkeypatch.setattr(gzip, "open", spy)

        snapshot = tmp_path / "snap"
        snapshot.mkdir()
        (snapshot / "plane2.log").write_bytes(b"abc123" * 500)
        _compress_raw_log(str(snapshot))

        assert seen["compresslevel"] == 6

    def test_round_trips_byte_identical(self, tmp_path):
        from tools.bga_snapshot import _compress_raw_log

        payload = b"the quick brown fox jumps over the lazy dog\n" * 1000
        snapshot = tmp_path / "snap"
        snapshot.mkdir()
        (snapshot / "plane2.log").write_bytes(payload)
        _compress_raw_log(str(snapshot))

        with gzip.open(snapshot / "plane2.log.gz", "rb") as handle:
            assert handle.read() == payload
