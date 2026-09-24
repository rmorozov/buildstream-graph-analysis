"""UX-905: say what a build is waiting on when the machine goes quiet.

A capture that hangs dies at its step timeout with nothing recorded: the
tracer's report is written at exit, and a cancelled job's artifact is
out of a session's reach. This samples the host's busy jiffies every
`--every` seconds; once they stay under `--idle-cores` for
`--quiet-after` seconds it dumps every process's state, kernel wait
channel and command line, the FIFOs each one holds open, and how many
tokens sit unread in each FIFO named `jobserver`. One dump per quiet
episode, to stdout (the job log) and `--out`, led by a `::warning::`.

    python3 -m tools.hang_witness --out capture/hang-witness.log &
"""
import argparse
import fcntl
import os
import stat
import struct
import sys
import termios
import time

_TICKS_PER_S = float(os.sysconf("SC_CLK_TCK"))


def busy_jiffies(proc="/proc") -> int:
    """Host-wide non-idle jiffies: /proc/stat's `cpu` line minus idle and iowait."""
    with open(os.path.join(proc, "stat"), encoding="ascii") as handle:
        fields = [int(v) for v in handle.readline().split()[1:]]
    return sum(fields) - fields[3] - (fields[4] if len(fields) > 4 else 0)


def fifo_tokens(path: str):
    """Bytes unread in the FIFO at `path` (a `/proc/PID/fd/N` link works), or None."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError:
        return None
    try:
        buf = fcntl.ioctl(fd, termios.FIONREAD, struct.pack("i", 0))
        return struct.unpack("i", buf)[0]
    except OSError:
        return None
    finally:
        os.close(fd)


def _read(path: str) -> str:
    try:
        with open(path, "rb") as handle:
            return handle.read().decode("utf-8", "replace")
    except OSError:
        return ""


def process_rows(proc="/proc") -> list:
    """One dict per live process: pid, ppid, state, wchan, argv, FIFOs held."""
    rows = []
    for name in os.listdir(proc):
        if not name.isdigit():
            continue
        base = os.path.join(proc, name)
        status = _read(os.path.join(base, "stat"))
        if not status:
            continue
        after = status.rsplit(")", 1)[-1].split()
        fifos = []
        try:
            fds = os.listdir(os.path.join(base, "fd"))
        except OSError:
            fds = []
        for fd in fds:
            link = os.path.join(base, "fd", fd)
            try:
                if not stat.S_ISFIFO(os.stat(link).st_mode):
                    continue
                target = os.readlink(link)
            except OSError:
                continue
            fifos.append({"fd": int(fd), "target": target, "link": link})
        rows.append({
            "pid": int(name), "ppid": int(after[1]) if len(after) > 1 else 0,
            "state": after[0] if after else "?",
            "wchan": _read(os.path.join(base, "wchan")) or "-",
            "argv": _read(os.path.join(base, "cmdline")).replace("\0", " ").strip(),
            "fifos": fifos,
        })
    return sorted(rows, key=lambda r: r["pid"])


def render(rows: list) -> list:
    """The dump's lines: every process, then every jobserver FIFO's unread tokens."""
    lines = [f"{'pid':>7} {'ppid':>7} st {'wchan':<22} argv"]
    pools = {}
    for row in rows:
        lines.append(f"{row['pid']:>7} {row['ppid']:>7} {row['state']:<2} "
                     f"{row['wchan'][:22]:<22} {row['argv'][:160]}")
        for fifo in row["fifos"]:
            lines.append(f"{'':>19}fd {fifo['fd']} -> {fifo['target']}")
            if "jobserver" in fifo["target"] and fifo["target"] not in pools:
                pools[fifo["target"]] = fifo_tokens(fifo["link"])
    for target, tokens in sorted(pools.items()):
        lines.append(f"jobserver fifo {target}: {tokens} token(s) unread")
    return lines


def watch(every: float, quiet_after: float, idle_cores: float, out, rounds=None) -> int:
    """Sample until killed (or `rounds` samples); returns the dumps written."""
    last, quiet_since, dumped, dumps, n = busy_jiffies(), None, False, 0, 0
    while rounds is None or n < rounds:
        time.sleep(every)
        n += 1
        now = busy_jiffies()
        cores = (now - last) / _TICKS_PER_S / every
        last = now
        if cores >= idle_cores:
            quiet_since, dumped = None, False
            continue
        quiet_since = quiet_since or time.monotonic() - every
        if dumped or time.monotonic() - quiet_since < quiet_after:
            continue
        lines = [f"::warning::hang witness: {cores:.2f} cores busy for "
                 f"{time.monotonic() - quiet_since:.0f}s"] + render(process_rows())
        text = "\n".join(lines) + "\n"
        sys.stdout.write(text)
        sys.stdout.flush()
        if out:
            with open(out, "a", encoding="utf-8") as handle:
                handle.write(text)
        dumped, dumps = True, dumps + 1
    return dumps


def main(argv=None):
    parser = argparse.ArgumentParser(description="dump what a quiet build waits on")
    parser.add_argument("--every", type=float, default=60.0)
    parser.add_argument("--quiet-after", type=float, default=600.0)
    parser.add_argument("--idle-cores", type=float, default=0.25)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    watch(args.every, args.quiet_after, args.idle_cores, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
