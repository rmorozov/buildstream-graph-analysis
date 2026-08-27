// UX-199: getting *between* sections.
//
// Field report: *"navigation in html report is quite poor at the moment
// if explored through the browser."* Round 22's inventory agreed
// precisely - no section ids, so nothing to anchor to or link at; no
// table of contents; no collapse; fourteen sections on a real
// `examples/06` capture, in payload key order, navigated by Ctrl-F.
//
// Everything here is *navigation*, never analysis: nothing in this file
// changes a number, hides a finding, or decides what is worth showing.
// A reader who ignores all of it sees exactly the report they saw
// before, in the same order.

const COLLAPSED_KEY = "bga.collapsed";

// UX-209: the rails, in the order a reader moves through them.
// Mirrors `schemas.RAILS`; the schema decides which rail a
// section is in, this decides what order the groups appear.
export const RAILS = ["decide", "act", "prove", "investigate", "raw"];

// UX-286: and the chapters the rail lists, which are the document's
// grouping rather than a second one written here.
import { CHAPTERS, UNCHAPTERED, chapterFor } from "./chapters.js";

/** The sections the page actually rendered, in document order. */
export function sections(root) {
  return [...(root.querySelectorAll?.("section[data-section]") ?? [])];
}

// UX-223: the anchor spelling comes from `views.js`, which imports
// nothing - so this edge adds no cycle. UX-216 made a link and its
// target one expression, and the palette must not reintroduce a
// second spelling of it.
// `UX-337`: `elementAnchor` moved to `primitives.js` with the other
// symbols that were making the chapters cyclic. Named directly
// rather than re-exported through `views.js`: a re-export is
// invisible to the export's `_module_order`, which walks `import`
// lines, so the module would never be inlined.
import { elementAnchor } from "./primitives.js";

/**
 * The named things inside one section, as a nested list - or `null`.
 *
 * A subsection is anything the section gave a name and an anchor:
 * today that is the folded maps `UX-267` labels. Bounded, because a
 * section with one entry per element would put the run's size back in
 * the rail (`UX-254` capped the one group that grows).
 */
export const SUBSECTIONS_SHOWN = 8;

/**
 * UX-289: the named views a section offers, as rail entries.
 *
 * "Reachable from the rail and from a link" is one requirement, not
 * two: the entry's `href` is `UX-211`'s fragment for that view, so it
 * is the link a reader copies, and the click applies it live rather
 * than waiting for a reload - the page reads the fragment once, at
 * load, and a rail that needed a reload to work would be a rail that
 * does not work.
 */
function viewEntries(section, doc) {
  const select = section?.querySelector?.("select.preset-view");
  const options = [...(select?.children ?? [])];
  if (options.length < 2) return null;
  const table = select.getAttribute?.("data-table") ?? "elements";
  const key = section.getAttribute("data-section");
  const list = doc.createElement("ul");
  list.className = "toc-sub";
  for (const option of options) {
    const name = option.value;
    if (!name) continue;
    const item = doc.createElement("li");
    const link = doc.createElement("a");
    link.href = `#${key}~v.${table}=${encodeURIComponent(name)}`;
    link.setAttribute("data-toc-view", name);
    link.textContent = name;
    link.addEventListener?.("click", () => {
      if (select.value === name) return;
      select.value = name;
      select.dispatchEvent?.(new Event("change", { bubbles: true }));
    });
    item.append(link);
    list.append(item);
  }
  return list;
}

