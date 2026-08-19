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

/* UX-118: the set of tracees whose attach-stop has already been
 * consumed.
 *
 * A child auto-attached by PTRACE_O_TRACEFORK is stopped with SIGSTOP,
 * and that SIGSTOP is the kernel's attach mechanism rather than a signal
 * the program sent itself. Restarting the tracee with it - which is what
 * passing every non-SIGTRAP signal through does - converts the
 * attach-stop into a real group stop the tracee then has to escape, at
 * two extra ptrace round-trips per process and a CLD_STOPPED the
 * untraced build never produces. Suppressed exactly once per pid, so a
 * SIGSTOP the program really does raise later is still passed through.
 *
 * Open-addressed, fixed size, no allocation: this runs as the sandbox's
 * root process, which may have no allocator worth trusting under memory
 * pressure, and a tracer that can fail to malloc is a tracer that can
 * hang a build. A full table degrades to the old behaviour for the
 * overflowing pid rather than evicting an entry, because a wrong
 * "already seen" is a swallowed signal and a wrong "not seen" costs one
 * group stop.
 */
#define SEEN_SLOTS 8192
static pid_t g_seen[SEEN_SLOTS];

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

/* Returns 1 the first time it is called for `pid`, 0 afterwards. */
static int first_stop_for(pid_t pid)
{
    unsigned long start = (unsigned long)pid * 2654435761UL % SEEN_SLOTS;
    for (unsigned long probe = 0; probe < SEEN_SLOTS; probe++) {
        unsigned long slot = (start + probe) % SEEN_SLOTS;
        if (g_seen[slot] == pid)
            return 0;
        if (g_seen[slot] == 0) {
            g_seen[slot] = pid;
            return 1;
        }
    }
    return 0;  /* table full - the old behaviour, for this pid only */
}

/* A pid that has exited: its slot is freed so a pid namespace which
 * recycles small numbers (every bwrap --unshare-pid sandbox does) does
 * not fill the table or mistake a new process for an old one. */
static void forget_pid(pid_t pid)
{
    unsigned long start = (unsigned long)pid * 2654435761UL % SEEN_SLOTS;
    for (unsigned long probe = 0; probe < SEEN_SLOTS; probe++) {
        unsigned long slot = (start + probe) % SEEN_SLOTS;
        if (g_seen[slot] == pid) {
            g_seen[slot] = 0;
            return;
        }
        if (g_seen[slot] == 0)
            return;
    }
}

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

