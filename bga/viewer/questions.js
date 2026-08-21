// UX-194 item 3, extracted to data by `UX-199`.
//
// The SQL engine is Perfetto's; these are the questions that kept
// coming up often enough to be worth writing down. They live here
// rather than in `sql.html` because the **export** needs them too:
// `bga view --export` has no server, so it used to strip the link to
// that page and leave nothing in its place - functionality silently
// lost. One source, two renderings.
export const QUESTIONS = [
  {
    title: "Where did the time actually go, per element?",
    why: "Plane 1's element spans, aggregated. The answer bga analyze gives you in the Attribution table \u2014 here to cross-check it, or to slice it further.",
    sql: "select name, count(*) as spans, sum(dur) / 1e9 as seconds\nfrom slice\ngroup by name\norder by seconds desc\nlimit 25;",
  },
  {
    title: "Which elements ran the most processes?",
    why: "Plane 2's lanes. A high count with low total time is a process-storm \u2014 many short execs, the shape examples/08-process-storm exists to show.",
    sql: "select t.name as lane, count(*) as processes,\n       sum(s.dur) / 1e9 as seconds\nfrom slice s join track t on s.track_id = t.id\nwhere t.name like 'native:%'\ngroup by lane\norder by processes desc\nlimit 25;",
  },
  {
    title: "What is the sandbox tax here?",
    why: "Time inside an element's span that no traced process accounts for: staging, checkout, the sandbox itself. Compare with bga correlate's figure.",
    sql: "select p.name as element,\n       p.dur / 1e9 as element_seconds,\n       (p.dur - coalesce(sum(c.dur), 0)) / 1e9 as unaccounted_seconds\nfrom slice p\nleft join slice c\n  on c.ts >= p.ts and c.ts + c.dur <= p.ts + p.dur and c.id != p.id\ngroup by p.id\norder by unaccounted_seconds desc\nlimit 20;",
  },
  {
    title: "Where are the longest stalls?",
    why: "Gaps on the element track: the build was running and nothing was building. The wait-gap analysis in the report, seen directly.",
    sql: "select s.name, s.ts, s.dur,\n       lead(s.ts) over (order by s.ts) - (s.ts + s.dur) as gap_after\nfrom slice s\norder by gap_after desc\nlimit 20;",
  },
  {
    title: "What did one element actually execute?",
    why: "Replace the name. This is the micro half of the cycle \u2014 the commands inside one sandbox, longest first.",
    sql: "select s.name as command, s.dur / 1e6 as ms\nfrom slice s join track t on s.track_id = t.id\nwhere t.name = 'native:core.bst'\norder by s.dur desc\nlimit 40;",
  },
];


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
  for (const question of QUESTIONS) {
    const heading = make("h3", {});
    heading.textContent = question.title;
    const why = make("p", { class: "muted" });
    why.textContent = question.why;
    const block = make("pre", {});
    const code = make("code", {});
    code.textContent = question.sql;
    block.append(code);
    section.append(heading, why, block);
  }
  return section;
}
