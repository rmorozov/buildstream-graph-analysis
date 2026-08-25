/**
 * UX-286: the report has chapters.
 *
 * Measured at 1440x900 in Chrome 141, before this landed:
 *
 * ```text
 *                            1,202-element     macro_micro
 * sections                             48              39
 * document                       18.8 scr        20.1 scr
 * median section                 0.24 scr        0.35 scr
 * sections under 0.8 screens           46 (95%)        37 (94%)
 * ```
 *
 * The median section is 216 pixels. The page was not a document with
 * chapters; it was forty-eight fragments read by scrolling past them,
 * and nothing grouped them - so the rail listed thirty-one top-level
 * entries and the reader's only unit of navigation was the fragment.
 *
 * Direction 13 refuses the other half of the proposal on the same
 * measurement: padding every section to one screen adds 31.3 screens of
 * whitespace to the synthetic run. Grouping is free; height is not.
 *
 * **What a chapter is.** A question a reader has, holding the sections
 * that answer it. Every payload section already publishes its own
 * question (`bga:question`), and the chapter titles here are the
 * questions those group into - `findings` ("What did this run
 * conclude?"), `headline` ("What should I fix first, and what is it
 * worth?") and `next_steps` ("What should I run next?") are three
 * spellings of *what should I do*, and they are one chapter.
 *
 * **Why the table is here and not in the schema.** Nine of the
 * forty-eight sections on the synthetic run are built by the page and
 * published by no contract at all - the decision panel, the drawn
 * critical path, the blast box, the element blocks. A hint can only
 * name sections the schema has, so a chaptering that lived in
 * `bga:question`'s neighbourhood would leave a fifth of the document
 * unassigned. The published `bga:rail` is still what places a section
 * this table does not name: a new payload key lands in the chapter its
 * *rail* belongs to rather than in a bucket at the end.
 */

// The chapters, in the order the document reads. Each names the
// question it answers, and holds the sections that answer it.
export const CHAPTERS = [
  {
    id: "decide",
    title: "What should I do?",
    // `UX-207`'s first screen, plus the diagnosis that justifies it.
    sections: ["decision", "evidence", "overview",
               "findings", "headline", "next_steps"],
  },
  {
    id: "change",
    title: "What if I change this?",
    // The queries rather than the measurements: what one edit rebuilds
    // (`UX-172`), what fixing a set would be worth (`UX-219`), and the
    // questions to ask the timeline once you leave this page.
    // `UX-285` put the blast control next to `findings`; a chapter
    // boundary is where that belongs, one heading below it.
    sections: ["resource_blast", "blast", "blast-offline", "blast-tree",
               "whatif", "perfetto-questions"],
  },
  {
    id: "compare",
    title: "What changed since last time?",
    // Only rendered when there is something to compare against, so the
    // chapter is absent on a first run rather than empty.
    sections: ["culprits", "band", "store-trend"],
  },
  {
    id: "time",
    title: "Where did the time go?",
    sections: ["attribution", "attribution_hints", "signals",
               "critical_path_detail", "critical-path-drawn", "horizon",
               "pipeline_overhead"],
  },
  {
    id: "machine",
    title: "Was the machine used well?",
    // `UX-275` published `capacity_recommendation` into this document,
    // and an unchaptered section is one the guard reddens on - which is
    // what put it here rather than at the foot of the page under
    // "Everything else".
    sections: ["occupancy", "utilisation", "floors", "capacity_verdict",
               "capacity_recommendation"],
  },
  {
    id: "elements",
    title: "Which elements, and how do they connect?",
    sections: ["structural", "element_join"],
    // `UX-216`'s one section per element, and `UX-278`'s built on
    // demand: there is one per element the report names, so they are
    // matched by prefix rather than listed.
    prefix: "element-",
  },
  {
    id: "believe",
    title: "How much of this can I believe?",
    sections: ["confidence", "violations", "timestamp_agreement",
               "plane2_coverage", "element_join_coverage"],
  },
  {
    id: "run",
    title: "Which run is this?",
    // `UX-285`: the identity is reference, and reference goes last.
    sections: ["summary", "run_instance", "producer"],
  },
];

// Where a section the table does not name goes, by its published
// `bga:rail`. The contract still places it: a payload key added later
// lands in the chapter its rail already says it belongs to.
export const RAIL_CHAPTER = {
  decide: "decide",
  act: "time",
  investigate: "elements",
  prove: "believe",
  raw: "run",
};

// The last chapter, for a section with no entry and no rail. It is not
// a hiding place: `test_the_report_has_chapters` asserts it is empty on
// both runs, so a section that lands here reddens a guard rather than
// disappearing into a bucket.
export const UNCHAPTERED = { id: "more", title: "Everything else" };

