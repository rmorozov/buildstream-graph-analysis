/* LD_PRELOAD process-lifecycle hook for UX-11's native-build-system
 * tracer - see docs/backlog/scenarios/UX-0011-native-build-system-profiler-tool.md
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
 *
 * UX-45: the END line also carries real, kernel-measured CPU time for
 * the process (getrusage utime/stime, plus cutime/cstime for children it
 * reaped). See append_rusage.
 *
 * UX-46: when BST_TRACE_OPENS is set, this hook additionally interposes
 * open/openat and records the absolute paths a process read, emitting
 * them as OPEN lines at exit. That is what makes "which of this
 * element's declared build dependencies did its sandbox never touch?"
 * answerable - BuildStream stages every dependency into one shared
 * sandbox root, so a command line cannot tell you which element a path
 * came from, but the *set of files opened* can be matched against each
 * artifact's own contents.
 *
 * The interposition is opt-in precisely because it is the invasive part:
 * unlike the lifecycle hooks it runs on a genuinely hot path (a single
 * cmake configure opens thousands of files). It is written to fail
 * silently into "no tracing" rather than to ever break the wrapped
 * build, per this file's own standing requirement.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdarg.h>
#include <string.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>

static pid_t g_pid = 0;
static const char *g_trace_log = NULL;
static const char *g_element = NULL;
/* UX-56: which sandbox this process belongs to. Unlike the element
 * name above it does not depend on the project's build-root layout,
 * so a correlation can relabel a whole sandbox's processes at once
 * when the name collapsed. */
static const char *g_invocation = NULL;

/* ---- UX-46: opened-path recording ------------------------------------
 *
 * Design constraints, in priority order:
 *   1. Never break the wrapped build. Every failure path here degrades
 *      to "record nothing" and lets the real call through.
 *   2. Never recurse. Our own trace writes call open(); a guard flag
 *      keeps them out of the record.
 *   3. Bounded memory and bounded work per call. A cmake configure opens
 *      thousands of files, most of them repeatedly.
 *
 * Paths are deduplicated in-process by a fixed open-addressing hash set
 * and stored in a bump arena, then written once in the destructor -
 * a per-open write() would dominate the traced build's own runtime.
 */
/* UX-57: both were raised ~4x and, more importantly, stopped being a
 * ceiling at all (see flush_open_record). The raise is close to free:
 * both live in .bss, so their pages are anonymous zero pages that are
 * only faulted in when actually written - a process that records 30
 * paths pays for 30 paths no matter how large these are declared. A
 * real examples/06 capture averages 32 unique paths and 1.4 KiB of
 * arena per process (max 149 / 7 KiB), so the common case never comes
 * near either number; the point of raising them is to make a flush
 * rare on the processes that do. */
/* Overridable at compile time so the window-flush path can be
 * exercised for real by a test, rather than only on a build large
 * enough to fill a megabyte of paths. */
#ifndef OPEN_SLOTS
#define OPEN_SLOTS 32768          /* power of two; ~50% max load */
#endif
#ifndef OPEN_ARENA_BYTES
#define OPEN_ARENA_BYTES 1048576  /* 1 MiB of path text per process */
#endif

static int g_record_opens = 0;
static __thread int g_in_hook = 0;
static unsigned long g_open_hashes[OPEN_SLOTS];
static char g_open_arena[OPEN_ARENA_BYTES];
static size_t g_open_arena_used = 0;
static unsigned g_open_unique = 0;
static unsigned g_open_dropped = 0;
static unsigned g_open_part = 0;

typedef int (*open_fn)(const char *, int, ...);
typedef int (*openat_fn)(int, const char *, int, ...);
static open_fn g_real_open = NULL;
static open_fn g_real_open64 = NULL;
static openat_fn g_real_openat = NULL;
static openat_fn g_real_openat64 = NULL;

static void write_open_record(void);

