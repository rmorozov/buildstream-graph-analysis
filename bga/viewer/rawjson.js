// UX-302: the *deliberate* raw JSON - the second of the two escapes §1
// allows, and the reason the rule is "unless it is deliberate" rather
// than "never".
//
// The first escape is `UX-277`'s labeled fold, which the page decides
// on: past the nesting cap a value is folded as text. This one the
// **reader** decides on, per section, and it exists because of what
// people actually do with a report - paste a piece of it into an issue.
// Before this, the only way to get a section's published values out of
// the page was to read the payload file the page was built from, which
// an exported single-file report does not have beside it.
//
// Three properties it owes:
//
//   - **it works in the export.** The affordance is for the person the
//     report was sent to, who has one HTML file and no server, so it is
//     built from the payload the page already carries rather than
//     fetched. `UX-195`'s standing rule.
//   - **it leaves nothing behind.** Shown then hidden must restore the
//     section exactly - the guard compares a serialisation of the
//     section before and after, not just its child count, because a
//     stray empty wrapper is precisely what a child count misses.
//   - **it is labeled.** The JSON lives under `data-raw-json`, which is
//     what the boot guard allowlists. Raw JSON that arrives any other
//     way is a defect, and stays one.

/**
 * Which published value produced which section.
 *
 * A `WeakMap` rather than an attribute: the payload slice is a live
 * object, and serialising it into the DOM up front would put every
 * section's JSON in the document whether or not anyone asked - the
 * weight `UX-267` removed, reintroduced by the control meant to
 * replace it. `chapters.js` re-sorts the sections after they are
 * built; re-parenting a node does not disturb a `WeakMap` keyed on it.
 */
const SECTION_SOURCES = new WeakMap();

/** Remember what a section was rendered from. Returns the section. */
export function recordSource(section, value) {
  if (section && value !== undefined) SECTION_SOURCES.set(section, value);
  return section;
}

/** The published value a section was rendered from, or `undefined`. */
export function sourceOf(section) {
  return SECTION_SOURCES.get(section);
}

export const SHOW = "view as JSON";
export const HIDE = "hide JSON";

/** Two-space indent: this is read and pasted, not transmitted. */
export function sectionJson(value) {
  return JSON.stringify(value, null, 2);
}

/**
 * Give every section that has a recorded source a "view as JSON"
 * toggle, and return the keys that got one.
 *
 * Sections with no source get no toggle rather than an empty one: the
 * page builds several sections (the decision panel, the overview) by
 * composing values from across the document, and "the JSON for this
 * section" is not a thing those have. A control that showed `{}` for
 * them would be worse than no control.
 */
export function jsonToggles(root, { document: doc } = {}) {
  const given = [];
  for (const section of root?.querySelectorAll?.("section[data-section]") ?? []) {
    const key = section.getAttribute("data-section");
    const value = SECTION_SOURCES.get(section);
    if (value === undefined) continue;
    const heading = section.querySelector?.("h2");
    if (!heading) continue;

    const button = doc.createElement("button");
    button.className = "json-toggle";
    button.setAttribute("data-json-toggle", key);
    button.setAttribute("aria-expanded", "false");
    button.textContent = SHOW;

    let shown = null;
    button.addEventListener("click", () => {
      if (shown) {
        shown.remove();
        shown = null;
        button.setAttribute("aria-expanded", "false");
        button.textContent = SHOW;
        return;
      }
      const box = doc.createElement("div");
      box.className = "section-json";
      // The allowlisted marker. The boot guard walks every text node
      // for JSON-shaped content and forgives exactly what is under
      // this attribute and under the labeled fold; anything else is a
      // section that reopened the wall.
      box.setAttribute("data-raw-json", key);
      const pre = doc.createElement("pre");
      pre.textContent = sectionJson(value);
      box.append(pre);
      section.append(box);
      shown = box;
      button.setAttribute("aria-expanded", "true");
      button.textContent = HIDE;
    });

    heading.append(button);
    given.push(key);
  }
  return given;
}
