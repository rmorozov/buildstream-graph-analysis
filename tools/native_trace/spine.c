/* UX-106: a process spine that the dynamic linker cannot hide from.
 *
 * `hook.c` sees a process because the dynamic linker loads it into that
 * process. A fully static executable never invokes the dynamic linker,
 * so the hook is never loaded, records nothing, and - as its own header
 * says - cannot detect its own absence. `UX-105` measured how large
 * that hole can be: every command `examples/01` runs is static busybox,
 * and its Plane 2 capture is empty.
 *
 * This is the complement. It watches from *outside* the process, using
 * ptrace restricted to process events - fork/vfork/clone/exec/exit
 * stops, never per-syscall - which is the one mechanism that meets all
 * three constraints at once:
 *
 *   - a static binary is exactly as visible as any other, because an
 *     exec is an exec;
 *   - no capability is needed: every tracee is this process's own
 *     descendant, which Yama `ptrace_scope=1` permits;
 *   - the cost is a handful of context switches per *process*, not per
 *     syscall, which is what makes it affordable on a build that spawns
 *     127,000 of them.
 *
 * Compiled `-static` at capture time, for the same reason it exists: a
 * dynamically-linked tracer would need its own loader inside a sandbox
 * that may not have one.
 *
 * ## Never break the wrapped build
 *
 * `hook.c`'s standing rule, and harder to keep here because this process
 * sits between BuildStream and the command it asked for. Three things
 * follow, and each is load-bearing:
 *
 *   - **`PTRACE_O_EXITKILL` is deliberately NOT set.** It would kill
 *     every tracee if this tracer died - turning a tracer bug into a
 *     failed build, which is precisely the outcome forbidden. Without
 *     it the kernel auto-detaches on tracer death and the build runs on,
 *     untraced.
 *   - **The exit status is the command's, always.** Whatever happens to
 *     the tracing, this exits with what the traced command exited with,
 *     including the "killed by signal N" convention BuildStream reads.
 *   - **Any tracer-side error degrades rather than aborts**: it writes
 *     one DEGRADED record, stops tracing, and keeps running as a plain
 *     init.
 *
 * ## Where this process actually sits (corrected by UX-119)
 *
 * It is **pid 2**, not pid 1. BuildStream's real bwrap argv carries
 * `--unshare-pid --die-with-parent` and no `--as-pid-1`, so bubblewrap
 * installs its own reaper as pid 1 and everything it launches starts at
 * pid 2. Measured, not assumed:
 *
 *     bwrap --unshare-pid            sh -c 'echo $$'   ->  2
 *     bwrap --unshare-pid --as-pid-1 sh -c 'echo $$'   ->  1
 *
 * This header used to claim pid 1 and to justify its signal handling by
 * pid 1's missing default dispositions. That justification was wrong.
 * The handling is kept anyway, for a reason that survives the
 * correction: forwarding to the command's own process group is how a
 * `bst` cancellation reaches a *tree* rather than only its root, and the
 * measured behaviour is right - a SIGTERM aimed at this process
 * forwards, the command dies, and this process re-raises so its parent
 * sees the same wait status it would have seen untraced.
 *
 * Orphan reaping is bwrap's reaper's job, not ours. The
 * `waitpid(-1, __WALL)` loop still reaps what it is given, which is what
 * a tracer needs regardless of pid.
 *
 * Passing `--as-pid-1` from the shim was considered and rejected: bare
 * bwrap with that flag reports **0** for a command killed by a signal,
 * where without it the same command surfaces 143. Adding the flag would
 * change what BuildStream observes about its own builds, with or without
 * this tracer attached - which is precisely what a capture mechanism
 * must never do.
 *
 * ## What it does not do
 *
 * Opened paths. Those need syscall-level interception, which is the cost
 * this design exists to avoid; `hook.c` still provides them for the
 * processes it can see, and `UX-107`'s per-process provenance says which
 * those were.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define MAX_CMDLINE 4096
#define MAX_LINE 8192

static const char *g_trace_log;
static const char *g_element;
static const char *g_invocation;
static pid_t g_child;
static int g_degraded;

/* UX-130: how a stop is classified, and why there is no table here any
 * more.
 *
 * UX-118 fixed a real bug - a newly auto-attached child's first stop is
 * the kernel's attach-SIGSTOP, and restarting it *with* that signal
 * turns an attach-stop into a real group stop - by *guessing* which
 * SIGSTOP was the attach one: the first per pid, tracked in an
 * 8192-slot open-addressed table. Round 13 found the guess wrong at both
 * ends.
 *
 *   - The direct child's own attach-stop was consumed by the pre-loop
 *     `waitpid` and never entered the table, so the first genuine
 *     SIGSTOP the loop saw for it was classified as the attach-stop and
 *     swallowed - contradicting the comment that said "exactly once per
 *     pid".
 *   - `forget_pid` zeroed its slot instead of tombstoning it, which
 *     breaks the probe chain of an open-addressed table. The hash is a
 *     bijection below pid 8192, so collisions - and therefore broken
 *     chains, swallowed stops and leaked slots - begin exactly at the
 *     127k-pid scale of a real freedesktop-sdk capture.
 *   - Classic ptrace cannot tell a group-stop from a signal-delivery
 *     stop at all: both are `WSTOPSIG == SIGSTOP` with no event. So a
 *     genuinely group-stopped tracee ping-ponged instead of staying
 *     stopped, which is not "behaves exactly as untraced".
 *
 * `PTRACE_SEIZE` removes all three at once rather than patching them.
 * A seized tracee's stops are *typed*: the attach-stop and a group-stop
 * both arrive as `PTRACE_EVENT_STOP`, distinguishable by their signal
 * (SIGTRAP for the attach, one of the four job-control signals for a
 * group-stop), so nothing is guessed and no table is needed. And
 * `PTRACE_LISTEN` is only available under SEIZE - it is what lets a
 * group-stopped tracee *stay* stopped, which is the untraced behaviour
 * the old code could not reproduce.
 */