/* UX-57: flush what has been recorded so far and start a new window.
 * The measured alternative was compression: front-coding the arena
 * against the previous path - the only kind available to a streaming
 * hook - buys **1.41x** on a real path set (2.88x if the paths were
 * sorted, which they cannot be here). That moves the ceiling from
 * ~6,000 paths to ~8,500, which is below OPEN_SLOTS anyway, in
 * exchange for a format change and a decoder. Flushing removes the
 * ceiling entirely for the cost of an occasional write(), which is
 * why compression was measured and then not taken.
 *
 * Paths repeated across windows are re-recorded, which is harmless:
 * the parser unions them per element, so the final read set is exact
 * either way. */
static void flush_open_window(void) {
    write_open_record();
    memset(g_open_hashes, 0, sizeof(g_open_hashes));
    g_open_arena_used = 0;
    g_open_unique = 0;
    g_open_part++;
}

static unsigned long path_hash(const char *s) {
    /* FNV-1a. Never returns 0 - 0 marks an empty slot. */
    unsigned long h = 1469598103934665603UL;
    for (; *s; s++) {
        h ^= (unsigned char)*s;
        h *= 1099511628211UL;
    }
    return h ? h : 1;
}

static void record_open(const char *path) {
    if (!g_record_opens || path == NULL || path[0] != '/') {
        /* Relative paths are recorded by their opener's own cwd, which
         * we do not know and which differs per process; only absolute
         * paths can be matched against an artifact's contents. */
        return;
    }
    size_t len = strlen(path);
    if (len + 1 > OPEN_ARENA_BYTES) {
        /* A single path longer than a whole window. Cannot be recorded
         * by any windowing scheme, so it is counted rather than looped
         * on forever. PATH_MAX is 4096; this is unreachable in practice
         * and exists so the retry below is provably terminating. */
        g_open_dropped++;
        return;
    }
    /* Two attempts at most: the second runs against an empty window, in
     * which the path provably fits and a free slot provably exists. */
    for (int attempt = 0; attempt < 2; attempt++) {
        unsigned long h = path_hash(path);
        size_t slot = (size_t)(h & (OPEN_SLOTS - 1));
        for (size_t probe = 0; probe < OPEN_SLOTS; probe++) {
            size_t i = (slot + probe) & (OPEN_SLOTS - 1);
            if (g_open_hashes[i] == h) {
                return;  /* already recorded in this window */
            }
            if (g_open_hashes[i] == 0) {
                if (g_open_arena_used + len + 1 > OPEN_ARENA_BYTES) {
                    break;  /* arena full - flush and retry */
                }
                g_open_hashes[i] = h;
                memcpy(g_open_arena + g_open_arena_used, path, len);
                g_open_arena_used += len;
                g_open_arena[g_open_arena_used++] = '\n';
                g_open_unique++;
                return;
            }
        }
        /* Arena or table full. UX-57: a real freedesktop-sdk build
         * dropped 149,053 opens against 65,101 recorded here - a 70%
         * loss, and UX-46 refuses to draw any conclusion from a
         * truncated read set, so every heavy element was excluded from
         * declared-vs-used analysis. Write the window out and continue
         * instead of dropping. */
        if (attempt == 0) {
            flush_open_window();
        }
    }
    g_open_dropped++;  /* unreachable: kept so a future edit cannot silently lose paths */
}

/* Resolved lazily rather than in the constructor: the constructor may
 * itself run before the loader is ready to serve dlsym on some paths,
 * and a NULL here must mean "pass through", never "crash". */
static void *resolve(const char *name) {
    void *fn = dlsym(RTLD_NEXT, name);
    return fn;
}

int open(const char *path, int flags, ...) {
    mode_t mode = 0;
    if (flags & (O_CREAT | O_TMPFILE)) {
        va_list ap;
        va_start(ap, flags);
        mode = (mode_t)va_arg(ap, int);
        va_end(ap);
    }
    if (g_real_open == NULL) {
        g_real_open = (open_fn)resolve("open");
        if (g_real_open == NULL) {
            errno = ENOSYS;
            return -1;
        }
    }
    if (!g_in_hook) {
        g_in_hook = 1;
        record_open(path);
        g_in_hook = 0;
    }
    return g_real_open(path, flags, mode);
}