// The focus panel `UX-222` prepends and removes again. It is not part
// of the document - unfocusing must leave the page byte-identical to
// never-focused - so chaptering steps over it rather than filing it.
const TRANSIENT = "focus-investigation";

/** Which chapter a section belongs to: the table first, then its rail. */
export function chapterFor(key, rail) {
  if (!key) return UNCHAPTERED.id;
  for (const chapter of CHAPTERS) {
    if (chapter.sections.includes(key)) return chapter.id;
    if (chapter.prefix && key.startsWith(chapter.prefix)) return chapter.id;
  }
  return RAIL_CHAPTER[rail] ?? UNCHAPTERED.id;
}

function chapterOf(node) {
  return chapterFor(node.getAttribute?.("data-section"),
                    node.getAttribute?.("data-rail"));
}

function isTransient(node) {
  return node.getAttribute?.("data-role") === TRANSIENT;
}

/**
 * Group the document's sections into chapters, in place.
 *
 * Idempotent, and it moves rather than rebuilds: a section keeps its
 * identity, its listeners and its view state, because the alternative -
 * re-rendering into a new tree - would drop everything `UX-211` and
 * `UX-222` wired to the nodes that already exist.
 *
 * Relative order inside a chapter is the order the document already
 * had. This decides which chapter a section is in, not where it sits
 * among its neighbours; those are two separate claims and only the
 * first one is this function's.
 */
export function chapters(root, doc) {
  if (!root || !doc) return [];
  const boxes = openBoxes(root);
  const loose = [...(root.children ?? [])].filter(
    (node) => node.getAttribute?.("data-section") && !isTransient(node));

  const held = new Map();
  for (const node of loose) {
    const id = chapterOf(node);
    if (!held.has(id)) held.set(id, []);
    held.get(id).push(node);
  }

  const made = [];
  for (const chapter of [...CHAPTERS, UNCHAPTERED]) {
    const members = ordered(chapter, held.get(chapter.id) ?? []);
    let box = boxes.get(chapter.id);
    if (!members.length && !box) continue;
    if (!box) {
      box = makeBox(chapter, doc);
      boxes.set(chapter.id, box);
    }
    for (const node of members) {
      node.setAttribute("data-chapter", chapter.id);
      box.append(node);
    }
    root.append(box);
    made.push(box);
  }
  return made;
}

/**
 * The members of one chapter, in the order the chapter declares.
 *
 * The table is the order, not the document: `resource_blast` is a
 * payload section and the blast control is appended by `boot` five
 * steps later, so document order would put `whatif` between the table
 * and the query over it - which is the pairing `UX-285` measured and
 * fixed. Anything the chapter matched by prefix or by rail has no
 * declared position and keeps the order the document gave it, after
 * the sections that do.
 */
function ordered(chapter, members) {
  const at = (node) => chapter.sections?.indexOf(
    node.getAttribute?.("data-section")) ?? -1;
  const declared = members.filter((node) => at(node) >= 0)
    .sort((one, two) => at(one) - at(two));
  return [...declared, ...members.filter((node) => at(node) < 0)];
}

function makeBox(chapter, doc) {
  const box = doc.createElement("section");
  box.className = "chapter";
  box.setAttribute("data-chapter", chapter.id);
  box.setAttribute("id", `chapter-${chapter.id}`);
  // A landmark rather than a heading level: the section headings below
  // are `h2` and stay `h2` - twenty-four of them, plus the collapse and
  // focus rules that select `> h2` - so a screen reader gets the
  // chapter as a named region it can jump to, instead of a heading
  // hierarchy that would lie about its depth.
  box.setAttribute("role", "region");
  box.setAttribute("aria-label", chapter.title);
  const title = doc.createElement("h2");
  title.className = "chapter-title";
  title.textContent = chapter.title;
  box.append(title);
  return box;
}

/** The chapter boxes already in the document: `id -> box`. */
function openBoxes(root) {
  const boxes = new Map();
  for (const node of root.children ?? []) {
    const id = node.getAttribute?.("data-chapter");
    if (id && !node.getAttribute?.("data-section")) boxes.set(id, node);
  }
  return boxes;
}

/**
 * File one section that arrived after the document was chaptered.
 *
 * `UX-278` builds an element block when its anchor is followed, which
 * is long after `boot` grouped everything. Appended to the root it
 * would land below the last chapter - past the identity block that is
 * supposed to close the page (`UX-285`) - so it joins its chapter
 * instead.
 */
export function fileInChapter(root, node, doc) {
  if (!root || !node) return node;
  const id = chapterOf(node);
  let box = openBoxes(root).get(id);
  if (!box && doc) {
    chapters(root, doc);
    box = openBoxes(root).get(id);
  }
  if (box) {
    node.setAttribute("data-chapter", id);
    box.append(node);
  }
  return node;
}
