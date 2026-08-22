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
export const QUESTIONS = [
  {
    id: "element-time",
    category: "execution",
    title: "Where did the time actually go, per element?",
    why: "Plane 1's element spans, aggregated. The answer bga analyze gives you in the Attribution table — here to cross-check it, or to slice it further.",
    sql: "select name, count(*) as spans, sum(dur) / 1e9 as seconds\nfrom slice\ngroup by name\norder by seconds desc\nlimit 25;",
  },
  {
    id: "process-storm",
    category: "resources",
    title: "Which elements ran the most processes?",
    why: "Plane 2's lanes. A high count with low total time is a process-storm — many short execs, the shape examples/08-process-storm exists to show.",
    sql: "select t.name as lane, count(*) as processes,\n       sum(s.dur) / 1e9 as seconds\nfrom slice s join track t on s.track_id = t.id\nwhere t.name like 'native:%'\ngroup by lane\norder by processes desc\nlimit 25;",
  },
  {
    id: "sandbox-tax",
    category: "resources",
    title: "What is the sandbox tax here?",
    why: "Time inside an element's span that no traced process accounts for: staging, checkout, the sandbox itself. Compare with bga correlate's figure.",
    sql: "select p.name as element,\n       p.dur / 1e9 as element_seconds,\n       (p.dur - coalesce(sum(c.dur), 0)) / 1e9 as unaccounted_seconds\nfrom slice p\nleft join slice c\n  on c.ts >= p.ts and c.ts + c.dur <= p.ts + p.dur and c.id != p.id\ngroup by p.id\norder by unaccounted_seconds desc\nlimit 20;",
  },
  {
    id: "stalls",
    category: "scheduling",
    title: "Where are the longest stalls?",
    why: "Gaps on the element track: the build was running and nothing was building. The wait-gap analysis in the report, seen directly.",
    sql: "select s.name, s.ts, s.dur,\n       lead(s.ts) over (order by s.ts) - (s.ts + s.dur) as gap_after\nfrom slice s\norder by gap_after desc\nlimit 20;",
  },
  {
    id: "element-commands",
    category: "execution",
    title: "What did one element actually execute?",
    why: "The micro half of the cycle — the commands inside one sandbox, longest first.",
    example: "core.bst",
    sql: "select s.name as command, s.dur / 1e6 as ms\nfrom slice s join track t on s.track_id = t.id\nwhere t.name = 'native:{element}'\norder by s.dur desc\nlimit 40;",
  },
  {
    id: "dependency-wait",
    category: "dependencies",
    title: "What was this element waiting for?",
    why: "The elements that finished last before it could start. A long gap here is a dependency shape problem, not a scheduler one — which is the distinction the blast and criticality findings are about.",
    example: "core.bst",
    sql: "select s.name as finished_before,\n       (s.ts + s.dur) / 1e9 as ended_at_seconds\nfrom slice s\nwhere s.ts + s.dur <= (select min(ts) from slice where name = '{element}')\norder by ended_at_seconds desc\nlimit 15;",
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
