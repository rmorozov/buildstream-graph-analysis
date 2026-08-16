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
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

static pid_t g_pid = 0;
static const char *g_trace_log = NULL;

static double monotonic_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

static void write_trace_line(const char *event, double ts) {
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
    dprintf(fd, "%s pid=%d ppid=%d ts=%.9f cmd=%s\n", event, (int)g_pid, (int)getppid(), ts, cmdline);
    close(fd);
}

__attribute__((constructor)) static void bst_trace_start(void) {
    g_trace_log = getenv("BST_TRACE_LOG");
    g_pid = getpid();
    write_trace_line("START", monotonic_seconds());
}

__attribute__((destructor)) static void bst_trace_end(void) {
    write_trace_line("END", monotonic_seconds());
}
