"""The wrapper's stamp is UTC, so parse_timestamp must not depend on TZ (UX-1124)."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PROBE = """
import sys
sys.path.insert(0, "tools")
from bst_log_to_chrome_trace import WrapperTraceConverter
c = WrapperTraceConverter()
a = c.parse_timestamp("2026-10-25 02:59:00,000")
b = c.parse_timestamp("2026-10-25 03:00:00,000")
print(b - a, a)
"""


def _probe(tz):
    out = subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=ROOT,
        env={"PATH": "/usr/bin:/bin", "TZ": tz, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return int(out[0]), int(out[1])


def test_a_dst_end_minute_measures_sixty_seconds_in_berlin():
    delta, _ = _probe("Europe/Berlin")
    assert delta == 60_000_000


def test_the_epoch_is_the_same_in_every_zone():
    assert _probe("Europe/Berlin")[1] == _probe("UTC")[1] == _probe("Asia/Kolkata")[1]
