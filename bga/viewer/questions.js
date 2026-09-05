// UX-194 item 3, extracted to data by `UX-199`, grown into a library by
// `UX-204`.
//
// The SQL engine is Perfetto's; these are the questions that kept
// coming up often enough to be worth writing down. They live here
// rather than in `sql.html` because the **export** needs them too:
// `bga view --export` has no server, so it used to strip the link to
// that page and leave nothing in its place - functionality silently
// lost. One source, three renderings: the page, the export, and the
// per-finding investigate buttons that reference entries by `id`.
//
// `{element}` is the one substitution. `trace_context.js` puts a real
// element uid there when a finding names one; `renderQuestions` puts
// one from **this run** there, over the population the page holds.
//
// `UX-369`: it used to put the literal `"core.bst"` - `macro_micro`'s
// element name, in three entries, shipped to every project. A reader
// on any other build copied a query, pasted it into Perfetto and got
// zero rows, with nothing on the page saying which token to change.
// The default is `headline.top_actions[0]` now, which is `core.bst`
// on that one fixture by coincidence rather than by compilation.

import { identify, labelFor } from "./controls.js";

// `UX-210`: **every query says which plane it is asking.**
//
// `bga timeline`'s whole point is that both planes land in one trace,
// and four of the six queries here were written as if it had one track.
// The scoping channel is `slice.category`, which the merged trace
// already carries: `bst-builder` is a Plane 1 element span,
// `native-process` is a Plane 2 process, `bst-invocation` is the build
// itself. Measured on a real capture of `examples/06`: 11 / 663 / 1.
//
// The join key across the planes is `args.element`, which **both** carry
// - so an element's processes are found by the uid the report prints
// rather than by parsing a span's display name or matching a
// `native: ` prefix. That prefix is a *process* name, not a track name,
// which is why the old `track.name like 'native:%'` matched nothing.
// `UX-312`: two things about these strings that a reader has to know
// before editing a query below.
//
// **The arg namespace is `debug.`, not `args.`.** `UX-204` wrote these
// queries against the legacy Chrome JSON trace, where an `args` object
// becomes `args.<key>` in `trace_processor`. `UX-298` made Perfetto's
// own TrackEvent the default format, where the same facts are *debug
// annotations* and land as `debug.<key>` - and nobody re-pointed the
// library. Verified against Perfetto v49.0 on `examples/06`: the keys
// are there, under `debug.`.
//
// **The plane category came back.** `UX-210` scoped every query with
// `slice.category`, which the Chrome converter wrote and the
// TrackEvent emitter did not - `EVENT_CATEGORY_IIDS` was "reserved
// rather than used" until `UX-308` spent it on `failed`. So between
// those rounds all six queries here matched nothing and returned zero
// rows *in silence*, which is the worst way for a canned question to
// be wrong. The emitter tags every slice with its plane now, under
// these same names, so a query saved against the old trace works
// again rather than needing a rewrite.
//
// Matched with `glob` rather than `=` because a slice may carry more
// than one category - a failed Plane 2 process is
// `native-process,failed`, which `= 'native-process'` would miss, and
// missing exactly the failures is the wrong thing to be blind to.
const PLANE_1 = "bst-builder";
const PLANE_2 = "native-process";

