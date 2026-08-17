/* LD_PRELOAD process-lifecycle hook for UX-11's native-build-system
 * tracer - see docs/scenarios/UX-11-native-build-system-profiler-tool.md
 * for the real prototype this was validated against (119 real trace
 * lines from one `cmake`+`make`+`gcc` element build, real evidence of
 * -j4 concurrency).
 *
 * Records one START line (constructor - fires as the dynamic linker
 * loads this library into a freshly exec'd process) and one END line
 * (destructor - fires as that process exits normally) per traced
 * process, with real wall-clock timestamps from CLOCK_MONOTONIC. This
 * is the *same* underlying kernel monotonic clock for every process on
 * the system, including ones inside a bwrap `--unshare-pid` sandbox
 * (bwrap does not unshare CLONE_NEWTIME by default) - so timestamps
 * from different concurrent processes, even in different sandboxes, are
 * directly comparable on one shared timeline without any extra
 * correlation step.
 *
 * Known, deliberate limitation (see UX-11's "Risk 2" - confirmed real,
 * not hypothetical): LD_PRELOAD only affects dynamically-linked
 * executables. A statically-linked process produces no START/END lines
 * and no error - this hook cannot detect its own absence. Callers must
 * not treat a trace's process list as exhaustive; see
 * tools/bst_native_build_tracer.py's own report output for the
 * user-facing disclaimer this drives.
 *
 * The destructor does not fire if a process is killed by a signal
 * (SIGKILL, or terminated before returning from main abnormally) - such
 * processes appear as an unmatched START with no END in the trace, and
 * tools/bst_native_build_tracer.py's aggregation reports them as
 * "still open" rather than fabricating a duration.
 *
 * The trace log path is read from the BST_TRACE_LOG environment
 * variable at load time (not hardcoded) - a hardcoded path was the
 * actual, confirmed root cause of one dead-end during this design's own
 * real prototype (see UX-11's Deep Experiment Findings), so this is a
 * direct fix for a bug already hit once, not speculative hardening.
 * If BST_TRACE_LOG is unset, this hook is silently inert (no file is
 * opened, no crash) - matches the "never break the wrapped build" design
 * requirement: a build must succeed identically whether or not tracing
 * is active.
 *
 * UX-23: each line also carries `element=<name>` - the owning
 * BuildStream element, injected by tools/native_trace/bwrap_shim.py's
 * own `extract_element_name` (parsed from BuildStream's own real
 * `--dir` bwrap option) as the BST_TRACE_ELEMENT env var, one level
 * removed from this hook itself. Falls back to the literal string
 * "unknown" (never an empty field) when unset - this hook is also used
 * standalone without element tagging (UX-11's own original single-
 * element mode), and every trace line must stay parseable either way.
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>

static pid_t g_pid = 0;
static const char *g_trace_log = NULL;
static const char *g_element = NULL;

static double monotonic_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

static double timeval_seconds(const struct timeval *tv) {
    return (double)tv->tv_sec + (double)tv->tv_usec / 1e6;
}

/* UX-45: real, kernel-measured CPU time for this process, read in the
 * destructor - the one place in the whole system with access to the
 * kernel's own accounting for a process that is about to exit. No
 * sampling, no estimation, and nothing added to any hot path: this runs
 * exactly once per process, beside an open/dprintf/close that already
 * costs far more.
 *
 * RUSAGE_SELF is this process; RUSAGE_CHILDREN is the summed CPU of
 * children it already reaped, which is what makes the figure meaningful
 * for `make` and `sh` wrappers that do no work themselves.
 *
 * A non-zero getrusage return emits the fields as absent rather than as
 * zero. An unmeasured CPU time and a genuinely-zero one are different
 * claims, and conflating them is exactly the failure mode UX-36 was
 * written about.
 */
/* Format the rusage fields into `buf`, returning how many bytes were
 * written (0 if getrusage failed, which emits the fields as absent
 * rather than as zero - an unmeasured CPU time and a genuinely-zero one
 * are different claims, and conflating them is exactly the failure mode
 * UX-36 was written about). */
