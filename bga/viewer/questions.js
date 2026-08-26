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
// element uid there when a finding names one; the page renders
// `example` so the reader sees a query they can run as it stands.

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
    why:
      "Plane 1's element spans, aggregated - scoped to the element " +
      " plane, so Plane 2 command names cannot crowd the answer. The " +
      " figure bga analyze prints in the Attribution table; here to " +
      " cross-check it, or to slice it further.",
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
    id: "process-storm",
    category: "resources",
    plane: "Plane 2",
    title: "Which elements ran the most processes?",
    why:
      "Plane 2's processes, grouped by the element that ran them. A " +
      " high count with low total time is a process-storm - many short " +
      " execs, the shape examples/08-process-storm exists to show.",
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
      " processes do not account for: staging, checkout, the sandbox " +
      " itself. The containment is constrained to the same element, so " +
      " another element building in parallel cannot be subtracted from " +
      " this one. Compare with bga correlate's figure.",
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
      " was building. Windowed over element spans alone - measured " +
      " against every track, thousands of interleaved Plane 2 slices " +
      " close exactly the gaps this question is looking for.",
    sql: `select element, ts, dur,
       lead(ts) over (order by ts) - (ts + dur) as gap_after
from (select extract_arg(s.arg_set_id, 'debug.element') as element,
             s.ts, s.dur
      from slice s where s.category glob '*bst-builder*')
order by gap_after desc
limit 20;`,
  },
  {
    id: "element-commands",
    category: "execution",
    plane: "Plane 2",
    title: "What did one element actually execute?",
    example: "core.bst",
    why:
      "The micro half of the cycle - the commands Plane 2 recorded " +
      " inside one sandbox, longest first. Selected by the element uid " +
      " both planes carry, not by a lane name.",
    sql: `select s.name as command, s.dur / 1e6 as ms
from slice s
where s.category glob '*native-process*'
  and extract_arg(s.arg_set_id, 'debug.element') = '{element}'
order by s.dur desc
limit 40;`,
  },
  {
    id: "dependency-wait",
    category: "dependencies",
    plane: "Plane 1",
    title: "What was this element waiting for?",
    example: "core.bst",
    why:
      "The elements that finished last before it could start, on the " +
      " element plane only. A long gap here is a dependency shape " +
      " problem rather than a scheduler one - the distinction the " +
      " blast and criticality findings are about.",
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
      " is one group-by rather than a join against the graph. A kind " +
      " that dominates is a question about the build's shape - one " +
      " cmake element is slow, forty of them is a toolchain decision.",
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
      " that failed is one predicate away instead of a scan of every " +
      " command line. `debug.cmd` is the untruncated argv - the slice " +
      " name is only its first 120 characters, which is rarely the " +
      " part that distinguishes two compiler invocations.",
    sql: `select extract_arg(s.arg_set_id, 'debug.element') as element,
       extract_arg(s.arg_set_id, 'debug.exit_status') as exit_status,
       extract_arg(s.arg_set_id, 'debug.cmd') as command,
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
      " annotations alone - no containment join, so nothing another " +
      " element did in parallel can be attributed here. A ratio far " +
      " below 1 is a process that waited; far above 1 is one that " +
      " used several cores. This is the sandbox-tax cross-check that " +
      " `bga correlate` publishes, asked of the trace directly.",
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
      " peak. It is " +
      " read as a maximum and never summed: two processes peaking at " +
      " different moments never held the sum between them, which is " +
      " the same refusal `compute_peak_memory` makes and the reason " +
      " `UX-310` declined to draw a memory curve.",
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
    title: "What did this element wait for, by the graph?",
    example: "core.bst",
    why:
      "Plane 1 again, by the graph rather than the clock: `UX-309` " +
      " draws the dependency edges as **flows**, so this is " +
      " the declared graph rather than whatever happened to finish " +
      " first. The timestamp-proximity version of this question is " +
      " `dependency-wait` above; where they disagree, the gap is a " +
      " scheduler question and not a dependency one.",
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
      " sampled from the same records the " +
      " process census counts. Its peak equals the `max_concurrency` " +
      " the report publishes - by construction, because both read one " +
      " function. Read it against the machine's core count: a plateau " +
      " well under it is capacity nobody used.",
    sql: `select c.ts / 1e9 as seconds, c.value as processes_running
from counter c
join counter_track t on c.track_id = t.id
where t.name = 'traced processes running'
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
      " that left the machine still says which project, which host " +
      " and which `bga` wrote it. `incomplete_reason` is the one key " +
      " a finished run never emits - its absence is the only thing " +
      " its absence means, and a trace of an interrupted build is " +
      " not a measurement.",
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
      wrote = Boolean(clipboard?.writeText?.(text));
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
export function renderQuestions(make) {
  const section = make("section", { "data-section": "perfetto-questions",
                                    id: "perfetto-questions" });
  section.append(make("h2", {}, "Questions worth asking in Perfetto"));
  const intro = make("p", { class: "muted" });
  intro.textContent =
    "Load this run's timeline into ui.perfetto.dev, open Query (SQL), "
    + "and paste one of these. Slices are what you query: Plane 1's "
    + "element spans and Plane 2's process lanes are different tracks "
    + "in the same trace.";
  section.append(intro);
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
      const block = make("pre", {});
      const code = make("code", {});
      code.textContent = renderedSql(question);
      block.append(code);
      // UX-208 item 3: every rendered SQL block copies, with an
      // acknowledgment - a query you have to select by hand is a query
      // most readers retype wrongly.
      fold.append(heading, why, block, copyButton(make, renderedSql(question)));
    }
  }
  return section;
}

/** The query as the page shows it: the example element filled in, so a
 *  reader can paste it without editing. */
export function renderedSql(question) {
  return question.sql.split("{element}").join(question.example ?? "");
}
