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
    // `UX-535`: the option's *label*, which already carries the count -
    // the bare name collides with the section of the same name, and a
    // rail with one label on two hrefs cannot be navigated by reading.
    link.textContent = option.textContent ?? name;
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
 *
 * `enclosing` is the fold layer *outside* the sections, as
 * `(open) => …`. `UX-355`: the document folds at two layers now -
 * `UX-347`'s chapters over `UX-199`'s sections - and a control that
 * says "all" and drives one of them is a control whose label is not
 * true. It is injected rather than imported so this module keeps
 * knowing only about sections, and so `all()` is the one place both
 * layers are named.
 */
export function collapsible(root, { document: doc, storage,
                                    enclosing = null } = {}) {
  const collapsed = readCollapsed(storage);
  const toggles = new Map();

  for (const section of sections(root)) {
    const key = section.getAttribute("data-section");
    const heading = section.querySelector?.("h2");
    if (!heading) continue;

    const button = doc.createElement("button");
    button.className = "collapse";
    // `UX-536`: 65 of these had no accessible name and defaulted to
    // `type=submit`. The name is the heading's, read before the button
    // joins it; `aria-expanded` beside it carries the state.
    button.setAttribute("type", "button");
    button.setAttribute("aria-label", (heading.textContent || key).trim());
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
      // The enclosing layer first when opening, so the sections it
      // holds are on screen by the time they are told to open; and
      // last when shutting, for the same reason in reverse.
      if (!shut) enclosing?.(true);
      collapsed.clear();
      for (const [key, apply] of toggles) {
        apply(shut);
        if (shut) collapsed.add(key);
      }
      writeCollapsed(storage, collapsed);
      if (shut) enclosing?.(false);
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
      // `UX-388`: a section that came back empty is still in the map,
      // and says so there. Before this it was not in the document at
      // all, so the rail was a list of what happened to be non-empty on
      // this run and a reader comparing two runs had nothing to compare.
      if (section?.getAttribute?.("data-empty") === "true") {
        link.setAttribute("data-empty", "true");
      }
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
 * The rail learns where the reader is (`UX-399`, styleguide §6c).
 *
 * The rail has 77 entries on a real report and is 7.4 screens tall in
 * the document beside it, and until this it said nothing about which of
 * the 77 you were looking at. `IntersectionObserver` is the platform's
 * answer - no scroll handler, no layout read per frame, no library.
 *
 * `data-current` is the mark. One entry carries it: the topmost section
 * currently intersecting the viewport, which is the one whose heading a
 * reader would say they are "at". `aria-current="location"` is the same
 * fact for a screen reader, and is the attribute the spec has for
 * exactly this.
 *
 * Returns the observer so a caller can disconnect it, or `null` where
 * the platform has none - the DOM shim the module guards run on, and
 * any browser old enough to lack it. The rail is complete without the
 * mark; nothing here decides what is in it (`UX-199`'s rule for this
 * whole file).
 */
/**
 * `UX-393`: **next section, previous section, back to the top.**
 *
 * Counted on the round-63 export: 9,316 px of page (7.4 screens at
 * 1,260), 77 rail entries, and *one* control matching next/prev/top -
 * an ordinary link to `#next_steps` inside a sentence. A reader
 * working through the findings in order had to move the pointer to
 * the rail, find the entry after the one they were on among 77, and
 * click it, for every section.
 *
 * **The rail is where they live, not a banner.** `UX-347`'s distance
 * budget measures scroll distance to content, and a 60px chrome bar
 * makes every measurement on every screen worse. The rail is already
 * sticky and already beside the content, so three buttons at its head
 * cost the reading column nothing.
 *
 * **The order is the rail's**, which is `anchor(root)`'s, which is
 * `UX-235`'s declared order - so "next" means the next section the
 * page says comes next, not the next one in the DOM. And "here" is
 * `scrollspy`'s `data-current` mark, so the two controls cannot
 * disagree about where the reader is: one of them puts the mark there
 * and the other reads it.
 *
 * Moving is a **click on the rail link**, not a second implementation
 * of what a rail link does. A folded chapter opens, the anchor
 * updates, the scroll happens - whatever the rail does, this does
 * (`UX-347`'s "every way in opens it first").
 *
 * Returns `{ node, next, previous, top }` so a guard can drive the
 * steps without a browser's chrome, or `null` where there is no rail.
 */
/**
 * `UX-394`: **a run selector, in the page.**
 *
 * Round 63 ran the capture cycle twice, so the store held two runs of
 * one project while the report was open, and no control in the page
 * reached the other:
 *
 * ```text
 * runs in the store                        2
 * controls in the page reaching another    0
 * ```
 *
 * `bga view` was a single-run window. The tool already speaks about
 * more than one run - `bga compare`, `@prev`, `@last`, the store's own
 * listing - and all of it was CLI vocabulary, so a reader in a browser
 * had to go back to a terminal and re-invoke.
 *
 * **A navigation, not a re-render.** The page reads its payload once
 * at boot (`UX-296` - it parses nothing), so `?run=<stamp>` *is* the
 * state: choosing a run loads that URL, and sending someone the URL
 * sends them the same view of the same run (`UX-211`'s rule).
 *
 * **Absent, not empty** (`UX-388`). An export carries one run's
 * payload and can reach no other, so it renders no selector rather
 * than a control that fails - which is the Falsification's own
 * "what it must not do". The list comes from `store.json`, which only
 * a served page has.
 *
 * The identity is `UX-95`'s: what the run *is* - its stamp, its alias
 * and what it measured - never a directory name.
 */
export function runSelector(nav, store, { document: doc, current = null,
                                          location: where = null } = {}) {
  const owner = doc ?? nav?.ownerDocument;
  if (!nav || !owner) return null;
  const runs = ((store ?? {}).snapshots ?? []).filter((row) => row?.has_run);
  // One run is not a choice, and no store is not a page with a broken
  // control on it.
  if (runs.length < 2) return null;

  // The URL a stamp opens, written on the control as well as followed
  // by it. A guard cannot watch a navigation - it takes the page the
  // evaluation is running in with it - so the control says where it
  // goes, and the guard loads that URL itself and checks what comes
  // back. Two halves of one claim, and neither is the other's proof.
  const urlFor = (stamp) => `?run=${encodeURIComponent(stamp)}`;

  const box = owner.createElement("p");
  box.className = "run-picker";
  const label = owner.createElement("label");
  label.textContent = "Run: ";
  label.setAttribute("for", "bga-run");
  const select = owner.createElement("select");
  select.id = "bga-run";
  select.name = "run";
  select.setAttribute("aria-label", "Which run this report is of");
  for (const row of runs) {
    const option = owner.createElement("option");
    option.value = row.stamp;
    option.setAttribute("data-run-url", urlFor(row.stamp));
    // `UX-95`: what the run is. The alias a reader already types at a
    // terminal, then what it measured - never the directory name.
    const seconds = Number(row.total_duration_us);
    option.textContent = row.stamp
      + (row.alias ? ` (${row.alias})` : "")
      + (Number.isFinite(seconds) ? ` \u2014 ${(seconds / 1e6).toFixed(1)}s` : "");
    if (row.stamp === current) option.selected = true;
    select.append(option);
  }
  const go = (stamp) => {
    const target = where ?? owner.defaultView?.location ?? null;
    if (!target || !stamp) return;
    // The hash travels: a reader switching runs is usually looking at
    // one section and wants the same section of the other.
    target.assign(`${urlFor(stamp)}${target.hash || ""}`);
  };
  select.addEventListener("change", () => go(select.value));
  label.append(select);
  box.append(label);

  // The two neighbours, one click each. `@prev` and `@last` are the
  // aliases the store already publishes, so the page offers what the
  // terminal offers rather than inventing a second vocabulary.
  const at = runs.findIndex((row) => row.stamp === current);
  const jump = (text, stamp, name) => {
    if (!stamp || stamp === current) return;
    const button = owner.createElement("button");
    button.setAttribute("type", "button");
    button.setAttribute("data-run-jump", name);
    button.setAttribute("data-run", stamp);
    button.setAttribute("data-run-url", urlFor(stamp));
    button.textContent = text;
    button.addEventListener("click", () => go(stamp));
    box.append(button);
  };
  jump("\u2190 Previous run", at > 0 ? runs[at - 1].stamp : null, "previous");
  jump("Latest run", runs[runs.length - 1].stamp, "latest");

  const title = nav.querySelector?.(".toc-title");
  if (title?.nextSibling) nav.insertBefore(box, title.nextSibling);
  else nav.append(box);
  return { node: box, select, go };
}

export function stepper(root, nav, { document: doc, window: win } = {}) {
  if (!nav) return null;
  const owner = doc ?? root?.ownerDocument;
  if (!owner) return null;
  const view = win ?? owner.defaultView ?? null;

  const links = () => [...(nav.querySelectorAll?.("[data-toc]") ?? [])];
  //: Where the reader is, by `scrollspy`'s mark. With no mark - no
  //: `IntersectionObserver`, or the page not yet scrolled - "next"
  //: means the first section, which is what a reader at the top means.
  const at = () => links().findIndex((link) => link.hasAttribute("data-current"));

  // The mark is asynchronous: `IntersectionObserver` fires on a later
  // task and the scroll it is watching is smooth, so two clicks in a
  // row both read the *pre-click* mark and the second one goes
  // nowhere. Measured in Chrome before this: six presses of Next, six
  // times `decision`.
  //
  // So the stepper carries its own cursor and adopts the mark only
  // when the mark has **moved on its own** - which is the reader
  // scrolling, and is the one case where the mark knows something the
  // cursor does not. A mark that is merely behind reads as the same
  // value it had at the previous step, and that is what tells the two
  // apart.
  let cursor = -1;
  let lastMark = -1;
  const step = (by) => {
    const all = links();
    if (!all.length) return null;
    const marked = at();
    const behind = cursor >= 0 && marked >= 0
      && marked === lastMark && marked !== cursor;
    if (!behind && marked >= 0) cursor = marked;
    lastMark = marked;
    // From nowhere, `next` is the first and `previous` is the last:
    // the ends of the order, not an error.
    const to = cursor < 0 ? (by > 0 ? 0 : all.length - 1) : cursor + by;
    // Clamped, not wrapped. The Falsification asks that pressing next
    // past the end *stops*, and a reader who has reached the end of a
    // report has not asked to start it again.
    const bounded = Math.max(0, Math.min(all.length - 1, to));
    cursor = bounded;
    all[bounded].click?.();
    return all[bounded];
  };

  const bar = owner.createElement("p");
  bar.className = "toc-steps";
  const button = (text, name, label, run) => {
    const node = owner.createElement("button");
    node.setAttribute("type", "button");
    node.setAttribute("data-step", name);
    node.setAttribute("aria-label", label);
    node.textContent = text;
    node.addEventListener("click", run);
    bar.append(node);
    return node;
  };
  const previous = () => step(-1);
  const next = () => step(1);
  const top = () => {
    view?.scrollTo?.({ top: 0, behavior: "smooth" });
    // The mark follows the scroll through `scrollspy`; nothing here
    // writes it, so there is still one authority on "here".
  };
  button("\u2191 Top", "top", "Back to the top", top);
  button("\u2190 Prev", "previous", "Previous section, or the [ key", previous);
  button("Next \u2192", "next", "Next section, or the ] key", next);
  // `UX-536`: the two accelerators were announced nowhere. Beside the
  // controls they drive, which is where a reader looking for them is
  // already looking.
  const keys = owner.createElement("span");
  keys.className = "toc-keys";
  keys.setAttribute("data-step-keys", "[]");
  keys.textContent = "[ ] step";
  bar.append(keys);

  // `UX-393`: back to the top appears once there *is* a top to go
  // back to. Below the first screen it is a control that does nothing,
  // which is the dead affordance `UX-194` ruled out.
  const topButton = bar.querySelector?.('[data-step="top"]');
  const showTop = () => {
    const past = (view?.scrollY ?? 0) > (view?.innerHeight ?? 0);
    if (topButton) topButton.hidden = !past;
  };
  showTop();
  view?.addEventListener?.("scroll", showTop, { passive: true });

  // The accelerator, for the keyboard reader `UX-223` established.
  // Bracket keys because they are unmodified, unclaimed here, and on
  // every layout; ignored while the reader is typing, or the palette
  // would lose two characters.
  owner.addEventListener?.("keydown", (event) => {
    if (event.key !== "[" && event.key !== "]") return;
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    const tag = event.target?.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    event.preventDefault?.();
    (event.key === "]" ? next : previous)();
  });

  // After the title, before the chapters: the first thing in the rail
  // after its name, which is where a reader looks for its controls.
  const title = nav.querySelector?.(".toc-title");
  if (title?.nextSibling) nav.insertBefore(bar, title.nextSibling);
  else nav.append(bar);
  return { node: bar, next, previous, top };
}

export function scrollspy(root, nav, { observer } = {}) {
  const Observer = observer
    ?? (typeof IntersectionObserver === "function" ? IntersectionObserver
                                                   : null);
  if (!Observer || !nav) return null;
  const links = new Map(
    [...(nav.querySelectorAll?.("[data-toc]") ?? [])]
      .map((link) => [link.getAttribute("data-toc"), link]));
  const targets = sections(root)
    .filter((s) => links.has(s.getAttribute("data-section")));
  if (!targets.length) return null;

  const visible = new Set();
  // Which of the sections on screen the reader would call "here": the
  // last one that has already started above the reading line. Not the
  // first in document order - the sticky header leaves the tail of the
  // previous section on screen after a jump, and that section would
  // keep the mark. Measured on `macro_micro`: jumping to `overview`
  // marked `readers` under the first-in-order rule, and `evidence`
  // under a nearest-to-the-top rule, because two headings 103px apart
  // are both within a header's height of the top.
  //
  // The line is a fraction of the window rather than the header's
  // measured height: the header is sticky and its height is a layout
  // read of its own, and any line between the header and the first
  // fifth of the screen picks the same section.
  const READING_LINE = 0.15;
  const here = (on, height) => {
    const line = height * READING_LINE;
    let started = null;
    for (const section of on) {
      if ((section.getBoundingClientRect?.().top ?? 0) <= line) started = section;
    }
    return started ?? on[0];
  };
  const mark = () => {
    // Document order: `targets` is in document order and `visible` is a
    // set, so filtering here rather than iterating the set is what makes
    // "the last one that has started" mean anything.
    const on = targets.filter((s) => visible.has(s));
    const current = on.length
      ? here(on, root.ownerDocument?.defaultView?.innerHeight ?? 900)
      : null;
    for (const link of links.values()) {
      link.removeAttribute("data-current");
      link.removeAttribute("aria-current");
    }
    const link = current && links.get(current.getAttribute("data-section"));
    if (link) {
      link.setAttribute("data-current", "true");
      link.setAttribute("aria-current", "location");
    }
  };

  const watch = new Observer((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) visible.add(entry.target);
      else visible.delete(entry.target);
    }
    mark();
  // The whole viewport, so a section taller than the screen still
  // counts as on screen while the reader is inside it. The reading
  // line above is what turns "on screen" into "here".
  }, { threshold: 0 });
  for (const section of targets) watch.observe(section);
  return watch;
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
  const detail = (payload?.critical_path_detail ?? [])
    .find((row) => row.element_uid === uid);
  const durations = payload?.elements?.element_durations ?? {};
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
