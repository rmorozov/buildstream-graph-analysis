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

/** The sections the page actually rendered, in document order. */
export function sections(root) {
  return [...(root.querySelectorAll?.("section[data-section]") ?? [])];
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

  // UX-209: grouped by rail - which part of the argument a section
  // belongs to - rather than by payload key order. Still generated from
  // what was actually rendered: a section with no declared rail lands
  // in `raw`, never nowhere.
  const grouped = new Map(RAILS.map((rail) => [rail, []]));
  for (const key of keys) {
    const section = root.querySelector?.(`[data-section="${key}"]`)
      ?? [...(root.children ?? [])].find(
        (n) => n.getAttribute?.("data-section") === key);
    const rail = section?.getAttribute?.("data-rail");
    grouped.get(RAILS.includes(rail) ? rail : "raw").push(key);
  }

  for (const rail of RAILS) {
    const members = grouped.get(rail);
    if (!members.length) continue;
    const groupName = doc.createElement("p");
    groupName.className = "toc-rail";
    groupName.setAttribute("data-rail", rail);
    groupName.textContent = rail;
    nav.append(groupName);
    const list = doc.createElement("ul");
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