export const QUESTIONS = [
  {
    id: "element-time",
    category: "execution",
    plane: "Plane 1",
    title: "Where did the time actually go, per element?",
    // `UX-348`: what this query *answers with*. Declared rather than
    // illustrated: a sample result would be numbers from some other
    // run pasted into this one, and the thing a reader cannot guess
    // from SQL they have not run is which columns come back and what
    // each one holds.
    returns: [
      ["element", "the element uid - the same string this report "
                  + "prints, because both planes tag their slices with it"],
      ["spans", "how many slices that element has on the timeline: one "
                + "per task it ran"],
      ["seconds", "their total duration, which is the figure the "
                  + "attribution table above is made of"],
    ],
    why:
      "Plane 1's element spans, aggregated - scoped to the element " +
      "plane, so Plane 2 command names cannot crowd the answer. The " +
      "figure bga analyze prints in the Attribution table; here to " +
      "cross-check it, or to slice it further.",
    sql: `select extract_arg(s.arg_set_id, 'debug.element') as element,
       count(*) as spans,
       sum(s.dur) / 1e9 as seconds
from slice s
where s.category glob '*bst-builder*'
group by element
order by seconds desc
limit 25;`,
  },
  {
    id: "graph-levels",
    // `dependencies`, not a new category: the level *is* the dependency
    // graph's own decomposition, and `CATEGORIES` is what the page
    // renders - a question outside it draws nowhere.
    category: "dependencies",
    plane: "Plane 1",
    title: "What ran at each level of the dependency graph?",
    // `UX-380`: the keys this asks on are new, and `UX-368`'s rule is
    // that a key nothing asks about is a key nobody finds.
    returns: [
      ["graph_depth", "the level - the longest path in edges from a "
                      + "source, which is what `parallelism.levels` "
                      + "decomposes by"],
      ["elements", "how many distinct elements sit at that level"],
      ["seconds", "their total task duration"],
      ["on_path", "how many of them are on the critical path"],
    ],
    why:
      "Plane 1 only - the level rides the element task, and a Plane 2 " +
      "slice carries no `depth`. The shape of the build rather than " +
      "its timing: a level that is wide and quick is parallelism " +
      "working; one that is narrow and slow is a waist the whole build " +
      "waits on, and the elements in it are where widening the graph " +
      "would pay. Absent on a trace rendered from a snapshot with no " +
      "analysis beside it.",
    // `UX-434`: the annotations are projected in a subquery and grouped
    // by the projected name. Two defects, both found only by running
    // this against a real capture:
    //
    // 1. `group by depth` bound to **`slice.depth`** - the slice's
    //    nesting depth, which every builder slice has as 0 - and not to
    //    the `extract_arg(...) as depth` alias, which it shadows. One
    //    group, and the `depth` printed beside it was whichever row
    //    SQLite happened to keep. `graph_depth` cannot collide.
    // 2. `on_critical_path` is emitted as the **string** `'true'` /
    //    `'false'` (Plane 1's booleans are strings in the arg table), so
    //    `sum(...)` was 0 on every capture, including one where eight of
    //    ten elements were on the path. Compared as the string it is.
    //
    // And counted over **distinct elements**, like the column beside it:
    // an element can produce more than one task in a run - which is why
    // `_plane1_flows` has a last-ending and a first-beginning rule - and
    // summing slices would report a level of one element as two.
    sql: `select graph_depth,
       count(distinct element) as elements,
       sum(dur) / 1e9 as seconds,
       count(distinct case when on_path = 'true' then element end) as on_path
from (select extract_arg(s.arg_set_id, 'debug.depth') as graph_depth,
             extract_arg(s.arg_set_id, 'debug.element') as element,
             extract_arg(s.arg_set_id, 'debug.on_critical_path') as on_path,
             s.dur
      from slice s
      where s.category glob '*bst-builder*'
        and extract_arg(s.arg_set_id, 'debug.depth') is not null)
group by graph_depth
order by graph_depth;`,
  },
  {
    id: "process-storm",
    category: "resources",
    plane: "Plane 2",
    title: "Which elements ran the most processes?",
    why:
      "Plane 2's processes, grouped by the element that ran them. A " +
      "high count with low total time is a process-storm - many short " +
      "execs, the shape examples/08-process-storm exists to show.",
    sql: `select extract_arg(s.arg_set_id, 'debug.element') as element,
       count(*) as processes,
       sum(s.dur) / 1e9 as seconds
from slice s
where s.category glob '*native-process*'
group by element
order by processes desc
limit 25;`,
  },
  {
    id: "sandbox-tax",
    category: "resources",
    plane: "both planes",
    title: "What is the sandbox tax here?",
    why:
      "Time inside an element's Plane 1 span that its own Plane 2 " +
      "processes do not account for: staging, checkout, the sandbox " +
      "itself. The containment is constrained to the same element, so " +
      "another element building in parallel cannot be subtracted from " +
      "this one. Compare with bga correlate's figure.",
    sql: `select e.element,
       e.dur / 1e9 as element_seconds,
       (e.dur - coalesce(sum(n.dur), 0)) / 1e9 as unaccounted_seconds
from (select s.id, s.ts, s.dur,
             extract_arg(s.arg_set_id, 'debug.element') as element
      from slice s where s.category glob '*bst-builder*') e
left join (select s.ts, s.dur,
                  extract_arg(s.arg_set_id, 'debug.element') as element
           from slice s where s.category glob '*native-process*') n
  on n.element = e.element
 and n.ts >= e.ts and n.ts + n.dur <= e.ts + e.dur
group by e.id
order by unaccounted_seconds desc
limit 20;`,
  },
  {
    id: "stalls",
    category: "scheduling",
    plane: "Plane 1",
    title: "Where are the longest stalls?",
    why:
      "Gaps on the element plane: the build was running and nothing " +
      "was building. Windowed over element spans alone - measured " +
      "against every track, thousands of interleaved Plane 2 slices " +
      "close exactly the gaps this question is looking for.",
    sql: `select element, ts, dur,
       lead(ts) over (order by ts) - (ts + dur) as gap_after
from (select extract_arg(s.arg_set_id, 'debug.element') as element,
             s.ts, s.dur
      from slice s where s.category glob '*bst-builder*')
order by gap_after desc
limit 20;`,
  },
  {
    // `UX-469`: the queue the report cannot name. `attribution`'s
    // `resource_wait_us` is one number over the whole build - "time
    // work was ready and the capacity to run it was not free" - and
    // BuildStream's scheduler has several queues with separate limits,
    // so that figure says a queue was full without saying which. The
    // trace carries `debug.resource` now; this is the question it was
    // added for.
    id: "resource-queues",
    category: "scheduling",
    plane: "Plane 1",
    title: "Which scheduler queue was the build waiting in?",
    returns: [
      ["resource", "the queue the tasks held: PROCESS for a build slot, "
                   + "DOWNLOAD for a fetch or pull, UPLOAD for a push, "
                   + "CACHE for a cache query"],
      ["tasks", "how many tasks passed through it"],
      ["elements", "how many distinct elements they belong to"],
      ["seconds", "their total occupancy - the time slots of this queue "
                  + "were held for"],
      ["window_seconds", "wall-clock from the queue's first task starting "
                         + "to its last one finishing"],
      ["mean_in_flight", "occupancy over that window: how many slots of "
                         + "this queue were held at once, on average. Read "
                         + "it against the limit that queue is configured "
                         + "with - at the limit is a saturated queue, well "
                         + "under it is one nothing was waiting on"],
    ],
    why:
      "Plane 1 only - the queue rides the scheduler's task, and a " +
      "Plane 2 process holds no scheduler slot. When the report says " +
      "the biggest wait category is RESOURCE WAIT, this is the " +
      "question that says which resource: raising a limit only helps " +
      "for the queue that was actually full, and the report's single " +
      "figure sums every queue at once.",
    // Projected in a subquery and grouped by the projected name, for
    // `graph-levels`'s reason - and `nullif` on the divisor because a
    // queue whose whole occupancy is one instantaneous task has a zero
    // window, which is a null row rather than a failed query.
    sql: `select resource,
       count(*) as tasks,
       count(distinct element) as elements,
       sum(dur) / 1e9 as seconds,
       (max(ts + dur) - min(ts)) / 1e9 as window_seconds,
       sum(dur) * 1.0 / nullif(max(ts + dur) - min(ts), 0) as mean_in_flight
from (select extract_arg(s.arg_set_id, 'debug.resource') as resource,
             extract_arg(s.arg_set_id, 'debug.element') as element,
             s.ts, s.dur
      from slice s
      where s.category glob '*bst-builder*'
        and extract_arg(s.arg_set_id, 'debug.resource') is not null)
group by resource
order by seconds desc;`,
  },
  {
    id: "element-commands",
    category: "execution",
    plane: "Plane 2",
    title: "What did one element actually execute?",
    why:
      "The micro half of the cycle - the commands Plane 2 recorded " +
      "inside one sandbox, longest first. Selected by the element uid " +
      "both planes carry, not by a lane name.",
    sql: `select s.name as command, s.dur / 1e6 as ms
from slice s
where s.category glob '*native-process*'
  and extract_arg(s.arg_set_id, 'debug.element') = '{element}'
order by s.dur desc
limit 40;`,
  },
  {
    // `UX-433`: the pivot the library had no key for. `element-commands`
    // above groups by `s.name`, which is the whole command line - 14,424
    // near-unique strings on the audited capture - so it answers one row
    // per invocation and cannot answer one per program. `debug.exe` is
    // the key; these two are what it is for.
    id: "cost-by-executable",
    category: "resources",
    plane: "Plane 2",
    title: "Which programs is this build made of?",
    returns: [
      ["exe", "the program, argv stripped - the path as it was exec'd"],
      ["runs", "how many times it ran"],
      ["wall_seconds", "wall time summed over those runs"],
      ["cpu_seconds", "CPU time summed over them, which exceeds wall "
                      + "where they overlapped"],
      ["peak_rss_kb", "the largest single resident set any one of them "
                      + "reached - never a sum, which no moment held"],
    ],
    why:
      "Plane 2 only - the executable rides the process record, and a " +
      "Plane 1 slice is a task rather than a program. The pivot: how " +
      "much of this build is the compiler, how much the linker, how " +
      "much the shell. Wall time says what the build waited " +
      "on and CPU says what it burned - a program whose CPU far exceeds " +
      "its wall ran in parallel with itself, and one whose wall exceeds " +
      "its CPU was waiting. Group on the path rather than the basename " +
      "so a compiler's own `cc1` stays separate from the `cc` that ran " +
      "it; trim it in the query if the coarser answer is the one you " +
      "want.",
    sql: `select exe,
       count(*) as runs,
       sum(dur) / 1e9 as wall_seconds,
       sum(cpu_us) / 1e6 as cpu_seconds,
       max(rss_kb) as peak_rss_kb
from (select extract_arg(s.arg_set_id, 'debug.exe') as exe,
             extract_arg(s.arg_set_id, 'debug.cpu_us') as cpu_us,
             extract_arg(s.arg_set_id, 'debug.max_rss_kb') as rss_kb,
             s.dur
      from slice s
      where s.category glob '*native-process*'
        and extract_arg(s.arg_set_id, 'debug.exe') is not null)
group by exe
order by wall_seconds desc
limit 40;`,
  },
  {
    // `UX-448`: the same pivot inside one sandbox.
    //
    // Drafted with `cost-by-executable` in `UX-433` and dropped rather
    // than shipped unreachable - `UX-368`'s rule is that a question no
    // finding points at is a question nobody arrives at, and at the
    // time no claim was about what an element ran. `latent-heavies`
    // now offers both grains: `element-commands` above lists that
    // element's invocations, and this collapses them to the programs
    // that produced them. On `examples/06`'s captured `app.bst` that is
    // 70 invocations against 5 programs.
    id: "executables-in-element",
    category: "execution",
    plane: "Plane 2",
    title: "Which programs is one element made of?",
    returns: [
      ["exe", "the program, argv stripped - the path as it was exec'd"],
      ["runs", "how many times this element ran it"],
      ["wall_seconds", "wall time summed over those runs"],
      ["cpu_seconds", "CPU time summed over them, which exceeds wall "
                      + "where they overlapped"],
      ["peak_rss_kb", "the largest single resident set any one of them "
                      + "reached - never a sum, which no moment held"],
    ],
    why:
      "The micro half of `cost-by-executable`. A heavy element is "
      + "usually one program run many times, and the question a reader "
      + "who has picked an element asks next is which one - a compiler "
      + "and a shell loop are the same seconds and different fixes. "
      + "`element-commands` answers the same question one row per "
      + "invocation, which is the grain to use when the command lines "
      + "differ in a way that matters; this is the grain to use when "
      + "they do not. Group on the path rather than the basename, for "
      + "the reason `cost-by-executable` gives.",
    sql: `select exe,
       count(*) as runs,
       sum(dur) / 1e9 as wall_seconds,
       sum(cpu_us) / 1e6 as cpu_seconds,
       max(rss_kb) as peak_rss_kb
from (select extract_arg(s.arg_set_id, 'debug.exe') as exe,
             extract_arg(s.arg_set_id, 'debug.cpu_us') as cpu_us,
             extract_arg(s.arg_set_id, 'debug.max_rss_kb') as rss_kb,
             s.dur
      from slice s
      where s.category glob '*native-process*'
        and extract_arg(s.arg_set_id, 'debug.element') = '{element}'
        and extract_arg(s.arg_set_id, 'debug.exe') is not null)
group by exe
order by wall_seconds desc
limit 40;`,
  },
  {
    id: "dependency-wait",
    category: "dependencies",
    plane: "Plane 1",
    title: "What was this element waiting for?",
    why:
      "The elements that finished last before it could start, on the " +
      "element plane only. A long gap here is a dependency shape " +
      "problem rather than a scheduler one - the distinction the " +
      "blast and criticality findings are about.",
    sql: `select element, (ts + dur) / 1e9 as ended_at_seconds
from (select extract_arg(s.arg_set_id, 'debug.element') as element,
             s.ts, s.dur
      from slice s where s.category glob '*bst-builder*')
where ts + dur <= (select min(s.ts) from slice s
                   where s.category glob '*bst-builder*'
                     and extract_arg(s.arg_set_id, 'debug.element') = '{element}')
order by ended_at_seconds desc
limit 15;`,
  },
  {
    id: "time-by-kind",
    category: "execution",
    plane: "Plane 1",
    title: "Which kinds of element cost the most?",
    why:
      "`UX-308` put the element's kind on its Plane 1 slice, so this " +
      "is one group-by rather than a join against the graph. A kind " +
      "that dominates is a question about the build's shape - one " +
      "cmake element is slow, forty of them is a toolchain decision.",
    sql: `select extract_arg(s.arg_set_id, 'debug.element_kind') as kind,
       count(*) as tasks,
       sum(s.dur) / 1e9 as seconds
from slice s
where s.category glob '*bst-builder*'
group by kind
order by seconds desc;`,
  },
  {
    id: "failed-processes",
    category: "execution",
    plane: "Plane 2",
    title: "What failed, and what ran it?",
    why:
      "`UX-308` gives a non-zero exit its own category, so the work " +
      "that failed is one predicate away instead of a scan of every " +
      "Plane 2 command line. The command is `s.name`: `UX-333` untrimmed the " +
      "slice name and dropped the `debug.cmd` this question used to " +
      "read, because the argv's distinguishing part is the file at " +
      "the end and the 120-character cut fell before it.",
    sql: `select extract_arg(s.arg_set_id, 'debug.element') as element,
       extract_arg(s.arg_set_id, 'debug.exit_status') as exit_status,
       s.name as command,
       s.dur / 1e6 as ms
from slice s
where s.category glob '*native-process*'
  and s.category glob '*failed*'
order by ms desc
limit 40;`,
  },
  {
    id: "cpu-versus-wall",
    category: "resources",
    plane: "Plane 2",
    title: "Which elements are waiting rather than computing?",
    why:
      "Plane 2's own `debug.cpu_us` against wall time, per element, " +
      "annotations alone - no containment join, so nothing another " +
      "element did in parallel can be attributed here. A ratio far " +
      "below 1 is a process that waited; far above 1 is one that " +
      "used several cores. This is the sandbox-tax cross-check that " +
      "`bga correlate` publishes, asked of the trace directly.",
    sql: `select extract_arg(s.arg_set_id, 'debug.element') as element,
       sum(extract_arg(s.arg_set_id, 'debug.cpu_us')) / 1e6 as cpu_seconds,
       sum(s.dur) / 1e9 as wall_seconds,
       sum(extract_arg(s.arg_set_id, 'debug.cpu_us')) * 1000.0
         / nullif(sum(s.dur), 0) as cpu_per_wall
from slice s
where s.category glob '*native-process*'
group by element
having cpu_seconds > 0
order by wall_seconds desc
limit 25;`,
  },
  {
    id: "peak-rss",
    category: "resources",
    plane: "Plane 2",
    title: "Which single process wanted the most memory?",
    why:
      "Plane 2's `debug.max_rss_kb` is one process's own lifetime " +
      "peak. It is " +
      "read as a maximum and never summed: two processes peaking at " +
      "different moments never held the sum between them, which is " +
      "the same refusal `compute_peak_memory` makes and the reason " +
      "`UX-310` declined to draw a memory curve.",
    sql: `select extract_arg(s.arg_set_id, 'debug.element') as element,
       max(extract_arg(s.arg_set_id, 'debug.max_rss_kb')) / 1024 as peak_mb,
       s.name as command
from slice s
where s.category glob '*native-process*'
group by element
order by peak_mb desc
limit 25;`,
  },
  {
    id: "waited-on-flow",
    category: "dependencies",
    plane: "Plane 1",
    reads: "flow",
    title: "What did this element wait for, by the graph?",
    why:
      "Plane 1 again, by the graph rather than the clock: `UX-309` " +
      "draws the dependency edges as **flows**, so this is " +
      "the declared graph rather than whatever happened to finish " +
      "first. The timestamp-proximity version of this question is " +
      "`dependency-wait` above; where they disagree, the gap is a " +
      "scheduler question and not a dependency one.",
    sql: `select extract_arg(o.arg_set_id, 'debug.element') as waited_for,
       (o.ts + o.dur) / 1e9 as it_ended_at,
       i.ts / 1e9 as this_started_at,
       (i.ts - (o.ts + o.dur)) / 1e6 as slack_ms
from flow f
join slice o on f.slice_out = o.id
join slice i on f.slice_in = i.id
where o.category glob '*bst-builder*'
  and i.category glob '*bst-builder*'
  and extract_arg(i.arg_set_id, 'debug.element') = '{element}'
order by slack_ms asc
limit 20;`,
  },
  {
    id: "concurrency-curve",
    category: "scheduling",
    plane: "Plane 2",
    reads: "counter",
    title: "How many processes were running at once, over time?",
    why:
      "Plane 2's concurrency as a curve: `UX-310`'s counter track, " +
      "sampled from the same records the " +
      "process census counts. Its peak equals the `max_concurrency` " +
      "the report publishes - by construction, because both read one " +
      "function. Read it against `host cores busy` below: a plateau of " +
      "processes over an idle machine is work that was blocked, not " +
      "work that filled the cores.",
    sql: `select c.ts / 1e9 as seconds, c.value as processes_running
from counter c
join counter_track t on c.track_id = t.id
where t.name = 'traced processes running'
  {window}
order by c.value desc
limit 25;`,
  },
  {
    id: "which-run-is-this",
    category: "scheduling",
    plane: "run",
    title: "Whose build is this, and did it finish?",
    why:
      "`UX-311` puts the run's identity on its own track, so a trace " +
      "that left the machine still says which project, which host " +
      "and which `bga` wrote it. `incomplete_reason` is the one key " +
      "a finished run never emits - its absence is the only thing " +
      "its absence means, and a trace of an interrupted build is " +
      "not a measurement.",
    sql: `select extract_arg(s.arg_set_id, 'debug.run') as run,
       extract_arg(s.arg_set_id, 'debug.project') as project,
       extract_arg(s.arg_set_id, 'debug.host_cpu_count') as cpus,
       extract_arg(s.arg_set_id, 'debug.builders') as builders,
       extract_arg(s.arg_set_id, 'debug.incomplete_reason') as incomplete
from slice s
where s.category glob '*bst-invocation*';`,
  },
];