/* The four signals that put a process in group-stop. A
 * PTRACE_EVENT_STOP carrying one of these is a real group stop; one
 * carrying SIGTRAP is the attach-stop or a PTRACE_INTERRUPT. */
static int is_group_stop_signal(int sig)
{
    return sig == SIGSTOP || sig == SIGTSTP || sig == SIGTTIN || sig == SIGTTOU;
}

/* UX-117: a seam for testing the degrade path, and the only one in this
 * file.
 *
 * The failure that path exists to handle - PTRACE_CONT refusing to
 * resume a live tracee - cannot be provoked from outside the tracer:
 * only the tracer may detach its own tracees, and the errno that matters
 * (anything but ESRCH) is not reachable by any sequence a test can
 * arrange. The alternative to a seam is shipping the worst failure mode
 * this program has - a hung build - with no test at all, which is how it
 * shipped the first time.
 *
 * Zero unless `BST_TRACE_SPINE_DEGRADE_AFTER` is set, read once at
 * startup, and set by nothing in the capture path: `bwrap_shim.py`
 * passes through a fixed list of BST_TRACE_* variables and this is not
 * among them. */
static long g_degrade_after;
static long g_events_seen;

/* UX-128: which restart site to make fail, for the same reason the seam
 * above exists - a PTRACE_CONT that refuses to resume a live tracee
 * cannot be provoked from outside the tracer, and the alternative to a
 * seam is shipping the hang untested. One name per call site
 * ("exec", "exit", "fork", "signal", "attach"); unset means none.
 *
 * UX-141: the list was ("initial", "exec", "exit", "fork", "signal")
 * until UX-130 deleted the `initial` site - SEIZE has no
 * post-SETOPTIONS CONT - and added `attach`, the restart that runs once
 * per auto-attached descendant and therefore more often than all the
 * others combined (~2,000 times on the process storm, ~127k on
 * freedesktop-sdk). Two test lists went on naming `initial`; `resume`
 * matches by `strcmp`, so those runs injected nothing and passed
 * vacuously, while the busiest site had no coverage at all. An unknown
 * name is now rejected at startup rather than silently ignored, so a
 * list that drifts again fails loudly instead of testing nothing.
 *
 * `bwrap_shim.py` passes a fixed list of BST_TRACE_* variables through
 * and this is not among them, so it cannot reach the capture path. */
static const char *g_fail_cont_at;

static const char *const CONT_SITES[] = {
    "exec", "exit", "fork", "signal", "attach", NULL,
};

static double monotonic_now(void)
{
    struct timespec ts;
    /* The same clock `hook.c` reads, so the two record streams share one
     * timeline by construction rather than by correlation. It is also
     * the same clock inside a `--unshare-pid` sandbox: bwrap does not
     * unshare CLONE_NEWTIME by default. */
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0)
        return 0.0;
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

/* One record, one write(). The log is opened O_APPEND and written by
 * every traced build in the run; O_APPEND is atomic per write() only, and
 * `hook.c` learned that the hard way - a real 820-process capture came
 * back with three records interleaved mid-line. */
static void emit(const char *line, size_t len)
{
    if (!g_trace_log)
        return;
    int fd = open(g_trace_log, O_WRONLY | O_APPEND | O_CREAT | O_CLOEXEC, 0644);
    if (fd < 0)
        return;
    ssize_t written = write(fd, line, len);
    (void)written;
    close(fd);
}

/* `/proc/<pid>/cmdline` is NUL-separated; the trace format's `cmd=` is
 * last and free-form, so spaces are safe and quoting is not needed.
 *
 * Read at an exec-stop, which is the whole reason this is trustworthy:
 * the process is stopped by the kernel at that instant, so there is no
 * race against it exec'ing again or exiting - unlike every /proc-polling
 * design, which reads whatever happens to still be there. */