export function subsections(section, doc) {
  const views = viewEntries(section, doc);
  if (views) return views;
  const folds = [...(section?.querySelectorAll?.("details.map > summary") ?? [])];
  if (folds.length < 2) return null;
  const list = doc.createElement("ul");
  list.className = "toc-sub";
  for (const fold of folds.slice(0, SUBSECTIONS_SHOWN)) {
    const name = fold.querySelector?.(".map-name")?.textContent
      ?? fold.textContent;
    const id = `${section.getAttribute("data-section")}--${
      String(name).trim().toLowerCase().replace(/[^\w]+/g, "-")}`;
    const target = fold.parentElement ?? fold;
    if (!target.getAttribute?.("id")) target.setAttribute?.("id", id);
    const item = doc.createElement("li");
    const link = doc.createElement("a");
    link.href = `#${target.getAttribute?.("id") ?? id}`;
    link.setAttribute("data-toc-sub", id);
    link.textContent = String(name).trim();
    item.append(link);
    list.append(item);
  }
  if (folds.length > SUBSECTIONS_SHOWN) {
    const more = doc.createElement("li");
    more.className = "toc-more muted";
    // `UX-208`'s rule: a reader who cannot see the denominator cannot
    // tell a bounded list from a short one.
    more.textContent = `+${folds.length - SUBSECTIONS_SHOWN} more`;
    list.append(more);
  }
  return list;
}

export function label(key) {
  return key.replace(/[-_]/g, " ").replace(/^./, (c) => c.toUpperCase());
}

/**
 * Give every section a stable `id`.
 *
 * The schema key, which is already unique within a document - so a
 * link to `#floors` keeps working as the report grows, and can be
 * pasted into an issue.
 */
export function anchor(root) {
  const named = [];
  for (const section of sections(root)) {
    const key = section.getAttribute("data-section");
    if (!key) continue;
    if (!section.getAttribute("id")) section.setAttribute("id", key);
    named.push(key);
  }
  return named;
}

/** Remembered collapse state. Per viewer, per browser; never shared. */
function readCollapsed(storage) {
  try {
    return new Set(JSON.parse(storage?.getItem(COLLAPSED_KEY) ?? "[]"));
  } catch (error) {
    // A private window, cleared site data, or a browser that throws on
    // access. Every section open is the right answer for all of them.
    return new Set();
  }
}

function writeCollapsed(storage, keys) {
  try {
    storage?.setItem(COLLAPSED_KEY, JSON.stringify([...keys]));
  } catch (error) {
    /* not being able to remember is not a reason to stop working */
  }
}

/**
 * Make each section collapsible, and return the controls.
 *
 * Default-open, always: a report that hid itself on first load would
 * answer the navigation complaint by making the document harder to
 * read, not easier.
 */
export function collapsible(root, { document: doc, storage } = {}) {
  const collapsed = readCollapsed(storage);
  const toggles = new Map();

  for (const section of sections(root)) {
    const key = section.getAttribute("data-section");
    const heading = section.querySelector?.("h2");
    if (!heading) continue;

    const button = doc.createElement("button");
    button.className = "collapse";
    button.setAttribute("aria-expanded", String(!collapsed.has(key)));
    button.setAttribute("data-collapse", key);
    button.textContent = collapsed.has(key) ? "▸" : "▾";
    const apply = (shut) => {
      section.setAttribute("data-collapsed", String(shut));
      button.setAttribute("aria-expanded", String(!shut));
      button.textContent = shut ? "▸" : "▾";
    };
    apply(collapsed.has(key));
    button.addEventListener("click", () => {
      const shut = button.getAttribute("aria-expanded") === "true";
      apply(shut);
      if (shut) collapsed.add(key); else collapsed.delete(key);
      writeCollapsed(storage, collapsed);
    });
    // Not `heading.prepend?.(button) ?? heading.append(button)`: prepend
    // returns undefined, so `??` falls through and the button is added
    // *twice*. Caught by the collapse guard.
    if (typeof heading.prepend === "function") heading.prepend(button);
    else heading.append(button);
    toggles.set(key, apply);
  }

  return {
    keys: [...toggles.keys()],
    all(shut) {
      collapsed.clear();
      for (const [key, apply] of toggles) {
        apply(shut);
        if (shut) collapsed.add(key);
      }
      writeCollapsed(storage, collapsed);
    },
  };
}

/**
 * The table of contents.
 *
 * Generated from what was *rendered*, not from a hardcoded list, so a
 * section that a schema addition brings into being appears in the
 * contents with no edit here - the same property `UX-193` bought for
 * the sections themselves.
 */
