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
 * ## Init duties
 *
 * Under BuildStream's `--unshare-pid` this process is pid 1 of the
 * sandbox. Pid 1 has to reap orphans (the `waitpid(-1, __WALL)` loop
 * does that by construction) and has no default signal dispositions -
 * so fatal signals are caught and forwarded to the command's process
 * group rather than silently ignored, which is what would otherwise
 * make a `bst` cancellation hang.
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

/* As pid 1 there are no default dispositions, so a signal this process
 * does not handle is simply discarded - and a `bst` cancellation would
 * then never reach the build. Forwarded to the command's process group
 * so the whole tree goes down together. */
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
         * whole tree at once. */
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

        if (g_degraded) {
            /* Tracing has failed. Keep reaping - as pid 1 that duty does
             * not stop - but issue no further ptrace calls: a tracer
             * that keeps poking after an error is a tracer that can turn
             * one failure into a hung build. */
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
         * program it is supposed to be observing. */
        if (sig == SIGTRAP)
            sig = 0;
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