static void read_cmdline(pid_t pid, char *out, size_t size)
{
    char path[64];
    snprintf(path, sizeof(path), "/proc/%d/cmdline", (int)pid);
    out[0] = '\0';
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0)
        return;
    ssize_t n = read(fd, out, size - 1);
    close(fd);
    if (n <= 0) {
        out[0] = '\0';
        return;
    }
    for (ssize_t i = 0; i < n - 1; i++)
        if (out[i] == '\0')
            out[i] = ' ';
    out[n] = '\0';
    /* A trailing NUL turned into a space would leave the record ending
     * in whitespace; harmless but noisy in a diff of two captures. */
    for (ssize_t i = n - 1; i >= 0 && out[i] == ' '; i--)
        out[i] = '\0';
}

/* utime+stime in seconds from `/proc/<pid>/stat` fields 14 and 15.
 *
 * Parsed from the last ')' rather than from the start, because field 2
 * is the executable name in parentheses and may itself contain spaces
 * and parentheses - a comm of "(sh -c)" is legal and would break any
 * field-counting parser that starts at the beginning. */
static int read_cpu_times(pid_t pid, double *utime, double *stime)
{
    char path[64], buf[2048];
    snprintf(path, sizeof(path), "/proc/%d/stat", (int)pid);
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0)
        return 0;
    ssize_t n = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    if (n <= 0)
        return 0;
    buf[n] = '\0';
    char *tail = strrchr(buf, ')');
    if (!tail)
        return 0;
    long ticks = sysconf(_SC_CLK_TCK);
    if (ticks <= 0)
        ticks = 100;
    unsigned long long ut = 0, st = 0;
    /* After ") " comes field 3 (state); utime is field 14 and stime 15,
     * i.e. the 11th and 12th values after the state. */
    int scanned = sscanf(tail + 2,
                         "%*c %*d %*d %*d %*d %*d %*u %*u %*u %*u %*u %llu %llu",
                         &ut, &st);
    if (scanned != 2)
        return 0;
    *utime = (double)ut / (double)ticks;
    *stime = (double)st / (double)ticks;
    return 1;
}

/* Peak resident set, in KiB, from `/proc/<pid>/status`'s VmHWM.
 *
 * Read at the exit-stop, before the process is gone - `getrusage`, which
 * `hook.c` uses, is not available for another process, and the kernel
 * keeps VmHWM until the task is reaped. */
static long read_peak_rss_kb(pid_t pid)
{
    char path[64], buf[4096];
    snprintf(path, sizeof(path), "/proc/%d/status", (int)pid);
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0)
        return -1;
    ssize_t n = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    if (n <= 0)
        return -1;
    buf[n] = '\0';
    char *found = strstr(buf, "VmHWM:");
    if (!found)
        return -1;
    long kb = -1;
    if (sscanf(found + 6, " %ld", &kb) != 1)
        return -1;
    return kb;
}

/* The real parent, from `/proc/<pid>/stat` field 4.
 *
 * Read rather than remembered: a tracee's parent can change (a vforked
 * child re-parented on its parent's exit, an orphan adopted by this
 * process as pid 1), and the record's job is to say who its parent was
 * at the moment it exec'd. Parsed from the last ')' for the same reason
 * `read_cpu_times` is - field 2 is the comm and may contain anything. */
static pid_t read_ppid(pid_t pid)
{
    char path[64], buf[2048];
    snprintf(path, sizeof(path), "/proc/%d/stat", (int)pid);
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0)
        return 0;
    ssize_t n = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    if (n <= 0)
        return 0;
    buf[n] = '\0';
    char *tail = strrchr(buf, ')');
    if (!tail)
        return 0;
    int ppid = 0;
    if (sscanf(tail + 2, "%*c %d", &ppid) != 1)
        return 0;
    return (pid_t)ppid;
}

static void write_start(pid_t pid, pid_t ppid, const char *cmdline)
{
    char line[MAX_LINE];
    int len = snprintf(line, sizeof(line),
                       "START pid=%d ppid=%d ts=%.9f element=%s inv=%s src=spine cmd=%s\n",
                       (int)pid, (int)ppid, monotonic_now(),
                       g_element ? g_element : "unknown",
                       g_invocation ? g_invocation : "none", cmdline);
    if (len <= 0)
        return;
    if ((size_t)len >= sizeof(line)) {
        len = (int)sizeof(line) - 1;
        line[len - 1] = '\n';
    }
    emit(line, (size_t)len);
}

