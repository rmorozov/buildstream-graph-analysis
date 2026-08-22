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
    why:
      "Plane 1's element spans, aggregated - scoped to the element " +
      " plane, so Plane 2 command names cannot crowd the answer. The " +
      " figure bga analyze prints in the Attribution table; here to " +
      " cross-check it, or to slice it further.",
    sql: `select extract_arg(s.arg_set_id, 'args.element') as element,
       count(*) as spans,
       sum(s.dur) / 1e9 as seconds
from slice s
where s.category = 'bst-builder'
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
    sql: `select extract_arg(s.arg_set_id, 'args.element') as element,
       count(*) as processes,
       sum(s.dur) / 1e9 as seconds
from slice s
where s.category = 'native-process'
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
             extract_arg(s.arg_set_id, 'args.element') as element
      from slice s where s.category = 'bst-builder') e
left join (select s.ts, s.dur,
                  extract_arg(s.arg_set_id, 'args.element') as element
           from slice s where s.category = 'native-process') n
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
from (select extract_arg(s.arg_set_id, 'args.element') as element,
             s.ts, s.dur
      from slice s where s.category = 'bst-builder')
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
where s.category = 'native-process'
  and extract_arg(s.arg_set_id, 'args.element') = '{element}'
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
from (select extract_arg(s.arg_set_id, 'args.element') as element,
             s.ts, s.dur
      from slice s where s.category = 'bst-builder')
where ts + dur <= (select min(s.ts) from slice s
                   where s.category = 'bst-builder'
                     and extract_arg(s.arg_set_id, 'args.element') = '{element}')
order by ended_at_seconds desc
limit 15;`,
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
export function copyButton(make, text, deps = {}) {
  const button = make("button", { type: "button", class: "copy-sql" });
  button.textContent = "Copy";
  button.setAttribute("data-copy", text);
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
    deps.setTimeout?.(() => { button.textContent = "Copy"; }, 1500)
      ?? (typeof setTimeout !== "undefined"
          && setTimeout(() => { button.textContent = "Copy"; }, 1500));
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