static int format_rusage(char *buf, size_t size) {
    struct rusage self, children;
    if (getrusage(RUSAGE_SELF, &self) != 0) {
        return 0;
    }
    if (getrusage(RUSAGE_CHILDREN, &children) != 0) {
        int n = snprintf(buf, size, " utime=%.6f stime=%.6f",
                         timeval_seconds(&self.ru_utime),
                         timeval_seconds(&self.ru_stime));
        return (n < 0 || (size_t)n >= size) ? 0 : n;
    }
    int n = snprintf(buf, size,
                     " utime=%.6f stime=%.6f cutime=%.6f cstime=%.6f",
                     timeval_seconds(&self.ru_utime),
                     timeval_seconds(&self.ru_stime),
                     timeval_seconds(&children.ru_utime),
                     timeval_seconds(&children.ru_stime));
    return (n < 0 || (size_t)n >= size) ? 0 : n;
}

static void write_trace_line(const char *event, double ts, int with_rusage) {
    if (g_trace_log == NULL) {
        return;
    }
    int fd = open(g_trace_log, O_WRONLY | O_APPEND | O_CREAT, 0644);
    if (fd < 0) {
        return;
    }
    char cmdline[4096];
    cmdline[0] = '\0';
    int cfd = open("/proc/self/cmdline", O_RDONLY);
    if (cfd >= 0) {
        ssize_t n = read(cfd, cmdline, sizeof(cmdline) - 1);
        close(cfd);
        if (n < 0) {
            n = 0;
        }
        cmdline[n] = '\0';
        for (ssize_t i = 0; i < n; i++) {
            if (cmdline[i] == '\0') {
                cmdline[i] = ' ';
            }
        }
    }

    char rusage[160];
    rusage[0] = '\0';
    if (with_rusage) {
        format_rusage(rusage, sizeof(rusage));
    }

    /* The whole line is composed into one buffer and written with a
     * single write(). This is load-bearing, not tidiness: the log is
     * opened O_APPEND and written concurrently by every traced process
     * in the build, and O_APPEND only guarantees atomicity per write().
     * An earlier version of this function emitted the line as three
     * dprintf calls, and a real 820-process capture came back with
     * three corrupted lines where two processes had interleaved
     * mid-record - producing nonsense element names like
     * `element=lib-c.bstSTART`. One record, one write.
     *
     * The rusage fields sit before `cmd=` because `cmd=` is last: it is
     * the only unquoted free-form field and may contain spaces, so the
     * parser reads it as "everything after cmd=". Anything appended
     * after it would be unparseable. */
    char line[8192];
    int len = snprintf(line, sizeof(line),
                       "%s pid=%d ppid=%d ts=%.9f element=%s%s cmd=%s\n",
                       event, (int)g_pid, (int)getppid(), ts,
                       g_element ? g_element : "unknown", rusage, cmdline);
    if (len > 0) {
        /* Truncated by snprintf (an over-long cmdline) still ends in a
         * newline, so a partial record can never swallow the next one. */
        if ((size_t)len >= sizeof(line)) {
            len = (int)sizeof(line) - 1;
            line[len - 1] = '\n';
        }
        ssize_t written = write(fd, line, (size_t)len);
        (void)written;
    }
    close(fd);
}

__attribute__((constructor)) static void bst_trace_start(void) {
    g_trace_log = getenv("BST_TRACE_LOG");
    g_element = getenv("BST_TRACE_ELEMENT");
    g_pid = getpid();
    /* No rusage on START: a process that has just been exec'd has
     * consumed no CPU worth recording, and emitting a near-zero value
     * would invite it being read as a measurement. */
    write_trace_line("START", monotonic_seconds(), 0);
}

__attribute__((destructor)) static void bst_trace_end(void) {
    write_trace_line("END", monotonic_seconds(), 1);
}