/** The four the library is organised by, in the order the page shows
 *  them: what the scheduler did, what ran, what waited, what it cost. */
export const CATEGORIES = ["scheduling", "execution", "dependencies", "resources"];

/** One entry by id, or null. The findings reference queries by id so
 *  the button and the page cannot drift (`UX-204`). */
export function byId(id) {
  return QUESTIONS.find((question) => question.id === id) ?? null;
}

/** The entries of one category, in declaration order. */
export function inCategory(category) {
  return QUESTIONS.filter((question) => question.category === category);
}

/**
 * A Copy control for one block of text, with a "\u2713 copied"
 * acknowledgment that reverts.
 *
 * `make` is passed in for the same reason `renderQuestions` takes it:
 * this renders in the served page, in `sql.html` and in the export, and
 * none of the three should own the element factory.
 */
export function copyButton(make, text, deps = {}, noun = "query") {
  // UX-279: what it copies, not that it copies. One function draws two
  // different controls - the SQL a question renders, and a finding's
  // pasteable text - and both read `Copy`, which is the ambiguity the
  // item was reported for. The noun is the caller's, because only the
  // caller knows what it handed over.
  const button = make("button", { type: "button", class: "copy-sql" });
  const label = `Copy ${noun}`;
  button.textContent = label;
  button.setAttribute("data-copy", text);
  button.setAttribute("data-copies", noun);
  button.title = `Copy this ${noun} to the clipboard`;
  button.addEventListener?.("click", () => {
    const clipboard = deps.clipboard
      ?? (typeof navigator !== "undefined" ? navigator.clipboard : null);
    let wrote = false;
    try {
      // `UX-369`: the **attribute**, not the closure. The element
      // picker re-renders a query in place, and a button that copied
      // the text it was built with would hand over the query the
      // reader is no longer looking at - worse than no picker.
      wrote = Boolean(clipboard?.writeText?.(
        button.getAttribute("data-copy") ?? text));
    } catch (error) {
      wrote = false;
    }
    button.textContent = wrote ? "\u2713 copied" : "select and copy";
    deps.setTimeout?.(() => { button.textContent = label; }, 1500)
      ?? (typeof setTimeout !== "undefined"
          && setTimeout(() => { button.textContent = label; }, 1500));
  });
  return button;
}