static void write_end(pid_t pid, pid_t ppid, const char *cmdline, int have_exit,
                      unsigned long exit_msg)
{
    double utime = 0.0, stime = 0.0;
    int have_cpu = read_cpu_times(pid, &utime, &stime);
    long rss = read_peak_rss_kb(pid);
    char extra[128];
    extra[0] = '\0';
    /* Same rule as `hook.c`: an unmeasured CPU time and a genuinely-zero
     * one are different claims, so the fields are omitted rather than
     * written as zero when /proc could not be read. */
    if (have_cpu) {
        int n = snprintf(extra, sizeof(extra), " utime=%.6f stime=%.6f", utime, stime);
        if (n > 0 && rss >= 0 && (size_t)n < sizeof(extra))
            snprintf(extra + n, sizeof(extra) - (size_t)n, " maxrss_kb=%ld", rss);
    } else if (rss >= 0) {
        snprintf(extra, sizeof(extra), " maxrss_kb=%ld", rss);
    }
    /* The exit status, from the event message the kernel hands over at
     * the exit-stop - a wait(2)-encoded status, so a process killed by a
     * signal is distinguishable from one that returned that number.
     * `hook.c` has no equivalent: its destructor runs before the process
     * has a status, and does not run at all when one is killed. */
    char exit_field[48];
    exit_field[0] = '\0';
    if (have_exit) {
        int wstatus = (int)exit_msg;
        if (WIFSIGNALED(wstatus))
            snprintf(exit_field, sizeof(exit_field), " exit=signal:%d", WTERMSIG(wstatus));
        else
            snprintf(exit_field, sizeof(exit_field), " exit=%d", WEXITSTATUS(wstatus));
    }
    char line[MAX_LINE];
    int len = snprintf(line, sizeof(line),
                       "END pid=%d ppid=%d ts=%.9f element=%s inv=%s%s%s src=spine cmd=%s\n",
                       (int)pid, (int)ppid, monotonic_now(),
                       g_element ? g_element : "unknown",
                       g_invocation ? g_invocation : "none", extra, exit_field, cmdline);
    if (len <= 0)
        return;
    if ((size_t)len >= sizeof(line)) {
        len = (int)sizeof(line) - 1;
        line[len - 1] = '\n';
    }
    emit(line, (size_t)len);
}

/* Fail open, and say so once. A degraded capture that produced records
 * and then stopped must be distinguishable from one that was never
 * enabled - the same reason `UX-105`'s census exists one layer up. */
static void degrade(const char *reason)
{
    if (g_degraded)
        return;
    g_degraded = 1;
    char line[MAX_LINE];
    int len = snprintf(line, sizeof(line),
                       "DEGRADED ts=%.9f element=%s inv=%s src=spine reason=%s\n",
                       monotonic_now(), g_element ? g_element : "unknown",
                       g_invocation ? g_invocation : "none", reason);
    if (len > 0)
        emit(line, (size_t)len);
}

/* Every PTRACE_CONT in this file goes through here (UX-128).
 *
 * UX-117 guarded exactly one of five restart sites and then reasoned, in
 * a comment, that "no tracee is ever left stopped by any other path, so
 * there is no third case for a set to cover". There were four: the
 * exec-stop, exit-stop and fork-stop restarts each discarded the CONT
 * return value, and so did the initial post-SETOPTIONS restart. A
 * failure at any of them leaves that tracee stopped forever, `waitpid`
 * never reaches ECHILD, and the build hangs - the identical failure mode
 * UX-117 was filed for, one branch over.
 *
 * The guard is therefore a function rather than a repeated three lines,
 * because the defect was that the repetition diverged. On failure:
 * degrade (naming the site, so a report says which restart broke) and
 * detach, which resumes the tracee - after which the loop only reaps.
 *
 * ESRCH is ordinary and not a failure: the tracee died between the wait
 * and the continue. The pending signal goes to the detach as well, so a
 * tracee stopped for a real signal still receives it.
 */
/* UX-143: which signal a detach must carry to leave the tracee as it
 * would have been untraced.
 *
 * A **group-stop** carries one of the job-control signals, and detaching
 * with it re-delivers it, so the process stays stopped - which is the
 * whole point of being group-stopped. Detaching with 0 resumes it
 * instead, silently converting a suspended process into a running one.
 *
 * The tracer's *own* stops - every `PTRACE_EVENT_*`, and the SIGTRAP of
 * an attach or interrupt - carry nothing a program should receive, so
 * they detach with 0. Passing SIGTRAP on would kill an ordinary process
 * that never asked for it.
 */
static int detach_signal(int wstatus)
{
    int event = wstatus >> 16;
    int sig = WSTOPSIG(wstatus);
    /* UX-152: this test comes FIRST, and getting the order wrong is how
     * UX-143 shipped the bug it was filed against. Under SEIZE a
     * group-stop *is* an event-stop - `wstatus >> 16` is
     * `PTRACE_EVENT_STOP` with `WSTOPSIG` carrying the job-control
     * signal (see the SEIZE commentary at the top of this file) - so an
     * `event != 0` short-circuit returns 0 for precisely the case this
     * function exists to handle, on every detach path at once. */
    if (event == PTRACE_EVENT_STOP && is_group_stop_signal(sig))
        return sig;
    if (event != 0 || sig == SIGTRAP)
        return 0;
    return sig;
}

static void resume(pid_t pid, int sig, const char *site)
{
    int failed;
    if (g_fail_cont_at && strcmp(g_fail_cont_at, site) == 0) {
        failed = 1;
        errno = EIO;   /* any errno but ESRCH; see the seam above */
    } else {
        failed = ptrace(PTRACE_CONT, pid, NULL, (void *)(long)sig) != 0;
    }
    if (!failed || errno == ESRCH)
        return;

    char reason[64];
    snprintf(reason, sizeof(reason), "cont-failed-%s", site);
    degrade(reason);
    ptrace(PTRACE_DETACH, pid, NULL, (void *)(long)sig);
}