int main(int argc, char **argv)
{
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
    }
    g_trace_log = getenv("BST_TRACE_LOG");
    g_element = getenv("BST_TRACE_ELEMENT");
    g_invocation = getenv("BST_TRACE_INVOCATION");

    pid_t child = fork();
    if (child < 0) {
        /* Could not even fork: exec the command directly rather than
         * failing the build. Tracing is the optional half. */
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
        if (ptrace(PTRACE_TRACEME, 0, NULL, NULL) != 0) {
            /* No ptrace here (a restrictive Yama policy, or an
             * already-traced process). Run the command untraced, which
             * is the whole fail-open contract. */
            execvp(argv[first], &argv[first]);
            _exit(127);
        }
        raise(SIGSTOP);
        execvp(argv[first], &argv[first]);
        _exit(127);
    }

    g_child = child;
    setpgid(child, child);   /* the parent half of the race above */
    install_signal_forwarding();

    int status = 0;
    if (waitpid(child, &status, __WALL) < 0) {
        degrade("initial-wait-failed");
        return 127;
    }
    if (!WIFSTOPPED(status)) {
        /* The child never reached its SIGSTOP - it failed to exec, and
         * its status is the answer. */
        return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
    }

    long options = PTRACE_O_TRACEFORK | PTRACE_O_TRACEVFORK | PTRACE_O_TRACECLONE
                 | PTRACE_O_TRACEEXEC | PTRACE_O_TRACEEXIT;
    if (ptrace(PTRACE_SETOPTIONS, child, 0, (void *)options) != 0) {
        degrade("setoptions-failed");
        ptrace(PTRACE_DETACH, child, NULL, NULL);
    }
    ptrace(PTRACE_CONT, child, NULL, NULL);

    int child_status = 0;
    int child_seen = 0;
    char cmdline[MAX_CMDLINE];

    for (;;) {
        int wstatus = 0;
        pid_t pid = waitpid(-1, &wstatus, __WALL);
        if (pid < 0) {
            if (errno == EINTR)
                continue;
            break;  /* ECHILD: everything, including reaped orphans, is gone */
        }

        if (WIFEXITED(wstatus) || WIFSIGNALED(wstatus)) {
            forget_pid(pid);
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
         * test until the two paths shared this line. */
        int pass_through = sig;
        if (sig == SIGTRAP)
            pass_through = 0;                       /* ours, not the program's */
        else if (sig == SIGSTOP && first_stop_for(pid))
            pass_through = 0;                       /* UX-118: the attach-stop */

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
             * already stopped and queued for a later waitpid. The set
             * would need bookkeeping to cover a case that cannot arise,
             * since no tracee is ever left stopped by any other path.
             *
             * The pending signal is passed to the detach so a tracee
             * stopped for a real signal still receives it - and only a
             * real one, per `pass_through` above. */
            ptrace(PTRACE_DETACH, pid, NULL, (void *)(long)pass_through);
            continue;
        }

        if (sig == SIGTRAP && event == PTRACE_EVENT_EXEC) {
            read_cmdline(pid, cmdline, sizeof(cmdline));
            write_start(pid, read_ppid(pid), cmdline);
            ptrace(PTRACE_CONT, pid, NULL, NULL);
            continue;
        }
        if (sig == SIGTRAP && event == PTRACE_EVENT_EXIT) {
            unsigned long exit_msg = 0;
            int have_exit = ptrace(PTRACE_GETEVENTMSG, pid, 0, &exit_msg) == 0;
            read_cmdline(pid, cmdline, sizeof(cmdline));
            write_end(pid, read_ppid(pid), cmdline, have_exit, exit_msg);
            ptrace(PTRACE_CONT, pid, NULL, NULL);
            continue;
        }
        if (sig == SIGTRAP && (event == PTRACE_EVENT_FORK
                            || event == PTRACE_EVENT_VFORK
                            || event == PTRACE_EVENT_CLONE)) {
            /* The new child is auto-attached and will announce itself at
             * its own exec-stop; nothing to record here, because a fork
             * without an exec is the same program, not a new one. */
            ptrace(PTRACE_CONT, pid, NULL, NULL);
            continue;
        }

        /* A group-stop or an ordinary signal-delivery-stop: pass the
         * signal through so the tracee behaves exactly as it would
         * untraced. Swallowing it here is how a tracer changes the
         * program it is supposed to be observing.
         *
         * Two exceptions, and only two. A SIGTRAP with no event is ours
         * rather than the program's. And a newly auto-attached child's
         * first stop is the kernel's attach-SIGSTOP (UX-118): passing
         * that back converts an attach-stop into a real group stop,
         * which costs two ptrace round-trips per process and hands the
         * real parent a CLD_STOPPED the untraced build never produces.
         * Suppressed once per pid, so a SIGSTOP the program itself
         * raises later still gets through. Both decisions are made by
         * `pass_through` above, which the degrade path shares. */
        sig = pass_through;
        if (ptrace(PTRACE_CONT, pid, NULL, (void *)(long)sig) != 0 && errno != ESRCH) {
            /* A tracee we cannot resume is a build we are about to hang.
             * Stop tracing entirely and let every remaining stop resolve
             * itself: detaching resumes them, and after this the loop
             * only reaps. ESRCH is ordinary - the tracee died between
             * the wait and the continue - and is not a failure.
             */
            degrade("cont-failed");
            ptrace(PTRACE_DETACH, pid, NULL, NULL);
        }
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