/** Render the questions as a page section. Used by the export and by
 *  `sql.html`, so the two cannot drift. */
/** `UX-348`: the query the section is worked through, before the
 *  library. Chosen because its answer is the figure the report's own
 *  attribution table is made of, so a reader can check the page against
 *  the timeline with one paste. */
export const WORKED_EXAMPLE = "element-time";

/**
 * `UX-348`: the handoff, and one query worked through.
 *
 * Measured on the exported report when this was filed: 216 px, four
 * `details` holding thirteen queries, **none of them open**, under one
 * paragraph of instructions - the smallest section in its chapter, for
 * the capability the tool is most distinguished by. Nothing on the page
 * showed what a query *returns*, which is the one thing a reader cannot
 * get from SQL they have not run yet.
 *
 * So the section leads with what the handoff is, then one query in
 * full - its sentence, its SQL, a copy button, and the columns that
 * come back - and only then the library. The four category folds stay
 * closed: they are the library, not the pitch.
 *
 * The example's answer is *declared*, never illustrated. A sample
 * result would be some other run's numbers pasted into this one, which
 * is the shape of lie this repository spends most of its guards on.
 */
/**
 * `UX-395`: the tables a canned query needs beyond `slice`, and which
 * trace format carries them.
 *
 * Measured on one snapshot, both formats from the same two logs:
 *
 * ```text
 *                     slices   flows   counters
 * trackevent             826     836        538
 * chrome                 663       0          0
 * ```
 *
 * Two of the questions - `waited-on-flow` and `concurrency-curve` -
 * read exactly what the chrome JSON does not carry, so against one they
 * return zero rows and the reader concludes the build had no
 * concurrency and that nothing waited on anything. That is `UX-107`'s
 * rule at the trace boundary: *nobody could look* rendered as *looked
 * and found nothing*.
 *
 * The declaration is on the query (`reads`), and this says what it
 * costs. The shipped path is unaffected - the page's own handoff is
 * the trackevent protobuf - so the sentence is a caveat on a hand-run
 * `bga timeline --format chrome`, which is where the reader meets it.
 */
