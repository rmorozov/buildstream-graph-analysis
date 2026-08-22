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
const PLANE_1 = "bst-builder";
const PLANE_2 = "native-process";

export const QUESTIONS = [
  {
    id: "element-time",
    category: "execution",
    plane: "Plane 1",
    title: "Where did the time actually go, per element?",
    why: "Plane 1's element spans, aggregated - scoped to the element plane, so Plane 2 command names cannot crowd the answer. The figure bga analyze prints in the Attribution table; here to cross-check it, or to slice it further.",
    sql: "select extract_arg(s.arg_set_id, 'args.element') as element,\n       count(*) as spans,\n       sum(s.dur) / 1e9 as seconds\nfrom slice s\nwhere s.category = 'bst-builder'\ngroup by element\norder by seconds desc\nlimit 25;",
  },
  {
    id: "process-storm",
    category: "resources",
    plane: "Plane 2",
    title: "Which elements ran the most processes?",
    why: "Plane 2's processes, grouped by the element that ran them. A high count with low total time is a process-storm - many short execs, the shape examples/08-process-storm exists to show.",
    sql: "select extract_arg(s.arg_set_id, 'args.element') as element,\n       count(*) as processes,\n       sum(s.dur) / 1e9 as seconds\nfrom slice s\nwhere s.category = 'native-process'\ngroup by element\norder by processes desc\nlimit 25;",
  },
  {
    id: "sandbox-tax",
    category: "resources",
    plane: "both planes",
    title: "What is the sandbox tax here?",
    why: "Time inside an element's Plane 1 span that its own Plane 2 processes do not account for: staging, checkout, the sandbox itself. The containment is constrained to the same element, so another element building in parallel cannot be subtracted from this one. Compare with bga correlate's figure.",
    sql: "select e.element,\n       e.dur / 1e9 as element_seconds,\n       (e.dur - coalesce(sum(n.dur), 0)) / 1e9 as unaccounted_seconds\nfrom (select s.id, s.ts, s.dur,\n             extract_arg(s.arg_set_id, 'args.element') as element\n      from slice s where s.category = 'bst-builder') e\nleft join (select s.ts, s.dur,\n                  extract_arg(s.arg_set_id, 'args.element') as element\n           from slice s where s.category = 'native-process') n\n  on n.element = e.element\n and n.ts >= e.ts and n.ts + n.dur <= e.ts + e.dur\ngroup by e.id\norder by unaccounted_seconds desc\nlimit 20;",
  },
  {
    id: "stalls",
    category: "scheduling",
    plane: "Plane 1",
    title: "Where are the longest stalls?",
    why: "Gaps on the element plane: the build was running and nothing was building. Windowed over element spans alone - measured against every track, thousands of interleaved Plane 2 slices close exactly the gaps this question is looking for.",
    sql: "select element, ts, dur,\n       lead(ts) over (order by ts) - (ts + dur) as gap_after\nfrom (select extract_arg(s.arg_set_id, 'args.element') as element,\n             s.ts, s.dur\n      from slice s where s.category = 'bst-builder')\norder by gap_after desc\nlimit 20;",
  },
  {
    id: "element-commands",
    category: "execution",
    plane: "Plane 2",
    title: "What did one element actually execute?",
    why: "The micro half of the cycle - the commands Plane 2 recorded inside one sandbox, longest first. Selected by the element uid both planes carry, not by a lane name.",
    example: "core.bst",
    sql: "select s.name as command, s.dur / 1e6 as ms\nfrom slice s\nwhere s.category = 'native-process'\n  and extract_arg(s.arg_set_id, 'args.element') = '{element}'\norder by s.dur desc\nlimit 40;",
  },
  {
    id: "dependency-wait",
    category: "dependencies",
    plane: "Plane 1",
    title: "What was this element waiting for?",
    why: "The elements that finished last before it could start, on the element plane only. A long gap here is a dependency shape problem rather than a scheduler one - the distinction the blast and criticality findings are about.",
    example: "core.bst",
    sql: "select element, (ts + dur) / 1e9 as ended_at_seconds\nfrom (select extract_arg(s.arg_set_id, 'args.element') as element,\n             s.ts, s.dur\n      from slice s where s.category = 'bst-builder')\nwhere ts + dur <= (select min(s.ts) from slice s\n                   where s.category = 'bst-builder'\n                     and extract_arg(s.arg_set_id, 'args.element') = '{element}')\norder by ended_at_seconds desc\nlimit 15;",
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
    const label = make("h3", { class: "category" });
    label.textContent = category;
    section.append(label);
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
      section.append(heading, why, block);
    }
  }
  return section;
}

/** The query as the page shows it: the example element filled in, so a
 *  reader can paste it without editing. */
export function renderedSql(question) {
  return question.sql.split("{element}").join(question.example ?? "");
}