/* Forwarded to the command's own process group so a cancellation reaches
 * the whole tree rather than only its root.
 *
 * UX-119 predicted this handler would *prevent* a cancellation, since
 * installing it replaces the default terminate disposition on an
 * ordinary (pid 2) process. Measured, it does not: the signal forwards,
 * the command dies of it, and the exit path below re-raises it here, so
 * the parent sees the same wait status either way. The prediction was
 * sound about dispositions and wrong about the outcome, because it did
 * not account for the re-raise. */
static void forward_signal(int signo)
{
    if (g_child > 0)
        kill(-g_child, signo);
}

/* UX-140: undo `install_signal_forwarding` before this process becomes
 * the command. `execvp` resets *caught* signals to their default on its
 * own, so this is belt-and-braces - but the exec can fail, and a process
 * that falls through to `_exit(127)` with a forwarder still installed
 * would be forwarding to a child that no longer exists. */
static void restore_default_signals(void)
{
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = SIG_DFL;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);
    sigaction(SIGHUP, &sa, NULL);
    sigaction(SIGQUIT, &sa, NULL);
}

static void install_signal_forwarding(void)
{
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = forward_signal;
    sigemptyset(&sa.sa_mask);
    /* SA_RESTART so the waitpid loop is not torn apart by a forwarded
     * signal; the loop handles EINTR anyway, but not needing to is
     * cheaper to reason about. */
    sa.sa_flags = SA_RESTART;
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);
    sigaction(SIGHUP, &sa, NULL);
    sigaction(SIGQUIT, &sa, NULL);
}

/* UX-152: `detach_signal` is the whole of the group-stop contract and it
 * shipped inverted, so it needs a test that does not depend on catching a
 * process in state `T`.
 *
 * That end-to-end probe is not reliably writable: when the traced command
 * exits, the survivor's process group is orphaned, and POSIX requires the
 * kernel to send SIGHUP+SIGCONT to an orphaned group containing stopped
 * members. The survivor is therefore resumed by the *kernel* moments
 * after the spine detaches it, whatever signal the detach carried - so
 * sampling `/proc/<pid>/stat` afterwards reads Z or S on a correct spine
 * and on a broken one alike. Measured: identical results from both
 * binaries, which is what sent this back to a decision table.
 *
 * So the decision itself is exposed instead, for synthesized statuses the
 * kernel would produce. Inert unless asked for, same as the three failure
 * seams, and not among the variables `bwrap_shim.py` passes through. */
static int selftest_detach_signal(void)
{
    struct { const char *name; int wstatus; } cases[] = {
        {"group-stop-SIGSTOP",  (PTRACE_EVENT_STOP << 16) | (SIGSTOP << 8) | 0x7f},
        {"group-stop-SIGTSTP",  (PTRACE_EVENT_STOP << 16) | (SIGTSTP << 8) | 0x7f},
        {"group-stop-SIGTTIN",  (PTRACE_EVENT_STOP << 16) | (SIGTTIN << 8) | 0x7f},
        {"group-stop-SIGTTOU",  (PTRACE_EVENT_STOP << 16) | (SIGTTOU << 8) | 0x7f},
        {"attach-stop-SIGTRAP", (PTRACE_EVENT_STOP << 16) | (SIGTRAP << 8) | 0x7f},
        {"exec-event",          (PTRACE_EVENT_EXEC << 16) | (SIGTRAP << 8) | 0x7f},
        {"exit-event",          (PTRACE_EVENT_EXIT << 16) | (SIGTRAP << 8) | 0x7f},
        {"signal-SIGSEGV",      (SIGSEGV << 8) | 0x7f},
        {"signal-SIGTRAP",      (SIGTRAP << 8) | 0x7f},
    };
    for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); i++)
        printf("%s %d\n", cases[i].name, detach_signal(cases[i].wstatus));
    return 0;
}