export const NEEDS_TRACKEVENT = {
  flow: "the `flow` table",
  counter: "the `counter` and `counter_track` tables",
};

export function requirementLine(question, make) {
  const needs = NEEDS_TRACKEVENT[question?.reads];
  if (!needs) return null;
  const line = make("p", { class: "muted query-needs" });
  line.setAttribute("data-reads", question.reads);
  line.textContent =
    `Needs a trackevent trace: this reads ${needs}, which `
    + "`bga timeline --format chrome` does not write. Against the "
    + "legacy JSON it returns no rows - which is the format missing "
    + "the structure, not the build lacking it.";
  return line;
}

/**
 * `UX-431`: what the dependency graph's edges became, in the section
 * that sends the reader to look for them.
 *
 * The arrows are the answer to "why did this start when it did", and on
 * a mostly-cached build there are none: measured on two real captures of
 * `examples/06`, 34 edges produced 0 flows on the cached build and 10 on
 * the full rebuild. Neither number reached this page, so the reader met
 * an empty timeline and no reason - and the render result's own counter
 * said nothing had been dropped, because it watched one of the two doors.
 *
 * Rendered whenever the run has edges at all, including the run that drew
 * every one of them: a sentence that appears only on loss teaches the
 * reader that its absence means nothing was lost.
 */
