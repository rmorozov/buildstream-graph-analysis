// UX-204: where to look, and why.
//
// The viewer's job is not to draw the timeline - Perfetto draws it far
// better - but to say *where to look and why*. "Open timeline in
// Perfetto" is correct and context-free: the findings know an element
// uid and a question, and none of it travelled.
//
// A link-builder, not a layer. Everything here is a pure function of
// data the page already has; nothing fetches, nothing renders. What
// Perfetto's deep-link API verifiably supports is used - the trace and
// a title - and what it does not is not faked: there is no documented
// way to preload a query into the Query pane, so the always-works floor
// is "open the trace, and put the right query one paste away".
import { ELEMENT_TOKEN, byId, takesElement } from "./questions.js";

/**
 * `UX-229` retired this file's own finding -> query table.
 *
 * It lived here, which made the page the only place that knew which
 * question deepens which finding: the text report could not print it
 * and the CI comment could not cite it. It is `bga/provenance.py`'s
 * `TRACE_QUERIES` now, and this module reads the field it publishes -
 * the same move `UX-207` made for the diagnosis.
 *
 * `UX-368`: **from `finding.trace_query`, not `finding.provenance
 * .trace_query`.** `UX-229` wrote the second path; `UX-344` moved the
 * records out of the findings into one list and this line was not
 * moved with them, so for four rounds it read a key the payload had
 * stopped having. Measured on `tests/fixtures/with_timeline`, the one
 * committed capture whose handoff works: four findings should earn an
 * Investigate button and **zero** were drawn. Every guard on this
 * function built its own finding object with the nested shape inline,
 * so all of them passed over a payload none of them had read.
 *
 * The consequence of a missing field is deliberate and unchanged: no
 * query, no button, which is `UX-194`'s dead-control rule. A guessed
 * query would be worse than none.
 */
export function queryFor(finding) {
  const query = finding?.trace_query;
  return typeof query === "string" && query ? query : null;
}

/**
 * Every query a finding earns, best first - `UX-448`.
 *
 * `trace_queries` is published only where a claim reads at more than
 * one grain, so its absence is the normal case and means "the one in
 * `trace_query`". Reading it as the whole answer would draw nothing on
 * nineteen findings of twenty; `trace_query` stays the first entry and
 * the head of this list either way.
 */
export function queriesFor(finding) {
  const first = queryFor(finding);
  if (!first) return [];
  const all = finding?.trace_queries;
  if (!Array.isArray(all) || !all.length) return [first];
  const ids = all.filter((id) => typeof id === "string" && id);
  return ids[0] === first ? ids : [first, ...ids.filter((id) => id !== first)];
}

/** The element a finding is about, or null. First one: the button is
 *  one question, and a question about eleven elements is none. */
export function subjectOf(finding) {
  const elements = finding?.elements;
  return Array.isArray(elements) && elements.length ? String(elements[0]) : null;
}

/**
 * `{element_uid?, reason, query?}` -> the handoff invocation.
 *
 * `title` is what Perfetto shows in its tab, so it carries the reason
 * rather than the file name. `sql` is the query with the element
 * substituted - the paste, ready.
 */
export function traceContext({ element_uid = null, reason, query = null } = {}) {
  if (!reason) return null;
  const entry = query ? byId(query) : null;
  if (query && !entry) return null;
  const title = element_uid ? `${reason} — ${element_uid}` : reason;
  return {
    title,
    element: element_uid,
    queryId: entry ? entry.id : null,
    sql: entry ? withElement(entry, element_uid) : null,
  };
}

/** The library entry's SQL, aimed at one element where it takes one.
 *
 *  `UX-369` removed the per-entry `example`, so the fallback here was
 *  the empty string: a finding naming no element handed the reader
 *  `= ''`, a query that runs and returns nothing. The token instead,
 *  for the reason that item gives - a visible `{element}` says there
 *  is a value to choose. */
export function withElement(entry, element_uid) {
  return entry.sql.split(ELEMENT_TOKEN)
    .join(element_uid ?? entry.example ?? ELEMENT_TOKEN);
}

/** The context a finding earns, or null when no query answers it. */
export function investigationFor(finding) {
  return investigationsFor(finding)[0] ?? null;
}

/**
 * One context per grain the finding offers - `UX-448`.
 *
 * The handoff is one trace and one tab whatever the reader came to
 * ask, so this is not two buttons: it is one button and the SQL for
 * each grain beside it. A context whose query is not in the library is
 * dropped rather than drawn empty, which is `UX-194`'s dead-control
 * rule applied per entry rather than to the whole set.
 */
export function investigationsFor(finding) {
  if (!finding) return [];
  return queriesFor(finding)
    .map((query) => {
      const entry = byId(query);
      return traceContext({
        // `UX-368`: only where the query asks about one. `stalls` and
        // `cpu-versus-wall` are questions about the run, and handing
        // them an element would put a name in a title the SQL never
        // uses.
        element_uid: entry && takesElement(entry) ? subjectOf(finding) : null,
        reason: finding.title ?? finding.id,
        query,
      });
    })
    .filter(Boolean);
}