int open64(const char *path, int flags, ...) {
    mode_t mode = 0;
    if (flags & (O_CREAT | O_TMPFILE)) {
        va_list ap;
        va_start(ap, flags);
        mode = (mode_t)va_arg(ap, int);
        va_end(ap);
    }
    if (g_real_open64 == NULL) {
        g_real_open64 = (open_fn)resolve("open64");
        if (g_real_open64 == NULL) {
            return open(path, flags, mode);
        }
    }
    if (!g_in_hook) {
        g_in_hook = 1;
        record_open(path);
        g_in_hook = 0;
    }
    return g_real_open64(path, flags, mode);
}

int openat(int dirfd, const char *path, int flags, ...) {
    mode_t mode = 0;
    if (flags & (O_CREAT | O_TMPFILE)) {
        va_list ap;
        va_start(ap, flags);
        mode = (mode_t)va_arg(ap, int);
        va_end(ap);
    }
    if (g_real_openat == NULL) {
        g_real_openat = (openat_fn)resolve("openat");
        if (g_real_openat == NULL) {
            errno = ENOSYS;
            return -1;
        }
    }
    if (!g_in_hook) {
        g_in_hook = 1;
        record_open(path);  /* absolute paths only; dirfd-relative skipped */
        g_in_hook = 0;
    }
    return g_real_openat(dirfd, path, flags, mode);
}

int openat64(int dirfd, const char *path, int flags, ...) {
    mode_t mode = 0;
    if (flags & (O_CREAT | O_TMPFILE)) {
        va_list ap;
        va_start(ap, flags);
        mode = (mode_t)va_arg(ap, int);
        va_end(ap);
    }
    if (g_real_openat64 == NULL) {
        g_real_openat64 = (openat_fn)resolve("openat64");
        if (g_real_openat64 == NULL) {
            return openat(dirfd, path, flags, mode);
        }
    }
    if (!g_in_hook) {
        g_in_hook = 1;
        record_open(path);
        g_in_hook = 0;
    }
    return g_real_openat64(dirfd, path, flags, mode);
}

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
        int n = snprintf(buf, size, " utime=%.6f stime=%.6f maxrss_kb=%ld",
                         timeval_seconds(&self.ru_utime),
                         timeval_seconds(&self.ru_stime),
                         (long)self.ru_maxrss);
        return (n < 0 || (size_t)n >= size) ? 0 : n;
    }
    /* UX-63: ru_maxrss from the same struct already being read. Two
     * traps the consumer has to respect and this function cannot:
     * it is *kilobytes* on Linux (bytes on macOS), and it is a per-
     * process *peak*, not a sample - so summing it across processes
     * overstates any concurrent total, which is the mistake that would
     * make it look like a memory measurement it is not. Emitted in KiB
     * verbatim; the reader converts and refuses to sum. */
    /* UX-379: six more fields out of the struct that is already
     * populated. `UX-63` took `ru_maxrss` on exactly this argument and
     * the rest were left; they are the only measurement bga has of the
     * two axes it otherwise only models - what a process actually read
     * and wrote, and whether it was waiting or being preempted.
     *
     * Self only, unlike `cutime`/`cstime`. Children's CPU is published
     * because a `make` or `sh` wrapper does no work itself and its
     * subtree cost is the interesting figure; these counts are
     * different, because every child is traced too and reports its own,
     * so folding a parent's `RUSAGE_CHILDREN` copy in would count each
     * block and each fault twice.
     *
     * `inblock`/`oublock` are the kernel's 512-byte block-layer counts,
     * emitted verbatim - they are what actually reached the device, so
     * a read served from page cache is genuinely zero and that is the
     * fact worth keeping. The reader converts. */
    int n = snprintf(buf, size,
                     " utime=%.6f stime=%.6f cutime=%.6f cstime=%.6f"
                     " maxrss_kb=%ld cmaxrss_kb=%ld"
                     " inblock=%ld oublock=%ld majflt=%ld minflt=%ld"
                     " nvcsw=%ld nivcsw=%ld",
                     timeval_seconds(&self.ru_utime),
                     timeval_seconds(&self.ru_stime),
                     timeval_seconds(&children.ru_utime),
                     timeval_seconds(&children.ru_stime),
                     (long)self.ru_maxrss, (long)children.ru_maxrss,
                     (long)self.ru_inblock, (long)self.ru_oublock,
                     (long)self.ru_majflt, (long)self.ru_minflt,
                     (long)self.ru_nvcsw, (long)self.ru_nivcsw);
    return (n < 0 || (size_t)n >= size) ? 0 : n;
}