function flowAccounting(make, options) {
  const losses = options.flowLosses;
  const edges = Number(losses?.edges) || 0;
  if (!options.hasTimeline || !edges) return null;
  const drawn = Number(losses.drawn) || 0;
  const parts = [`${drawn} of ${edges} dependency edges are drawn as `
                 + `arrows in this trace.`];
  for (const [reason, sentence] of Object.entries(LOSS_SENTENCES)) {
    const count = Number(losses[reason]) || 0;
    if (count) parts.push(`${count} are not: ${sentence}.`);
  }
  const node = make("p", { class: "muted",
                           "data-flow-accounting": String(edges - drawn) });
  node.textContent = parts.join(" ");
  return node;
}

/**
 * One sentence per reason an edge produced no arrow. The keys are
 * `FLOW_LOSS_REASONS` in `tools/bga_timeline.py`, which is what writes
 * them; a key that arrives without a sentence here is simply not named,
 * rather than printed as a bare identifier at the reader.
 */
const LOSS_SENTENCES = {
  no_task: "one end of the edge built nothing in this run, because it "
    + "was cached or built earlier, so there is no span to draw from",
  out_of_order: "the two spans do not begin in the dependency's order, "
    + "so an arrow would point the wrong way",
};

export function renderQuestions(make, options = {}) {
  const section = make("section", { "data-section": "perfetto-questions",
                                    id: "perfetto-questions" });
  section.append(make("h2", {}, "Questions worth asking in Perfetto"));
  // `UX-650`: **unmapped, deliberately.** The library's own titles span
  // every role - per-element time (R1), what one element executed (R2),
  // what ran at each level of the graph (R3), whether the run finished
  // (R4), the peak-memory process (R5). A section that is seventeen
  // readers' questions has no reader, which is why `UX-643` left
  // `findings` alone for the same shape.
  const intro = make("p", { class: "muted" });
  // `UX-364`: what this run's trace actually carries, from
  // `run.trace_planes`, which is the renderer's own answer. This
  // sentence used to open "Both planes of this run land in one trace"
  // unconditionally - on a Plane 1 capture that is a promise of process
  // lanes the reader will not find, three sections from `UX-362`'s
  // absence sentence saying the plane was never captured.
  const planes = options.tracePlanes || [];
  intro.setAttribute("data-planes", planes.join("+") || "none");
  // Three shapes, not two. The first draft branched on the planes and
  // kept the old "lands in this run's trace" opener for the other
  // side - which then told the two fixtures with **no** trace that
  // their element spans were in one. Trading one false claim for
  // another is what a measurement catches and a reading does not.
  // `UX-545`: two absences, and the page said the wrong one. `export()`
  // writes `timeline_recipe` only for a timeline it rendered and
  // refused, so that key is what tells a ceiling apart from a snapshot
  // that never had a build log - and only the second is a reason to
  // capture again.
  const refused = options.hasTimeline ? null : options.timelineRecipe;
  if (refused) {
    intro.setAttribute("data-omitted", "refused");
    intro.textContent =
      `This file has the build log and refused the timeline: `
      + `${options.timelineOmitted}. Capturing again refuses the same `
      + `way; run \`${refused.command}\` instead. ${refused.note} The `
      + `queries below are what to ask it there.`;
  } else if (!options.hasTimeline) {
    intro.textContent =
      "This snapshot carries no build log, so there is no timeline to "
      + "open here - a capture made with `bga capture` records one, and "
      + "`bga timeline` writes the trace. The queries below are what to "
      + "ask it once there is one.";
  } else {
    // One copy of the how-to-open half, so the two trace shapes differ
    // only where they actually differ - and so the button's name stays
    // a contiguous string that `UX-326`'s guard can read out of the
    // source and match against the control `index.html` draws.
    const openIt =
      " Open it with \u201cOpen timeline in Perfetto\u201d at the top of "
      + "this page, then Query (SQL), and paste one of these.";
    intro.textContent = (planes.includes("2")
      ? "Both planes of this run land in one trace: Plane 1's element "
        + "spans and Plane 2's process lanes, on one clock, joined by "
        + "the element uid this report prints."
      : "Plane 1's element spans land in this run's trace - one span "
        + "per task, on the build's own clock. Plane 2 is not in it, so "
        + "the queries below that read process lanes return nothing "
        + "here and the ones scoped to Plane 1 answer.") + openIt;
    // `UX-530`: and *why* it is not in it. The export degrades before
    // it refuses, and a narrowed page that does not say so reads as a
    // Plane 1 capture - which is a fact about the build, not about
    // this file's ceilings.
    if (options.timelineDegraded) {
      intro.setAttribute("data-degraded", "true");
      intro.textContent = `${options.timelineDegraded} ${intro.textContent}`;
    }
  }
  section.append(intro);
  const accounting = flowAccounting(make, options);
  if (accounting) section.append(accounting);
  // `UX-369`: the element these queries ask about, and the control
  // that swaps it. Before the worked example, because the example is
  // one of the queries the choice applies to.
  const chosen = elementPicker(section, make, options);
  const worked = byId(WORKED_EXAMPLE);
  if (worked) section.append(workedExample(worked, make, chosen));
  for (const category of CATEGORIES) {
    const entries = inCategory(category);
    if (!entries.length) continue;
    // UX-209 item 4: one `<details>` per category, collapsed - with the
    // full SQL still in the DOM, because Ctrl-F must keep finding it
    // and the export must keep carrying it.
    const fold = make("details", { class: "question-group",
                                   "data-category": category,
                                   // UX-211: nameable, so "the query I
                                   // had open" travels in the link.
                                   "data-fold": `questions-${category}` });
    const label = make("summary", { class: "category" });
    label.textContent = `${category} (${entries.length})`;
    fold.append(label);
    section.append(fold);
    for (const question of entries) {
      const heading = make("h4", {});
      heading.setAttribute("data-query-id", question.id);
      heading.textContent = question.title;
      const why = make("p", { class: "muted" });
      why.textContent = question.why;
      const needs = requirementLine(question, make);
      fold.append(heading, why, ...(needs ? [needs] : []),
                  ...sqlBlock(question, make, chosen));
    }
  }
  return section;
}