export function toc(root, { document: doc, controls } = {}) {
  const keys = anchor(root);
  if (!keys.length) return null;

  const nav = doc.createElement("nav");
  nav.className = "toc";
  nav.setAttribute("aria-label", "Sections");

  const heading = doc.createElement("p");
  heading.className = "toc-title";
  heading.textContent = "Sections";
  nav.append(heading);

  // UX-286: grouped by chapter - the question the reader has - rather
  // than by payload key order or by the rail. `UX-209` grouped this
  // list by `bga:rail` and the document by nothing, so the rail's five
  // groups described an arrangement the page did not have: `decision`,
  // `findings` and `summary` all landed under `raw`, because they are
  // built by the page and no schema node declares their rail. The
  // chapters are the document's own grouping, so the list and the page
  // agree by construction.
  //
  // Still generated from what was actually rendered, and the rail is
  // still what places a section the chapter table does not name.
  const order = [...CHAPTERS, UNCHAPTERED];
  const grouped = new Map(order.map((chapter) => [chapter.id, []]));
  for (const key of keys) {
    const section = root.querySelector?.(`[data-section="${key}"]`)
      ?? [...(root.children ?? [])].find(
        (n) => n.getAttribute?.("data-section") === key);
    const id = section?.getAttribute?.("data-chapter")
      ?? chapterFor(key, section?.getAttribute?.("data-rail"));
    grouped.get(grouped.has(id) ? id : UNCHAPTERED.id).push(key);
  }

  for (const chapter of order) {
    const members = grouped.get(chapter.id);
    if (!members.length) continue;
    const groupName = doc.createElement("p");
    groupName.className = "toc-rail";
    groupName.setAttribute("data-rail", chapter.id);
    groupName.setAttribute("data-chapter", chapter.id);
    // UX-286 item 2: navigation moves chapter to chapter, so the
    // chapter's own name is the link to it - a reader who wants the
    // next question does not have to aim at its first section.
    const jump = doc.createElement("a");
    jump.href = `#chapter-${chapter.id}`;
    jump.setAttribute("data-toc-chapter", chapter.id);
    jump.textContent = chapter.title;
    groupName.append(jump);
    nav.append(groupName);
    const rail = chapter.id;
    const list = doc.createElement("ul");
    // UX-254: the rail this list belongs to, so the stylesheet can
    // bound the one group that grows with the run (`investigate` is
    // one entry per focused element) without JS truncating anything.
    list.setAttribute("data-rail", rail);
    for (const key of members) {
      const item = doc.createElement("li");
      const link = doc.createElement("a");
      link.href = `#${key}`;
      link.setAttribute("data-toc", key);
      link.setAttribute("data-rail", rail);
      // UX-216: a section may name itself. `label(key)` is the right
      // default for a schema key and the wrong one for an element uid,
      // which arrives already sanitised into an id.
      const section = root.querySelector?.(`[data-section="${key}"]`);
      link.textContent = section?.getAttribute?.("data-toc-label")
        || label(key);
      item.append(link);
      // UX-271: one level of nesting, so the rail stops being a flat
      // list of 30+ entries.
      //
      // The request was a third column carrying the JSON structure.
      // Declined and argued in Direction 12: a structural tree makes
      // the *document's shape* the organising principle, which
      // `UX-207` and `UX-199` moved away from - the rail is grouped by
      // what you are trying to do - and a third column leaves under
      // 900px of reading width at 1440, undoing `UX-254`. What the
      // request is actually asking for is that the rail stop being
      // flat, and that needs no column.
      const inner = subsections(section, doc);
      if (inner) item.append(inner);
      list.append(item);
    }
    nav.append(list);
  }

  if (controls) {
    const row = doc.createElement("p");
    row.className = "toc-controls";
    for (const [text, shut] of [["Collapse all", true], ["Expand all", false]]) {
      const button = doc.createElement("button");
      button.textContent = text;
      button.setAttribute("data-all", String(shut));
      button.addEventListener("click", () => controls.all(shut));
      row.append(button);
    }
    nav.append(row);
  }
  return nav;
}

