"""UX-1005 track C: `AdmissionBroker` ranks *waiting* shims by slack,
least first, rather than the arrival order the kernel's own FIFO
wakeups would give a raw read. Mirrors `test_the_broker_grants_by_slack.
py`'s own shape (real FIFOs, `_readable` inspects without consuming) -
and the same FIFO `open_jobserver` seeds, per the verifier fix: admission
has no pool of its own, so its own guard uses none either."""
import json
import os

from tools.jobserver.pool import AdmissionBroker, create_jobserver_proxies, open_jobserver


def _readable(fd) -> int:
    held = 0
    while True:
        try:
            if not os.read(fd, 1):
                break
        except BlockingIOError:
            break
        held += 1
    if held:
        os.write(fd, b"+" * held)
    return held


def _broker(tmp_path, elements, plan, pool_size=2):
    global_scratch = str(tmp_path / "global")
    os.makedirs(global_scratch, exist_ok=True)
    _path, global_fd, _tokens = open_jobserver(pool_size, global_scratch)
    proxies_dir = str(tmp_path / "proxies")
    proxy_fds = create_jobserver_proxies(proxies_dir, dict.fromkeys(elements, "make"))
    requests_path = str(tmp_path / "requests.jsonl")
    ledger = str(tmp_path / "ledger.jsonl")
    broker = AdmissionBroker(global_fd, proxy_fds, plan, requests_path, ledger_path=ledger)
    return broker, global_fd, proxy_fds, requests_path, ledger


def _request(requests_path, element, pid, t):
    with open(requests_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"element": element, "pid": pid, "t": t}) + "\n")


def test_a_later_arrival_with_less_slack_is_admitted_first():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        broker, global_fd, proxy_fds, requests_path, ledger = _broker(
            tmp_path, ["early", "late"], {"early": 100, "late": 5}, pool_size=2)
        # "early" arrives first (t=1.0) but has more slack; "late" arrives
        # second (t=2.0) with the least slack - it must be admitted first.
        _request(requests_path, "early", 111, 1.0)
        _request(requests_path, "late", 222, 2.0)

        broker.tick()

        assert _readable(proxy_fds["late"]) == 1, "least slack wins despite arriving later"
        assert _readable(proxy_fds["early"]) == 0
        assert _readable(global_fd) == 0
        rows = [json.loads(line) for line in open(ledger, encoding="utf-8")]
        grants = [row for row in rows if row["event"] == "admission_grant"]
        assert grants[0]["element"] == "late"
        os.close(global_fd)
        for fd in proxy_fds.values():
            os.close(fd)


def test_an_unplanned_element_falls_back_to_arrival_order():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        broker, global_fd, proxy_fds, requests_path, ledger = _broker(
            tmp_path, ["a", "b"], {}, pool_size=2)
        _request(requests_path, "a", 1, 5.0)
        _request(requests_path, "b", 2, 1.0)

        broker.tick()

        assert _readable(proxy_fds["b"]) == 1, "no plan entries - earliest arrival wins"
        assert _readable(proxy_fds["a"]) == 0
        os.close(global_fd)
        for fd in proxy_fds.values():
            os.close(fd)