//: `UX-527`: how many of the population the control draws at once.
//: The jump box's own limit (`nav.js`'s `matches`), because this is the
//: same act - type part of a uid, get the few that match.
const PICKER_SHOWN = 8;

/**
 * `UX-369`: which element the three element-scoped queries ask about.
 *
 * The smallest honest query builder: one substitution, over the
 * population the page already holds. `options.elements` is this run's
 * element uids and `options.element` the default - `app.js` reads both
 * from the payload, so `sql.html`, which has no run behind it, gets no
 * control and renders the token instead.
 *
 * `UX-527`: a search box, not a menu. This was the only `<select>` on
 * the page whose options were the project - 4,002 of them on a
 * 4,002-element run, 4,119 of that page's 8,953 DOM elements - and a
 * 4,002-entry dropdown is not a control anyone can use. The population
 * it reaches is unchanged; what it *draws* is the eight that match.
 *
 * Returns the element chosen at render time, so the initial SQL and
 * the re-render agree on where they started.
 */
function elementPicker(section, make, options) {
  const asks = QUESTIONS.filter(takesElement).length;
  const population = (options.elements ?? []).filter(Boolean);
  const chosen = population.includes(options.element)
    ? options.element : (population[0] ?? null);
  if (!asks) return chosen;

  const lead = `${asks} of the queries below ask about one element. `;
  const box = make("div", { class: "query-element",
                            "data-control": "query-element" });
  const note = make("p", { class: "muted" });
  if (!population.length) {
    // No run behind this page. Saying so is the point: the token is
    // visible in the SQL below, and this says what to put there
    // rather than leaving a reader to infer it from zero rows.
    note.textContent = `${lead}Replace ${ELEMENT_TOKEN} with an element `
                     + "uid from your own report.";
    box.append(note);
    section.append(box);
    return null;
  }
  // `labelFor`, not `make("label", { for: ... })`: `format.js`'s `el`
  // assigns any name without a hyphen as a **property**, and a label's
  // reflecting property is `htmlFor` - so `for` lands nowhere and
  // Chromium reports `FormLabelHasNeitherForNorNestedInput`. Measured
  // by `test_the_console_stays_clean.py` on the golden export, which
  // is `UX-317`'s defect one property over. This is also the seam that
  // uniquifies the id, so two runs of the picker in one document
  // cannot collide.
  const label = make("label", {}, "Ask about element");
  const list = make("datalist", {});
  const listId = identify(list, "query-element-list");
  const search = make("input", {
    type: "text", class: "table-filter",
    autocomplete: "off", "data-role": "query-element",
    "data-population": String(population.length),
    "aria-label": "Ask about element",
    placeholder: "type part of an element uid" });
  // `setAttribute`, for `labelFor`'s reason one property over: `el`
  // assigns any unhyphenated name as a property and `input.list` is
  // read-only, so `{ list: id }` throws inside the module and takes the
  // section with it. Measured - the `<code>` blocks stopped rendering.
  search.setAttribute("list", listId);
  search.value = chosen ?? "";
  search.setAttribute("value", chosen ?? "");
  labelFor(label, search, "query-element");
  // The matched few, redrawn on every keystroke. `includes`, not a
  // prefix: an element is `layer07/mod123.bst` and the part a reader
  // remembers is rarely the layer.
  const fill = (typed) => {
    const needle = String(typed ?? "").trim().toLowerCase();
    for (const node of [...(list.children ?? [])]) node.remove?.();
    const hits = needle
      ? population.filter((uid) => uid.toLowerCase().includes(needle))
      : population;
    for (const uid of hits.slice(0, PICKER_SHOWN)) {
      list.append(make("option", { value: uid }, uid));
    }
  };
  fill("");
  note.textContent = `${lead}Type any part of a uid to search this run's `
                   + `${population.length} elements; the box offers the `
                   + `first ${PICKER_SHOWN} that match. The default is the `
                   + "one the report's first action names.";
  box.append(label, search, list, note);
  section.append(box);
  const applyTyped = () => {
    fill(search.value);
    // Only a uid this run has reaches the query: a half-typed name is a
    // reader still typing, not a request to substitute nothing.
    if (population.includes(search.value)) applyElement(section, search.value);
  };
  search.addEventListener?.("input", applyTyped);
  search.addEventListener?.("change", applyTyped);
  return chosen;
}