/**
 * Type-ahead over section names and element uids.
 *
 * Navigation, not analysis: it scrolls to something the page already
 * shows. It never filters the report, and it never asks the server
 * anything - `UX-205` is where finding things *inside* a section
 * lives.
 */
export function jumpTargets(root, payload) {
  const targets = anchor(root).map(
    (key) => ({ kind: "section", key, text: label(key) }));

  const seen = new Set();
  for (const node of root.querySelectorAll?.("[data-element]") ?? []) {
    const uid = node.getAttribute("data-element");
    if (uid && !seen.has(uid)) {
      seen.add(uid);
      targets.push({ kind: "element", key: uid, text: uid });
    }
  }
  for (const finding of payload?.findings ?? []) {
    for (const uid of finding.elements ?? []) {
      if (!seen.has(uid)) {
        seen.add(uid);
        targets.push({ kind: "element", key: uid, text: uid });
      }
    }
  }
  return targets;
}

export function matches(targets, query, limit = 8) {
  const needle = String(query ?? "").trim().toLowerCase();
  if (!needle) return [];
  return targets
    .filter((t) => t.text.toLowerCase().includes(needle))
    .slice(0, limit);
}

// UX-223: the jump box, as an index over what the page can already do.
//
// `wireJumpBox` searched section names and element uids and scrolled to
// the hit. Useful, and by the time a reader has typed `openssl` the page
// knows six things they might want to do with it and offers one.
//
// Every row below is a link or a control that exists elsewhere in the
// page. This is an index over affordances, not a new capability - which
// is why it is cheap, and why it must not grow into one. No fuzzy
// matching, no ranking heuristic, no search index: substring matching
// over a list the page already holds is what this is.

/** The published numbers for one element, or `null`. Never computed.
 *
 * Named for the palette rather than generically: `views.js` has an
 * `elementFacts` of its own since UX-216, and the export flattens every
 * module into one scope - so a second declaration of that name is a
 * `SyntaxError` in the shipped page, which is UX-199's defect exactly.
 */
export function paletteFacts(payload, uid) {
  const detail = (payload?.signals?.critical_path_detail ?? [])
    .find((row) => row.element_uid === uid);
  const durations = payload?.signals?.element_durations ?? {};
  const action = (payload?.headline?.top_actions ?? [])
    .find((row) => row.element_uid === uid);
  const duration = detail?.duration_us ?? durations[uid] ?? null;
  if (duration === null && !action) return null;
  return {
    duration_us: duration,
    share_of_path: detail?.share_of_path ?? null,
    saving_us: action?.saving_us ?? null,
  };
}

/**
 * What the palette offers for one query, in groups.
 *
 * `context` says which preconditions this run meets. An action whose
 * precondition is absent is **not listed** - `UX-194`'s rule, applied
 * to more buttons than it was written for: a Perfetto row on a run with
 * no timeline is a dead affordance, and offering it is worse than not
 * having it.
 */
export function paletteResults(targets, query, payload, context = {}, limit = 8) {
  const hits = matches(targets, query, limit);
  const elements = hits.filter((hit) => hit.kind === "element")
    .map((hit) => ({ ...hit, facts: paletteFacts(payload, hit.key) }));
  const sections = hits.filter((hit) => hit.kind === "section");

  const actions = [];
  const first = elements[0];
  if (first) {
    actions.push({ id: "show", label: `Show everything about ${first.key}`,
                   element: first.key,
                   href: `#${elementAnchor(first.key)}` });
    actions.push({ id: "focus", label: `Focus ${first.key}`,
                   element: first.key, focus: true });
    if (context.hasTimeline) {
      actions.push({ id: "perfetto", label: `Inspect ${first.key} in Perfetto`,
                     element: first.key, investigate: true });
    }
    if (context.hasBlast) {
      actions.push({ id: "blast", label: `Blast radius of ${first.key}`,
                     element: first.key, blast: true });
    }
  }
  return { elements, actions, sections };
}