static void write_trace_line(const char *event, double ts, int with_rusage) {
    if (g_trace_log == NULL) {
        return;
    }
    /* UX-46: this function opens the trace log and /proc/self/cmdline
     * through our own interposed open(). Without the guard the hook
     * records its own bookkeeping as though the traced process had read
     * those files, which would then be matched against artifact
     * contents like any other read. */
    int outer = g_in_hook;
    g_in_hook = 1;
    int fd = open(g_trace_log, O_WRONLY | O_APPEND | O_CREAT, 0644);
    if (fd < 0) {
        g_in_hook = outer;
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

    /* UX-379: 160 fitted the six fields `UX-45`/`UX-63` wrote with
     * little to spare; twelve need more. Oversized on purpose -
     * `format_rusage` returns 0 when the line does not fit, which
     * drops *every* field rather than the ones that overflowed. */
    char rusage[384];
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
                       "%s pid=%d ppid=%d ts=%.9f element=%s inv=%s%s cmd=%s\n",
                       event, (int)g_pid, (int)getppid(), ts,
                       g_element ? g_element : "unknown",
                       g_invocation ? g_invocation : "none", rusage, cmdline);
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
    g_in_hook = outer;
}

/* UX-46: one OPEN record per process, listing the unique absolute paths
 * it opened. Written in the destructor as a single write() for the same
 * atomicity reason as write_trace_line, and only when something was
 * recorded - a process that opened nothing emits no record rather than
 * an empty one that would read as "opened nothing" when it may simply
 * have been killed. */
static void write_open_record(void) {
    if (!g_record_opens || g_trace_log == NULL || g_open_unique == 0) {
        return;
    }
    int outer = g_in_hook;
    g_in_hook = 1;
    int fd = open(g_trace_log, O_WRONLY | O_APPEND | O_CREAT, 0644);
    g_in_hook = outer;
    if (fd < 0) {
        return;
    }
    char header[256];
    /* UX-57: `part` distinguishes several windows written by one process
     * (see flush_open_window) from several processes. Appended rather
     * than inserted so a reader of older logs, where it is absent, keeps
     * working. */
    int n = snprintf(header, sizeof(header),
                     "OPENS pid=%d element=%s inv=%s unique=%u dropped=%u part=%u\n",
                     (int)g_pid, g_element ? g_element : "unknown",
                     g_invocation ? g_invocation : "none",
                     g_open_unique, g_open_dropped, g_open_part);
    if (n > 0 && (size_t)n < sizeof(header)) {
        ssize_t w = write(fd, header, (size_t)n);
        (void)w;
        /* The arena is already newline-separated, so the paths go out
         * as one contiguous block. Each is prefixed by nothing: the
         * parser reads `unique` lines following the header. */
        w = write(fd, g_open_arena, g_open_arena_used);
        (void)w;
    }
    close(fd);
}

__attribute__((constructor)) static void bst_trace_start(void) {
    g_trace_log = getenv("BST_TRACE_LOG");
    g_element = getenv("BST_TRACE_ELEMENT");
    g_invocation = getenv("BST_TRACE_INVOCATION");
    /* Non-empty, not merely set: `BST_TRACE_OPENS=` in an env block is
     * how a caller turns a feature *off*, and getenv returns "" for it. */
    const char *opens = getenv("BST_TRACE_OPENS");
    g_record_opens = (opens != NULL && opens[0] != '\0');
    g_pid = getpid();
    /* No rusage on START: a process that has just been exec'd has
     * consumed no CPU worth recording, and emitting a near-zero value
     * would invite it being read as a measurement. */
    write_trace_line("START", monotonic_seconds(), 0);
}

__attribute__((destructor)) static void bst_trace_end(void) {
    write_trace_line("END", monotonic_seconds(), 1);
    write_open_record();
}