int main(int argc, char **argv)
{
    {
        const char *selftest = getenv("BST_TRACE_SPINE_SELFTEST");
        if (selftest && strcmp(selftest, "detach-signal") == 0)
            return selftest_detach_signal();
    }
    int first = 1;
    if (argc > 1 && strcmp(argv[1], "--") == 0)
        first = 2;
    if (first >= argc) {
        fprintf(stderr, "usage: spine [--] command [args...]\n");
        return 2;
    }

    {
        const char *after = getenv("BST_TRACE_SPINE_DEGRADE_AFTER");
        g_degrade_after = after && *after ? strtol(after, NULL, 10) : 0;
        const char *site = getenv("BST_TRACE_SPINE_FAIL_CONT_AT");
        g_fail_cont_at = site && *site ? site : NULL;
        if (g_fail_cont_at) {
            int known = 0;
            for (int i = 0; CONT_SITES[i]; i++)
                if (strcmp(g_fail_cont_at, CONT_SITES[i]) == 0)
                    known = 1;
            if (!known) {
                /* UX-141: a name that matches no call site injects
                 * nothing, and a test asking for it passes while
                 * exercising the ordinary path. Two of them did, for a
                 * whole round. */
                fprintf(stderr,
                        "spine: BST_TRACE_SPINE_FAIL_CONT_AT=%s names no "
                        "restart site. Known sites:", g_fail_cont_at);
                for (int i = 0; CONT_SITES[i]; i++)
                    fprintf(stderr, " %s", CONT_SITES[i]);
                fprintf(stderr, "\n");
                return 2;
            }
        }
    }
    g_trace_log = getenv("BST_TRACE_LOG");
    g_element = getenv("BST_TRACE_ELEMENT");
    g_invocation = getenv("BST_TRACE_INVOCATION");

    /* UX-130: the child waits on this pipe until the parent has seized
     * it, which is what replaces `PTRACE_TRACEME` + `raise(SIGSTOP)`.
     *
     * SEIZE is done *by the parent to a running child*, so without a
     * handshake the child could exec before the seize lands and the
     * first exec - the one that names the command - would go unrecorded.
     * A pipe is the whole synchronisation: the child blocks in `read`
     * until the parent closes the write end, and a parent that dies
     * before that still releases it (EOF), rather than wedging the
     * build behind a tracer that is no longer there.
     */
    int ready[2];
    if (pipe(ready) != 0) {
        execvp(argv[first], &argv[first]);
        return 127;
    }

    pid_t child = fork();
    if (child < 0) {
        /* Could not even fork: exec the command directly rather than
         * failing the build. Tracing is the optional half. */
        close(ready[0]);
        close(ready[1]);
        execvp(argv[first], &argv[first]);
        return 127;
    }
    if (child == 0) {
        /* Its own process group, so signals can be forwarded to the
         * whole tree at once. Set on both sides of the fork (UX-119):
         * whichever call runs first wins and the other is a harmless
         * no-op, which closes the window where a signal arriving between
         * `fork` and this line would be forwarded to a process group
         * that does not exist yet and lost to ESRCH. */
        setpgid(0, 0);
        close(ready[1]);
        {
            char go;
            while (read(ready[0], &go, 1) < 0 && errno == EINTR)
                ;                       /* the parent is still seizing us */
        }
        close(ready[0]);
        execvp(argv[first], &argv[first]);
        _exit(127);
    }

    g_child = child;
    setpgid(child, child);   /* the parent half of the race above */
    install_signal_forwarding();
    close(ready[0]);

    long options = PTRACE_O_TRACEFORK | PTRACE_O_TRACEVFORK | PTRACE_O_TRACECLONE
                 | PTRACE_O_TRACEEXEC | PTRACE_O_TRACEEXIT;
    /* UX-140: the seam, same family as BST_TRACE_SPINE_DEGRADE_AFTER and
     * BST_TRACE_SPINE_FAIL_CONT_AT. This branch is taken in every
     * environment without ptrace, and until now nothing could reach it
     * on a machine that has it. */
    int seized = !getenv("BST_TRACE_SPINE_FAIL_SEIZE")
              && ptrace(PTRACE_SEIZE, child, 0, (void *)options) == 0;
    if (!seized) {
        /* No ptrace here - a restrictive Yama policy, a kernel without
         * SEIZE, or an already-traced process. Run the command untraced,
         * which is the fail-open contract this file opens with.
         * Deliberately *not* a fallback to the TRACEME attach: that path
         * is the one whose attach-stop had to be guessed at, and keeping
         * a second, weaker mechanism alive would carry the defects
         * UX-130 exists to delete into every environment where the
         * primary one is unavailable.
         *
         * UX-140: and *exec*, do not wrap. This branch used to `waitpid`
         * and return `128 + WTERMSIG`, which renders a signal death as a
         * normal exit - the exact WIFSIGNALED-vs-WIFEXITED confusion
         * this file's own UX-106 correction documents as wrong, with
         * BuildStream as the parent reading it. It also left a permanent
         * extra process in every sandbox on every machine without
         * ptrace.
         *
         * The child is still blocked on the handshake pipe and has not
         * exec'd, so killing it costs nothing and cannot lose work. What
         * survives is one process that *is* the command, which is what
         * "the tracer is transparent" has to mean. */
        degrade("seize-failed");
        kill(child, SIGKILL);
        int discard = 0;
        while (waitpid(child, &discard, __WALL) < 0 && errno == EINTR)
            ;
        close(ready[1]);
        restore_default_signals();
        execvp(argv[first], &argv[first]);
        return 127;
    }
    close(ready[1]);         /* the child may exec now */

    int child_status = 0;
    int child_seen = 0;
    char cmdline[MAX_CMDLINE];

    /* UX-133: how many more events to take after the command is reaped.
     *
     * The loop used to run to `ECHILD` - every descendant, not just the
     * command - so a build step that leaves a daemon behind
     * (`some-server &`) kept the *element* running until the daemon
     * exited, while untraced, bubblewrap's own reaper owns it and
     * BuildStream moves on. Measured: 30.01s traced against 0.00s
     * untraced for a step whose own work is instant. A tracer that
     * changes when an element finishes has changed the build, which is
     * the one thing this file promises never to do.
     *
     * But exiting the instant the command is reaped throws away events
     * already queued for its descendants - the daemon's own exec-stop is
     * typically among them - and those are real records. So after the
     * command exits the loop switches to `WNOHANG` and keeps handling
     * whatever is *immediately* ready, stopping as soon as nothing is.
     * Survivors are then detached, not killed: `PTRACE_O_EXITKILL` is
     * deliberately unset (see the header), so they carry on untraced
     * exactly as they would have.
     *
     * The cap bounds a pathological tree that could keep the drain fed
     * forever. It is large enough that no real build reaches it and
     * small enough that hitting it costs milliseconds.
     */
#define DRAIN_EVENT_CAP 4096
    long drained = 0;

    for (;;) {
        int wstatus = 0;
        int flags = __WALL | (child_seen ? WNOHANG : 0);
        pid_t pid = waitpid(-1, &wstatus, flags);
        if (pid == 0)
            break;              /* command done, nothing else ready */
        if (pid < 0) {
            if (errno == EINTR)
                continue;
            break;  /* ECHILD: everything, including reaped orphans, is gone */
        }
        if (child_seen && ++drained > DRAIN_EVENT_CAP) {
            /* UX-143: release this one before leaving. The cap used to
             * break here, having already *popped* a stop that the
             * cleanup loop below can never see again - `waitpid` does
             * not re-report a stop it has delivered - so the tracee was
             * left stopped until kernel auto-detach at exit, which is
             * the hang route UX-117/UX-128 exist to close arriving by a
             * new door. Detaching costs one syscall and ends the drain
             * with nothing owed. */
            degrade("drain-cap-reached");
            if (WIFSTOPPED(wstatus))
                ptrace(PTRACE_DETACH, pid, NULL,
                       (void *)(long)detach_signal(wstatus));
            break;
        }

        if (WIFEXITED(wstatus) || WIFSIGNALED(wstatus)) {
            if (pid == child) {
                child_status = wstatus;
                child_seen = 1;
            }
            continue;
        }
        if (!WIFSTOPPED(wstatus))
            continue;

        int sig = WSTOPSIG(wstatus);
        int event = (wstatus >> 16) & 0xff;

        if (g_degrade_after && ++g_events_seen == g_degrade_after)
            degrade("forced-degrade-for-test");

        /* What this tracee should be restarted (or detached) with.
         *
         * Computed here, before the degrade branch, because both paths
         * need the same answer and getting it in only one of them is how
         * the first attempt at UX-117 hung the build it was fixing: the
         * degrade path detached a freshly-attached tracee *with* its
         * attach-SIGSTOP, stopping for real the process it was trying to
         * set free. Measured, not reasoned - the fix hung on its own
         * test until the two paths shared this line.
         *
         * UX-130 made this one line instead of two guesses. Under SEIZE
         * every stop the tracer itself caused is an *event*-stop, so
         * "was this signal ours?" is answered by `event != 0` rather
         * than by pattern-matching SIGTRAP and remembering which
         * SIGSTOPs have been seen. A bare SIGTRAP with no event is now
         * passed through, because under `PTRACE_O_TRACEEXEC` it can only
         * be the program's own - which is what untraced does with it. */
        int pass_through = (event != 0) ? 0 : sig;

        if (g_degraded) {
            /* UX-117: tracing has failed, so detach this tracee and let
             * it run untraced. Keep reaping afterwards - a tracer's
             * `waitpid` loop owes that to whatever it is still given.
             *
             * This branch used to `continue`, on the reasoning that a
             * tracer which keeps poking after an error can turn one
             * failure into a hung build. The reasoning was right and the
             * code was backwards: a tracee popped from waitpid is
             * *stopped*, and skipping it leaves it stopped forever. The
             * loop then waits on tracees that will never move again and
             * exits only on ECHILD, which never comes - the deadlock the
             * header promises never to cause, in the path that exists to
             * prevent one.
             *
             * Detach-on-stop, rather than walking a tracked set at the
             * moment of degrading, because every tracee reaches this
             * branch on its own: one is either running - and
             * PTRACE_O_TRACEEXIT guarantees it stops at exit - or
             * already stopped and queued for a later waitpid.
             *
             * That reasoning holds; the sentence that used to follow it
             * did not. It read "no tracee is ever left stopped by any
             * other path", which was true of the path this comment sits
             * in and false of the four other restart sites, each of which
             * discarded its PTRACE_CONT result and could strand a tracee
             * exactly as UX-117 described (UX-128). Every restart now
             * goes through `resume()`, which degrades and detaches on
             * failure - so the invariant this branch relies on is
             * enforced rather than asserted.
             *
             * The pending signal is passed to the detach so a tracee
             * stopped for a real signal still receives it - and only a
             * real one. `detach_signal`, not `pass_through`: this branch
             * kept its own copy of the rule and therefore kept resuming
             * group-stopped tracees after UX-143 fixed the other two
             * paths (UX-152). One rule, three call sites. */
            ptrace(PTRACE_DETACH, pid, NULL,
                   (void *)(long)detach_signal(wstatus));
            continue;
        }

        if (sig == SIGTRAP && event == PTRACE_EVENT_EXEC) {
            read_cmdline(pid, cmdline, sizeof(cmdline));
            write_start(pid, read_ppid(pid), cmdline);
            resume(pid, 0, "exec");
            continue;
        }
        if (sig == SIGTRAP && event == PTRACE_EVENT_EXIT) {
            unsigned long exit_msg = 0;
            int have_exit = ptrace(PTRACE_GETEVENTMSG, pid, 0, &exit_msg) == 0;
            read_cmdline(pid, cmdline, sizeof(cmdline));
            write_end(pid, read_ppid(pid), cmdline, have_exit, exit_msg);
            resume(pid, 0, "exit");
            continue;
        }
        if (sig == SIGTRAP && (event == PTRACE_EVENT_FORK
                            || event == PTRACE_EVENT_VFORK
                            || event == PTRACE_EVENT_CLONE)) {
            /* The new child is auto-attached and will announce itself at
             * its own exec-stop; nothing to record here, because a fork
             * without an exec is the same program, not a new one. */
            resume(pid, 0, "fork");
            continue;
        }

        if (event == PTRACE_EVENT_STOP) {
            /* UX-130. Two different things arrive here, and under SEIZE
             * they are distinguishable rather than guessed at.
             *
             * A **group-stop** carries one of the four job-control
             * signals. The tracee must *stay* stopped - that is what
             * being group-stopped means, and the old code could not do
             * it: with classic ptrace a group-stop is indistinguishable
             * from a signal-delivery stop, so the tracee was restarted
             * and immediately re-stopped, ping-ponging where untraced it
             * would have sat still. `PTRACE_LISTEN` is the primitive
             * that holds it, and it exists only for seized tracees.
             * When the tracee is later SIGCONT'd the kernel reports
             * another PTRACE_EVENT_STOP, this time with SIGTRAP, which
             * falls through to the restart below.
             *
             * Everything else here is an **attach-stop** (a newly
             * auto-attached child's first stop) or a PTRACE_INTERRUPT
             * stop, both carrying SIGTRAP. These are the tracer's own
             * doing and are restarted with no signal - which is exactly
             * what UX-118 wanted and had to infer from "first SIGSTOP
             * per pid".
             */
            if (is_group_stop_signal(sig)) {
                if (ptrace(PTRACE_LISTEN, pid, NULL, NULL) != 0 && errno != ESRCH) {
                    /* Cannot hold it stopped; resuming it is the wrong
                     * behaviour but a live wrong behaviour, and a tracee
                     * left stopped with no listener is the hang UX-117
                     * and UX-128 exist to prevent. */
                    degrade("listen-failed");
                    ptrace(PTRACE_DETACH, pid, NULL, (void *)(long)sig);
                }
                continue;
            }
            resume(pid, 0, "attach");
            continue;
        }

        /* An ordinary signal-delivery-stop: pass the signal through so
         * the tracee behaves exactly as it would untraced. Swallowing it
         * here is how a tracer changes the program it is supposed to be
         * observing. `pass_through` above decides; the three detach
         * paths use `detach_signal`, which answers the same question for
         * a *stop* rather than a restart (UX-152). */
        resume(pid, pass_through, "signal");
    }

    /* Whatever is still stopped when the drain ends must be released, or
     * it is stopped forever - the hang UX-117/UX-128 exist to prevent,
     * arriving by a new route. Anything still *running* needs nothing:
     * the kernel auto-detaches when this process exits.
     *
     * UX-143: released *with its pending signal*. This detached with 0,
     * which resumes a genuinely group-stopped tracee - one that untraced
     * would have sat still, because sitting still is what being
     * group-stopped means. A tracer that restarts a suspended process
     * has changed the program it is observing, which is the one thing
     * this file promises not to do.
     *
     * The stops this loop can still see are the ones the drain never
     * popped. A stop already delivered to `waitpid` is not re-reported,
     * so it cannot be reached from here - which is why the cap above
     * now releases its own. */
    for (;;) {
        int wstatus = 0;
        pid_t pid = waitpid(-1, &wstatus, __WALL | WNOHANG);
        if (pid <= 0)
            break;
        if (WIFSTOPPED(wstatus))
            ptrace(PTRACE_DETACH, pid, NULL,
                   (void *)(long)detach_signal(wstatus));
    }

    if (!child_seen) {
        degrade("command-status-unobserved");
        return 127;
    }
    if (WIFEXITED(child_status))
        return WEXITSTATUS(child_status);
    if (WIFSIGNALED(child_status)) {
        /* Die the same way the command did, rather than *exiting* with
         * 128+N. A shell renders both as the same number, but the wait
         * status a parent inspects is different: WIFSIGNALED against
         * WIFEXITED. BuildStream is the parent here, so "the traced
         * build's exit status must be what it would have been untraced"
         * has to mean the status, not the shell's rendering of it.
         *
         * Caught earlier by comparing the two through Python's
         * subprocess, which reports a signal death as a negative code
         * and so does not hide the difference the way a shell does:
         * traced 143, untraced -15. */
        int signo = WTERMSIG(child_status);
        signal(signo, SIG_DFL);
        raise(signo);
        /* Only reached if the signal is somehow blocked or ignored. */
        return 128 + signo;
    }
    return 127;
}
