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

import { duration, quantity, title } from "./format.js";

/**
 * `UX-347`: **the distance budget, and what a folded chapter says.**
 *
 * Round 52 measured the click budget being met by never folding: 51
 * `details` on the page, 3 open, every *section* permanently expanded,
 * and the document 22.7 screens after `UX-346`'s note removal. Zero
 * clicks to `confidence` - and 19.9 screens of scroll. A click is
 * directed; a screen of scroll is a search past everything the reader
 * did not ask for, and only the first was ever measured.
 *
 * So every chapter but the first opens to its heading, its own
 * question and **one line answering it from published fields**, and
 * expands on demand. `answer` below is that line, per chapter: it
 * reads the payload the page is already rendering, returns `null`
 * when the fields it needs are absent (a first run has no comparison;
 * a Plane-1-only run has no join), and never computes anything the
 * document does not publish - a chapter summary that derived its own
 * numbers would be a second pipeline, disagreeing quietly.
 */
function largest(map, field) {
  let best = null;
  for (const [key, value] of Object.entries(map ?? {})) {
    const at = typeof value === "number" ? value : value?.[field];
    if (typeof at !== "number") continue;
    if (!best || at > best.value) best = { key, value: at, row: value };
  }
  return best;
}

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
    // `UX-348`: `blast-offline` is gone - the export draws the same
    // `blast` section, with the command instead of the search box.
    sections: ["resource_blast", "blast", "blast-tree",
               "whatif", "perfetto-questions"],
    // The widest change this graph can absorb, from `elements.blast_radius`
    // - the population the chapter's own first table ranks.
    answer(payload) {
      const worst = largest(payload?.elements?.blast_radius, "downstream_count");
      if (!worst) return null;
      const cost = worst.row?.weighted_duration_us;
      return `A change to ${worst.key} rebuilds `
        + `${quantity(worst.value, "count")} elements`
        + (typeof cost === "number" ? ` (${duration(cost)} of work)` : "")
        + " - the widest here.";
    },
  },
  {
    id: "compare",
    title: "What changed since last time?",
    // Only rendered when there is something to compare against, so the
    // chapter is absent on a first run rather than empty.
    sections: ["culprits", "band", "store-trend"],
    // Absent on a first run, so the sentence is too rather than
    // reading "no change" over a comparison that was never made.
    answer(payload) {
      const verdict = payload?.comparison?.verdict ?? payload?.verdict;
      const delta = payload?.comparison?.delta_us ?? payload?.delta_us;
      if (!verdict) return null;
      return `${title(String(verdict))}`
        + (typeof delta === "number" ? `, ${duration(Math.abs(delta))} `
            + `${delta < 0 ? "faster" : "slower"}` : "")
        + " than the baseline.";
    },
  },
  {
    id: "time",
    title: "Where did the time go?",
    // `UX-344`: the tables `signals` held that are about *time* rather
    // than about an element - each its own section since the namespace
    // was lifted, and each named here rather than left to its rail,
    // because "act" reaches this chapter and "prove" does not.
    sections: ["attribution", "attribution_hints",
               "critical_path_detail", "critical-path-drawn", "horizon",
               "optimization_horizon", "latent_heavies", "joint_saving",
               "cache", "fetch_build_overlap", "wall_clock_share_us",
               "element_duration_distribution", "pipeline_overhead"],
    // The run's wall-clock and the biggest thing it went on, named by
    // the attribution split rather than by this file's opinion.
    answer(payload) {
      const total = payload?.total_duration_us;
      const buckets = Object.fromEntries(
        Object.entries(payload?.attribution ?? {}).filter(
          ([key, value]) => key.endsWith("_us") && typeof value === "number"));
      const worst = largest(buckets);
      if (typeof total !== "number" || !worst) return null;
      return `${duration(total)} wall-clock, of which `
        + `${duration(worst.value)} is `
        + `${title(worst.key, "duration_us").toLowerCase()}.`;
    },
  },
  {
    id: "machine",
    title: "Was the machine used well?",
    // `UX-275` published `capacity_recommendation` into this document,
    // and an unchaptered section is one the guard reddens on - which is
    // what put it here rather than at the foot of the page under
    // "Everything else".
    sections: ["occupancy", "utilisation", "floors", "capacity_verdict",
               // `UX-344`: how much was runnable and not running is a
               // fact about the machine, not about an element - the one
               // lifted table whose rail points at the wrong chapter.
               "ready_queue", "capacity_recommendation"],
    // What the run was given and how much of it was used - the two
    // numbers the chapter's own verdict is computed from.
    answer(payload) {
      const slots = payload?.capacity_recommendation?.builders
        ?? payload?.utilisation?.effective_cpus;
      const used = payload?.floors?.occupancy_share;
      if (typeof used !== "number") return null;
      return (typeof slots === "number"
        ? `${quantity(slots, "count")} builder slots, ` : "")
        + `${quantity(used, "share")} of their time used.`;
    },
  },
  {
    id: "elements",
    title: "Which elements, and how do they connect?",
    // `UX-344`: `structural`'s nine tables, and the element population
    // itself. The namespace was one section holding nine; these are the
    // nine, in the order the document publishes them.
    sections: ["elements", "graph_summary", "graph_metrics", "bottleneck",
               "parallelism", "sensitivity", "deferrability",
               "batch_opportunities", "consolidation_candidates",
               "serialization_point_risks", "leaf_analysis",
               "blast_radius_distribution", "element_join"],
    // How many elements, and the one that costs the most - the row a
    // reader opening this chapter is looking for.
    answer(payload) {
      const count = payload?.graph_summary?.total_elements;
      const worst = largest(payload?.elements?.element_durations);
      if (typeof count !== "number") return null;
      return `${quantity(count, "count")} elements`
        + (worst ? `; the slowest is ${worst.key} at ${duration(worst.value)}.`
                 : ".");
    },
    // `UX-216`'s one section per element, and `UX-278`'s built on
    // demand: there is one per element the report names, so they are
    // matched by prefix rather than listed.
    prefix: "element-",
  },
  {
    id: "believe",
    title: "How much of this can I believe?",
    sections: ["confidence", "violations", "timestamp_agreement",
               // `UX-344`: every claim's chain, published once. It is
               // this chapter's question by construction.
               "provenance",
               "plane2_coverage", "element_join_coverage"],
    // The one number this chapter exists to qualify, and the count
    // that most often explains it.
    answer(payload) {
      const primary = payload?.confidence?.primary;
      if (typeof primary !== "number") return null;
      const violations = payload?.confidence?.ordering_violations;
      return `${quantity(primary, "share")} of this report resolves to `
        + "this run's own record"
        + (typeof violations === "number" && violations > 0
            ? `, and ${quantity(violations, "count")} recorded orderings `
              + "contradict the graph." : ".");
    },
  },
  {
    id: "run",
    title: "Which run is this?",
    // `UX-285`: the identity is reference, and reference goes last.
    // `UX-344`: `document_shape` is a fact about the document rather
    // than about the run it describes, which is what this chapter holds.
    sections: ["summary", "run_instance", "producer", "document_shape"],
    // When it was taken, on what, and under which contract - the
    // three questions this chapter's own blocks answer. Not the run
    // identity hash: sixty-four characters of it is what the block
    // itself is for, and a summary that pasted it would be the block.
    answer(payload) {
      const started = payload?.run_instance?.started_at;
      const host = payload?.run_instance?.host_manifest?.cpu_model;
      const contract = payload?.schema;
      // The golden fixture's run instance carries a directory and
      // nothing else, so this degrades rather than printing "as
      // analyze/v3." as if it were a sentence.
      const when = started
        ? `Captured ${started}${host ? ` on ${host}` : ""}` : null;
      if (when) return `${when}${contract ? `, written as ${contract}` : ""}.`;
      return contract ? `Written as ${contract}.` : null;
    },
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
export function chapters(root, doc, payload) {
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
      box = makeBox(chapter, doc, payload, chapter.id === CHAPTERS[0].id);
      boxes.set(chapter.id, box);
    }
    for (const node of members) {
      node.setAttribute("data-chapter", chapter.id);
      box.append(node);
    }
    // UX-347: the control counts what the chapter holds, and it holds
    // nothing until the loop above - a box labelled at construction
    // said "Show 0 sections" on every chapter, measured on both
    // fixtures before this line existed.
    labelFold(box);
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

function makeBox(chapter, doc, payload, first) {
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

  // UX-347: the first chapter is the decision and stays open - a
  // reader who has to open the verdict has been handed nothing. Every
  // other one opens to this much: its question, one line answering it,
  // and a control saying how many sections are behind it.
  box.setAttribute("data-open", String(Boolean(first)));
  const said = safely(chapter, payload);
  if (said) {
    const line = doc.createElement("p");
    line.className = "chapter-answer";
    line.setAttribute("data-chapter-answer", chapter.id);
    line.textContent = said;
    box.append(line);
  }
  if (!first) {
    const toggle = doc.createElement("button");
    toggle.className = "chapter-open";
    toggle.setAttribute("type", "button");
    toggle.setAttribute("data-chapter-open", chapter.id);
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-controls", `chapter-${chapter.id}`);
    toggle.addEventListener?.("click", () => setOpen(box, !isOpen(box)));
    title.append(toggle);
    labelFold(box);
  }
  return box;
}

/**
 * A chapter's own sentence, or `null`.
 *
 * Wrapped, because a summary that threw would take the chapter's
 * heading with it - `UX-335`'s rule that one bad value costs one
 * section, applied one level up. A chapter with no line is a chapter
 * that says so by saying nothing, which is the honest answer for a
 * payload whose fields are absent.
 */
function safely(chapter, payload) {
  if (typeof chapter.answer !== "function" || !payload) return null;
  try {
    const said = chapter.answer(payload);
    return typeof said === "string" && said.trim() ? said : null;
  } catch (error) {
    return null;
  }
}

/** Whether a chapter box is open. The first one always is. */
export function isOpen(box) {
  return box?.getAttribute?.("data-open") !== "false";
}

/**
 * Open or shut one chapter, and say on its control how many sections
 * are behind it (`§3a.1`: a fold names its count before it is opened).
 */
export function setOpen(box, open) {
  if (!box) return box;
  box.setAttribute("data-open", String(Boolean(open)));
  labelFold(box);
  return box;
}

/**
 * Open or shut **every** chapter that has a control.
 *
 * `UX-355`: the rail's "Expand all" was built on `collapsible().all()`,
 * which walks *sections* - and `UX-347` moved the document's fold to
 * the chapter. Sections are default-open, so from a fresh load
 * `all(false)` set open what was already open and the page did not
 * move: 3,548 px and 1 of 7 chapters before the press and after it.
 *
 * The first chapter is skipped, and that is not an oversight: it has no
 * toggle, because `UX-347` decided the decision stays open - "a reader
 * who has to open the verdict has been handed nothing". Shutting it
 * from here would make a fold with no way back, which is the defect
 * this function exists to remove rather than move.
 */
export function setAllOpen(root, open) {
  const boxes = [...(root?.querySelectorAll?.("section.chapter") ?? [])];
  for (const box of boxes) {
    if (!box.querySelector?.("[data-chapter-open]")) continue;
    setOpen(box, open);
  }
  return boxes.length;
}

function labelFold(box) {
  const toggle = box.querySelector?.("[data-chapter-open]");
  if (!toggle) return;
  const held = box.querySelectorAll?.("[data-section]")?.length ?? 0;
  const open = isOpen(box);
  toggle.setAttribute("aria-expanded", String(open));
  toggle.textContent = open ? "Hide" : `Show ${held} section${held === 1 ? "" : "s"}`;
  toggle.setAttribute("title", open
    ? `Fold "${box.getAttribute("aria-label")}" back to its answer`
    : `Open "${box.getAttribute("aria-label")}"`);
}

/**
 * Open whatever chapter holds `node`, and return it.
 *
 * Every way into a section goes through here: the rail's links, the
 * jump box, a pasted `#anchor`, `hashchange`. A fold that a link
 * cannot open is a section the click budget cannot reach, which is
 * the defect `UX-347` would have introduced rather than fixed.
 */
export function revealChapter(node) {
  let box = node;
  while (box && !(box.classList?.contains?.("chapter")
                  ?? String(box.className ?? "").includes("chapter"))) {
    box = box.parentElement ?? box._parent;
  }
  if (box && !isOpen(box)) setOpen(box, true);
  return box ?? null;
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
    // UX-347: the control counts what the chapter holds, and this is
    // the one path that changes that after boot.
    labelFold(box);
  }
  return node;
}