/**
 * `[<pre><code>, <button>]` for one query, aimed at `element`.
 *
 * UX-208 item 3: every rendered SQL block copies, with an
 * acknowledgment - a query you have to select by hand is a query most
 * readers retype wrongly. `UX-369` added the tag both nodes carry:
 * the display and the payload are two places the same query is
 * written, and a picker that moves one is a picker that lies.
 */
function sqlBlock(question, make, element) {
  const block = make("pre", {});
  const code = make("code", { "data-sql-for": question.id });
  code.textContent = renderedSql(question, element);
  block.append(code);
  const copy = copyButton(make, code.textContent);
  copy.setAttribute("data-sql-for", question.id);
  return [block, copy];
}

/** Re-render every element-scoped query in `section` for `element`.
 *  The `<code>` a reader reads and the `data-copy` a reader pastes,
 *  from the one call, because they are one query. */
function applyElement(section, element) {
  for (const node of section.querySelectorAll?.("[data-sql-for]") ?? []) {
    const entry = byId(node.getAttribute("data-sql-for"));
    if (!entry || !takesElement(entry)) continue;
    const sql = renderedSql(entry, element);
    if (String(node.tagName).toLowerCase() === "button") {
      node.setAttribute("data-copy", sql);
    } else {
      node.textContent = sql;
    }
  }
}

/**
 * `UX-348`: one question, open, with the shape of its answer.
 *
 * Not a `details`: the acceptance is that a reader meets a worked
 * example *before* any fold, and a fold that happens to be open is one
 * click from being the closed thing this item was filed about.
 */
function workedExample(question, make, element = null) {
  const box = make("div", { class: "worked-example",
                            "data-worked": question.id });
  box.append(make("p", { class: "worked-lead" },
                  "One of them, worked through:"));
  const heading = make("h3", {});
  heading.setAttribute("data-query-id", question.id);
  heading.textContent = question.title;
  const why = make("p", { class: "muted" });
  why.textContent = question.why;
  const needs = requirementLine(question, make);
  box.append(heading, why, ...(needs ? [needs] : []),
             ...sqlBlock(question, make, element));
  const returns = question.returns ?? [];
  if (returns.length) {
    box.append(make("p", { class: "muted" },
                    `What comes back: ${returns.length} columns, one row `
                    + "per element."));
    const list = make("dl", { class: "pairs", "data-role": "answer-shape" });
    for (const [column, sentence] of returns) {
      const term = make("dt", {});
      term.textContent = column;
      const value = make("dd", { class: "muted" });
      value.textContent = sentence;
      list.append(term, value);
    }
    box.append(list);
  }
  return box;
}

/** The one substitution, as a name rather than as a literal in four
 *  places - `takesElement` and the re-render below both need it. */
export const ELEMENT_TOKEN = "{element}";

/** `UX-676`: the second, and the last. A `underutilized_intervals` row
 *  points at a library entry and a time range, so the entry needs a
 *  place to put the range - a declared predicate placeholder, not
 *  string surgery on somebody else's `where`. Renders to nothing when
 *  no bounds are given, so the un-bounded query is byte-identical to
 *  what it was before this item. */
export const WINDOW_TOKEN = "{window}";

/** Whether this entry can be aimed at one window. */
export function takesWindow(question) {
  return String(question?.sql ?? "").includes(WINDOW_TOKEN);
}

/** Whether this entry asks about one element.
 *  Four of the seventeen questions do. */
export function takesElement(question) {
  return String(question?.sql ?? "").includes(ELEMENT_TOKEN);
}

/**
 * The query as the page shows it, aimed at `element`.
 *
 * `UX-369`: with no element, the **token** is what renders - not the
 * empty string it used to collapse to when an entry had no `example`.
 * A visible `{element}` says there is a value to choose; `= ''` says
 * the query is finished and returns nothing, which is the failure this
 * item was filed for happening more quietly.
 */
export function renderedSql(question, element = null, bounds = null) {
  const target = element ?? question?.example ?? ELEMENT_TOKEN;
  const start = Number(bounds?.start_ns);
  const end = Number(bounds?.end_ns);
  // `UX-676`: an incomplete pair renders the token, for `UX-369`'s
  // reason one line up - a query that silently lost its window returns
  // the whole build and looks like an answer.
  const window = (Number.isFinite(start) && Number.isFinite(end))
    ? `and c.ts between ${start} and ${end}`
    : (bounds ? WINDOW_TOKEN : "");
  return question.sql
    .split(ELEMENT_TOKEN).join(target)
    .split(WINDOW_TOKEN).join(window);
}
