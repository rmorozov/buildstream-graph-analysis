// UX-196: three views where a drawing says what sentences strain to.
//
// The discipline from UX-193 still holds: these render *published*
// payloads, and they draw only where the generic table genuinely cannot
// say it. That is exactly two SVGs - the band strip and the store trend
// - and no library behind either. Everything else here is layout.
//
// Nothing below recomputes anything. `compare/v1` already carries the
// band edges, the observed extent and the verdict; `store/v1` already
// carries the sizes and the incomplete reasons. A viewer that did its
// own arithmetic would be a second implementation of the analysis, and
// the first thing it would do is disagree with the first one.

const SVG = "http://www.w3.org/2000/svg";

function svg(tag, attrs = {}) {
  const node = document.createElementNS(SVG, tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value !== null && value !== undefined) node.setAttribute(name, String(value));
  }
  return node;
}


// Small local formatters rather than importing app.js's: app.js already
// imports *this* module, and a cycle between the two would work today
// (both export hoisted declarations) and break the first time either
// grows a top-level side effect. `UX-201` folds formatting into one
// schema-driven place, which is where this duplication goes to die.
function seconds(microseconds) {
  const s = microseconds / 1e6;
  return s < 90 ? `${s.toFixed(1)} s` : `${(s / 60).toFixed(1)} min`;
}

function mib(value) {
  const units = ["B", "KiB", "MiB", "GiB"];
  let n = value, i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i += 1; }
  return `${i === 0 ? n : n.toFixed(1)} ${units[i]}`;
}

// --------------------------------------------------------------- band
//
// `UX-170`'s disputed region is the case this drawing exists for: a
// candidate outside the noise band but inside the range the baseline
// runs actually spanned. In prose that took a paragraph and still read
// like a paradox. Drawn, the marker simply lands between the strip's
// edge and the dots' extent, and the question answers itself.

export function bandGeometry(compare) {
  const band = compare.baseline_band;
  if (!band) return null;

  const low = band.band_low_us ?? band.low_us ?? band.low;
  const high = band.band_high_us ?? band.high_us ?? band.high;
  const observedLow = band.observed_low_us ?? band.min_us ?? low;
  const observedHigh = band.observed_high_us ?? band.max_us ?? high;
  const candidate = compare.candidate?.total_duration_us;
  if ([low, high, candidate].some((v) => typeof v !== "number")) return null;

  // The axis spans whichever is wider - the band or what was observed -
  // with a margin so a candidate just outside is still on the canvas.
  const lo = Math.min(low, observedLow, candidate);
  const hi = Math.max(high, observedHigh, candidate);
  const pad = (hi - lo) * 0.1 || 1;
  const min = lo - pad, max = hi + pad;
  const at = (value) => ((value - min) / (max - min)) * 100;

  const inBand = candidate >= low && candidate <= high;
  const inObserved = candidate >= observedLow && candidate <= observedHigh;
  return {
    min, max, at,
    band: { low, high, x: at(low), width: at(high) - at(low) },
    observed: { low: observedLow, high: observedHigh,
                x: at(observedLow), width: at(observedHigh) - at(observedLow) },
    candidate: { value: candidate, x: at(candidate) },
    runs: (band.runs ?? band.baseline_runs ?? [])
      .map((r) => (typeof r === "number" ? r : r.total_duration_us))
      .filter((v) => typeof v === "number")
      .map((value) => ({ value, x: at(value) })),
    // The three-way answer, taken from the payload's own verdict where
    // it has one rather than re-derived from the numbers.
    where: inBand ? "inside the band"
      : inObserved ? "outside the band, inside the observed range"
      : "outside both",
    disputed: !inBand && inObserved,
  };
}

export function renderBand(compare) {
  const geometry = bandGeometry(compare);
  if (!geometry) return null;

  const H = 74;
  const figure = svg("svg", {
    viewBox: `0 0 100 ${H}`, class: "band", preserveAspectRatio: "none",
    role: "img", "data-where": geometry.where,
    "data-disputed": String(geometry.disputed),
    "data-candidate-x": geometry.candidate.x.toFixed(3),
    "data-band-x": geometry.band.x.toFixed(3),
    "data-band-width": geometry.band.width.toFixed(3),
    "data-observed-x": geometry.observed.x.toFixed(3),
    "data-observed-width": geometry.observed.width.toFixed(3),
  });
  figure.append(svg("rect", {
    x: geometry.observed.x, width: geometry.observed.width,
    y: 18, height: 26, class: "observed", "data-role": "observed",
  }));
  figure.append(svg("rect", {
    x: geometry.band.x, width: geometry.band.width,
    y: 24, height: 14, class: "band-strip", "data-role": "band",
  }));
  for (const run of geometry.runs) {
    figure.append(svg("circle", {
      cx: run.x, cy: 31, r: 1.4, class: "baseline-dot", "data-role": "run",
      "data-value": run.value,
    }));
  }
  figure.append(svg("line", {
    x1: geometry.candidate.x, x2: geometry.candidate.x, y1: 8, y2: 54,
    class: "candidate", "data-role": "candidate",
    "data-value": geometry.candidate.value,
  }));

  const wrapper = document.createElement("section");
  wrapper.setAttribute("data-section", "band");
  const heading = document.createElement("h2");
  heading.textContent = "The band";
  const caption = document.createElement("p");
  caption.className = "muted";
  caption.textContent = geometry.disputed
    ? "The candidate is outside the noise band but inside the range the "
      + "baseline runs themselves spanned — the marker sits between the "
      + "strip and the dots' extent. UX-170 calls this the disputed "
      + "region, and it is why compare declines to call it a regression."
    : `The candidate is ${geometry.where}.`;
  wrapper.append(heading, figure, caption);
  return wrapper;
}

// -------------------------------------------------------------- trend
//
// `--list`, made visual. The question is "is this project drifting",
// and the answer is a shape.

export function renderTrend(store) {
  const rows = store?.snapshots ?? [];
  if (rows.length < 2) return null;

  const W = 100, H = 40;
  // UX-203: the axis is duration. It was `bytes`, so the trend
  // answered "is this project drifting" with disk usage.
  const sizes = rows.map((r) => r.total_duration_us ?? 0);
  const max = Math.max(...sizes, 1);
  const x = (i) => (rows.length === 1 ? W / 2 : (i / (rows.length - 1)) * W);
  const y = (v) => H - (v / max) * (H - 6) - 3;

  const figure = svg("svg", {
    viewBox: `0 0 ${W} ${H}`, class: "trend", preserveAspectRatio: "none",
    role: "img", "data-points": rows.length,
  });
  figure.append(svg("polyline", {
    points: rows.map((r, i) => `${x(i)},${y(r.total_duration_us ?? 0)}`).join(" "),
    class: "trend-line", fill: "none",
  }));
  for (const [index, row] of rows.entries()) {
    // Incomplete snapshots are *marked*, not hidden: they occupy the
    // disk, and a trend that quietly dropped them would answer the
    // drift question with a curated subset.
    const reason = row.incomplete_reason;
    // UX-203: the verdict colours the dot - the question the trend is
    // asked is whether this build is drifting, and the verdict is the
    // answer the rest of the tool already gives for one pair.
    const verdict = row.verdict_kind ?? "";
    const point = svg(reason ? "rect" : "circle", reason
      ? { x: x(index) - 1.3, y: y(row.total_duration_us ?? 0) - 1.3, width: 2.6,
          height: 2.6, class: "trend-point incomplete",
          "data-stamp": row.stamp, "data-incomplete": reason }
      : { cx: x(index), cy: y(row.total_duration_us ?? 0), r: 1.3,
          class: `trend-point${row.alias ? " aliased" : ""}`
                 + (verdict ? ` verdict-${verdict}` : ""),
          "data-stamp": row.stamp, "data-alias": row.alias ?? "",
          "data-verdict": verdict });
    // Size is still here, demoted to where it belongs: a detail you can
    // hover for, not the axis the question is answered on.
    const tip = svg("title");
    tip.textContent = [
      row.stamp,
      row.total_duration_us != null ? seconds(row.total_duration_us) : null,
      verdict ? verdict.replace(/_/g, " ") : null,
      row.cache_hit_rate != null
        ? `${(row.cache_hit_rate * 100).toFixed(0)}% cache hits` : null,
      row.bytes != null ? mib(row.bytes) : null,
    ].filter(Boolean).join(" · ");
    point.append(tip);
    figure.append(point);
  }

  const wrapper = document.createElement("section");
  wrapper.setAttribute("data-section", "store-trend");
  const heading = document.createElement("h2");
  heading.textContent = `The store (${rows.length} snapshots)`;
  const caption = document.createElement("p");
  caption.className = "muted";
  const incomplete = rows.filter((r) => r.incomplete_reason);
  caption.textContent = incomplete.length
    ? `Squares are the ${incomplete.length} snapshot(s) that are not `
      + `measurements (${[...new Set(incomplete.map((r) => r.incomplete_reason))]
          .join(", ")}); they are on disk, so they are on the chart.`
    : "Every snapshot here finished.";
  wrapper.append(heading, figure, caption);
  return wrapper;
}

// ---------------------------------------------------------- blast box
//
// The search box is a *transport*: it hands the target to the server,
// which calls the same function `bga blast` calls. No resolution
// happens here, because a second resolver would be a second answer.

export function renderBlastSearch(onQuery) {
  const wrapper = document.createElement("section");
  wrapper.setAttribute("data-section", "blast");
  const heading = document.createElement("h2");
  heading.textContent = "What rebuilds if I touch this?";
  const form = document.createElement("form");
  form.setAttribute("data-role", "blast-form");
  const input = document.createElement("input");
  input.setAttribute("data-role", "blast-input");
  input.placeholder = "a git url, a path in the project, or an element name";
  input.size = 52;
  const button = document.createElement("button");
  button.textContent = "Ask";
  const answer = document.createElement("div");
  answer.setAttribute("data-role", "blast-answer");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    answer.textContent = "asking…";
    try {
      const result = await onQuery(input.value);
      answer.replaceChildren(renderBlastAnswer(result));
    } catch (error) {
      answer.textContent = String(error.message ?? error);
    }
  });
  form.append(input, button);
  wrapper.append(heading, form, answer);
  return wrapper;
}

export function renderBlastAnswer(result) {
  const list = document.createElement("dl");
  list.className = "pairs";
  list.setAttribute("data-role", "blast-result");
  // Straight from `blast/v1`; the sentence about keying is the payload's
  // own, so the page and `bga blast` cannot phrase it differently.
  const rows = [
    ["Resolved as", result.resolved_as],
    ["Keying", result.keying],
    ["Direct", result.direct_count],
    ["Rebuilds", result.blast_count],
    ["Of which build", result.building_count],
    ["…and assemble", result.assembling_count],
    ["Measured", result.measured
      ? `${result.measured_seconds?.toFixed?.(1) ?? result.measured_seconds}s `
        + `over ${result.measured_elements} element(s)`
      : "not measured (--no-cost, or no run)"],
  ];
  for (const [name, value] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = name;
    const dd = document.createElement("dd");
    dd.textContent = value === null || value === undefined ? "—" : String(value);
    dd.setAttribute("data-key", name.toLowerCase().replace(/\W+/g, "_"));
    list.append(dt, dd);
  }
  // UX-206: and the same answer as a tree, under the summary that
  // counts it. The counts say how much; the tree says what, and at what
  // remove.
  const tree = renderBlastTree(result);
  if (!tree) return list;
  const wrapper = document.createElement("div");
  wrapper.append(list, tree);
  return wrapper;
}

// ------------------------------------------------- UX-202: the overview
//
// "Why is my build slow" answered at the top, before the sections.
//
// **The rule this is built under: no viewer arithmetic.** Every number
// below is read from a published field and rendered; none is computed
// here. A gap the JSON does not carry enters `analyze/v1` first, where
// the text renderer, CI and every external consumer get it too - which
// is Direction 7's rule, and the reason the waterfall is a *reading* of
// the report rather than a second opinion about it.

// The waterfall, in the order the time is spent. Each entry names the
// published field it reads; nothing here adds, subtracts or divides.
const WATERFALL = [
  { key: "untracked_head_us", label: "Before the first task", from: "attribution" },
  { key: "execution_on_chain_us", label: "Execution on the chain", from: "attribution" },
  { key: "dependency_wait_us", label: "Waiting on dependencies", from: "attribution" },
  { key: "resource_wait_us", label: "Waiting on resources", from: "attribution" },
  { key: "scheduler_wait_us", label: "Waiting on the scheduler", from: "attribution" },
  { key: "retry_wait_us", label: "Retries", from: "attribution" },
  { key: "idle_us", label: "Idle", from: "attribution" },
  { key: "untracked_tail_us", label: "After the last task", from: "attribution" },
];

// The certified floors, read the same way.
const FLOORS = [
  { key: "t_infinity_observed", label: "T∞ (observed)" },
  { key: "lb", label: "LB" },
  { key: "t_c", label: "T_C" },
  { key: "certified_headroom", label: "Certified headroom" },
];

function bar(label, value, total, extra = {}) {
  const row = document.createElement("div");
  row.className = "wf-row";
  for (const [name, attr] of Object.entries(extra)) row.setAttribute(name, attr);
  const name = document.createElement("span");
  name.className = "wf-label";
  name.textContent = label;
  const track = document.createElement("span");
  track.className = "wf-track";
  const fill = document.createElement("span");
  fill.className = "wf-fill";
  // The only division in this file, and it is a *width*, not a number
  // the reader is told: the printed value is `value` itself.
  fill.setAttribute("style",
    `width: ${total > 0 ? Math.max(0, Math.min(100, (value / total) * 100)) : 0}%`);
  track.append(fill);
  const amount = document.createElement("span");
  amount.className = "wf-value num";
  amount.setAttribute("data-raw", String(value));
  amount.textContent = seconds(value);
  row.append(name, track, amount);
  return row;
}

export function renderOverview(payload) {
  const total = payload?.total_duration_us;
  const attribution = payload?.attribution;
  if (typeof total !== "number" || !attribution) return null;

  const section = document.createElement("section");
  section.setAttribute("data-section", "overview");
  section.setAttribute("id", "overview");
  const heading = document.createElement("h2");
  heading.textContent = "Where the time went";
  section.append(heading);

  section.append(bar("Total duration", total, total,
                     { "data-field": "total_duration_us" }));

  // UX-207: the largest segments stay visible and the tail folds -
  // **with no viewer-summed "Other" row.** A grouped figure would be a
  // number the pipeline never published, which is the one thing this
  // drawing is not allowed to invent. Ordering is by published value;
  // the fold hides rows, it does not merge them.
  const drawn = WATERFALL
    .map((entry) => ({ entry, value: attribution[entry.key] }))
    .filter((row) => typeof row.value === "number" && row.value !== 0)
    .sort((a, b) => b.value - a.value);
  const head = drawn.slice(0, OVERVIEW_SHOWN);
  const tail = drawn.slice(OVERVIEW_SHOWN);
  const segment = (row) => bar(row.entry.label, row.value, total, {
    "data-field": `attribution.${row.entry.key}`,
    // UX-199's anchors: each segment points at the section that
    // explains it.
    "data-section-link": "attribution",
  });
  for (const row of head) section.append(segment(row));
  if (tail.length) {
    const fold = document.createElement("details");
    fold.className = "overview-tail";
    fold.setAttribute("data-folded", String(tail.length));
    const summary = document.createElement("summary");
    summary.textContent = `${tail.length} smaller categories`;
    fold.append(summary);
    for (const row of tail) fold.append(segment(row));
    section.append(fold);
  }

  const floors = payload?.floors;
  if (floors) {
    const sub = document.createElement("h3");
    sub.textContent = "And the floors underneath it";
    section.append(sub);
    for (const entry of FLOORS) {
      const value = floors[entry.key];
      if (typeof value !== "number") continue;
      section.append(bar(entry.label, value, total, {
        "data-field": `floors.${entry.key}`,
        "data-section-link": "floors",
      }));
    }
  }
  return section;
}

/**
 * What this capture can support, before any number is believed.
 *
 * `UX-156`'s tone, and the place the refusal banners belong: an
 * interrupted or suspended run says so here rather than floating above
 * a report that looks otherwise ordinary.
 */
export function renderEvidence(payload) {
  const confidence = payload?.confidence ?? {};
  const instance = payload?.run_instance ?? {};
  const host = instance.host_manifest ?? {};
  const reason = instance.incomplete_reason;

  const rows = [];
  if (typeof confidence.primary === "number") {
    rows.push(["Confidence",
               `${(confidence.primary * 100).toFixed(0)}%`
               + (confidence.band ? ` (${confidence.band})` : ""),
               "confidence.primary"]);
  }
  if (typeof confidence.task_coverage === "number") {
    rows.push(["Task coverage",
               `${(confidence.task_coverage * 100).toFixed(0)}%`,
               "confidence.task_coverage"]);
  }
  // UX-202: Plane 2's half of "what can this capture support". Absent
  // when `analyze` had no Plane 2 report - and absent is the honest
  // rendering: a "0%" row would claim the hook saw nothing, when the
  // truth is that nobody looked.
  const plane2 = payload?.plane2_coverage;
  if (plane2 && typeof plane2.processes === "number") {
    rows.push(["Plane 2 coverage",
               `${plane2.processes} processes`
               + (typeof plane2.opens_coverage === "number"
                  ? `, opens ${(plane2.opens_coverage * 100).toFixed(0)}%` : ""),
               "plane2_coverage.processes"]);
  }
  if (host.cpu_model) {
    rows.push(["Host",
               [host.cpu_model, host.cpu_count && `${host.cpu_count} cpu`,
                host.memory_mb && `${Math.round(host.memory_mb / 1024)} GiB`]
                 .filter(Boolean).join(" · "),
               "run_instance.host_manifest"]);
  }
  if (instance.started_at) {
    rows.push(["Captured", instance.started_at, "run_instance.started_at"]);
  }
  if (!rows.length && !reason) return null;

  const section = document.createElement("section");
  section.setAttribute("data-section", "evidence");
  section.setAttribute("id", "evidence");
  const heading = document.createElement("h2");
  heading.textContent = "What this capture supports";
  section.append(heading);

  // UX-207: **the refusal renders once.** It used to appear here *and*
  // in `renderVerdict`, the same sentence in two banners - measured at
  // two `data-incomplete` nodes on an interrupted fixture. The banner
  // belongs above the decision, not inside a header a reader may have
  // collapsed, so `renderVerdict` keeps it and this stops drawing it.
  //
  // Everything else here compresses to one line: six rows at the top of
  // a page for values that matter only when they are alarming.
  const status = document.createElement("p");
  status.className = "status-line";
  status.setAttribute("data-role", "status");
  status.textContent = statusLine(payload);
  section.append(status);

  const fold = document.createElement("details");
  fold.className = "evidence-detail";
  const summary = document.createElement("summary");
  summary.textContent = "The numbers behind that";
  fold.append(summary);

  const list = document.createElement("dl");
  list.className = "pairs";
  for (const [label, value, field] of rows) {
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.setAttribute("data-field", field);
    detail.textContent = value;
    list.append(term, detail);
  }
  fold.append(list);
  section.append(fold);
  return section;
}

/**
 * `✓ high confidence · 100% task coverage · Plane 2 available`
 *
 * Every part read from a published field; a part with no field is
 * simply not said. The tick is the *band*, which `findings.py` decides
 * - the page does not get to call 0.87 high.
 */
export function statusLine(payload) {
  const confidence = payload?.confidence ?? {};
  const parts = [];
  if (confidence.band) {
    const mark = confidence.band === "high" ? "\u2713"
      : confidence.band === "low" ? "\u26a0" : "\u00b7";
    parts.push(`${mark} ${confidence.band} confidence`);
  } else if (typeof confidence.primary === "number") {
    parts.push(`confidence ${(confidence.primary * 100).toFixed(0)}%`);
  }
  if (typeof confidence.task_coverage === "number") {
    parts.push(`${(confidence.task_coverage * 100).toFixed(0)}% task coverage`);
  }
  const plane2 = payload?.plane2_coverage;
  parts.push(plane2 && typeof plane2.processes === "number"
    ? `Plane 2: ${plane2.processes} processes`
    : "Plane 2 not captured");
  return parts.join(" \u00b7 ");
}

// The same three sentences the CLI banners use. One source, so the
// page and the terminal cannot describe the same run differently.
export const INCOMPLETE = {
  failed: "This build failed: durations from a run that did not finish "
          + "are not measurements.",
  interrupted: "This capture was interrupted: durations from a run that did "
               + "not finish are not measurements.",
  suspended: "This capture spans a suspend: Plane 1 counts the sleep as "
             + "build time and Plane 2 does not, so the durations here are "
             + "not measurements.",
};


// ------------------------------------------------- UX-206: two graphs

// No general DAG viewer. The external review and Direction 7 arrived at
// that restraint independently: a BuildStream DAG rendering answers no
// question anyone asks, and the temptation to build one loses to the
// two drawings that *are* questions. Neither needs a layout algorithm -
// one is a list with widths, the other is an indented list.

/** How many of the chain's elements are drawn before the fold. */
// UX-207: how many attribution bars stay unfolded.
const OVERVIEW_SHOWN = 4;

const PATH_HEAD = 6;
const PATH_TAIL = 3;

/**
 * The critical path, drawn: the chain the report already prints as
 * text, as a sequence of boxes sized by their published share.
 *
 * `share_of_path` is a *published field*, so no width here is computed
 * from a duration - the same rule the overview waterfall follows, and
 * the reason the geometry can be asserted from the payload.
 *
 * `UX-187`'s fold, expandable in place: a 1,202-element chain is not a
 * drawing, and the middle is where a reader stops looking anyway.
 */
export function renderCriticalPath(payload) {
  const detail = payload?.signals?.critical_path_detail;
  if (!Array.isArray(detail) || !detail.length) return null;

  const section = document.createElement("section");
  section.setAttribute("data-section", "critical-path-drawn");
  section.setAttribute("id", "critical-path-drawn");
  const heading = document.createElement("h2");
  heading.textContent = "The chain, drawn";
  section.append(heading);

  const strip = document.createElement("div");
  strip.className = "path-strip";
  strip.setAttribute("data-elements", String(detail.length));

  const folded = detail.length > PATH_HEAD + PATH_TAIL + 1;
  const head = folded ? detail.slice(0, PATH_HEAD) : detail;
  const tail = folded ? detail.slice(detail.length - PATH_TAIL) : [];
  const middle = folded ? detail.slice(PATH_HEAD, detail.length - PATH_TAIL) : [];

  for (const entry of head) strip.append(pathBox(entry));
  if (folded) {
    const hidden = [];
    for (const entry of middle) {
      const box = pathBox(entry);
      box.hidden = true;
      hidden.push(box);
      strip.append(box);
    }
    const more = document.createElement("button");
    more.className = "path-more";
    more.setAttribute("type", "button");
    more.setAttribute("data-folded", String(middle.length));
    more.textContent = `+${middle.length} more`;
    // In place: the fold opens between the two ends rather than
    // scrolling the reader somewhere else.
    more.addEventListener("click", () => {
      for (const box of hidden) box.hidden = false;
      more.hidden = true;
    });
    strip.append(more);
  }
  for (const entry of tail) strip.append(pathBox(entry));
  section.append(strip);
  return section;
}

function pathBox(entry) {
  const box = document.createElement("a");
  box.className = "path-box";
  box.setAttribute("data-element", entry.element_uid ?? "");
  box.setAttribute("data-share", String(entry.share_of_path ?? 0));
  box.setAttribute("data-duration-us", String(entry.duration_us ?? 0));
  // The width is the published share, read not computed. `min-width`
  // in the stylesheet keeps a 0.1% element clickable.
  box.setAttribute("style",
    `flex-grow: ${Math.max(0, Number(entry.share_of_path) || 0) * 1000}`);
  // UX-199's anchors: the drawing points back at the section that
  // explains it.
  box.setAttribute("href", "#signals");
  const name = document.createElement("span");
  name.className = "path-name";
  name.textContent = entry.element_uid ?? "";
  const time = document.createElement("span");
  time.className = "path-time num";
  time.textContent = seconds(entry.duration_us ?? 0);
  box.append(name, time);
  if (entry.element_kind) {
    const badge = document.createElement("span");
    badge.className = "kind";
    badge.textContent = entry.element_kind;
    box.append(badge);
  }
  return box;
}

/**
 * The blast answer as an indented hierarchy: direct consumers, then the
 * closure by depth, each row with its kind badge and measured work.
 *
 * `blast_tree` is the payload `UX-206` assumed `blast/v1` already
 * carried and it did not - the answer had two flat lists and no depth
 * at all, and depth is the whole shape of a tree. It is published now
 * (`bga/blast.py`), so this reads rather than walks a graph.
 */
export function renderBlastTree(payload) {
  const tree = payload?.blast_tree;
  if (!Array.isArray(tree) || !tree.length) return null;

  const section = document.createElement("section");
  section.setAttribute("data-section", "blast-tree");
  section.setAttribute("id", "blast-tree");
  const heading = document.createElement("h2");
  heading.textContent = `What a change to ${payload.target ?? "it"} rebuilds`;
  section.append(heading);

  const list = document.createElement("div");
  list.className = "blast-tree";
  for (const entry of tree) {
    const depth = Number(entry.depth) || 0;
    const row = document.createElement("div");
    row.className = "blast-row";
    row.setAttribute("data-element", entry.element_uid ?? "");
    row.setAttribute("data-depth", String(depth));
    // Indentation is the published depth, not a position in the list.
    row.setAttribute("style", `padding-left: ${depth * 1.4}rem`);
    const name = document.createElement("span");
    name.className = "blast-name";
    name.textContent = entry.element_uid ?? "";
    row.append(name);
    if (entry.element_kind) {
      const badge = document.createElement("span");
      badge.className = "kind";
      badge.setAttribute("data-kind", entry.element_kind);
      badge.textContent = entry.element_kind;
      row.append(badge);
    }
    if (typeof entry.measured_seconds === "number") {
      const cost = document.createElement("span");
      cost.className = "blast-cost num";
      cost.setAttribute("data-raw", String(entry.measured_seconds));
      cost.textContent = seconds(entry.measured_seconds * 1e6);
      row.append(cost);
    }
    list.append(row);
  }
  section.append(list);
  return section;
}


// ------------------------------------------------- UX-207: the decision

/**
 * The first screen, and the only one that is not evidence.
 *
 * **Everything here is read.** The diagnosis, the ratio it came from,
 * the opportunity split and the ranked actions are all fields of the
 * published `headline` block - `UX-207`'s rule, and Direction 7's: a
 * viewer that derives the diagnosis is a second analyzer, free to
 * disagree with the report and the CI gate about the same build.
 *
 * No `headline`, no panel. An older payload renders the page it always
 * did rather than a box explaining what is missing.
 */
export function renderDecision(payload, investigate = null) {
  const headline = payload?.headline;
  if (!headline || !headline.diagnosis) return null;

  const section = document.createElement("section");
  section.className = "decision";
  section.setAttribute("data-section", "decision");
  section.setAttribute("id", "decision");
  section.setAttribute("data-diagnosis", headline.diagnosis);

  const heading = document.createElement("h2");
  heading.textContent = "What to fix first";
  section.append(heading);

  const sentence = document.createElement("p");
  sentence.className = "diagnosis";
  sentence.setAttribute("data-field", "headline.sentence");
  sentence.textContent = headline.sentence ?? "";
  section.append(sentence);

  // The opportunity split, both halves published. Absent stays absent -
  // a zero here would claim a measurement nobody made.
  const split = document.createElement("dl");
  split.className = "pairs opportunity";
  for (const [label, key, kind] of [
    ["Certified headroom", "certified_headroom_us", "duration_us"],
    ["Beyond the chain", "scheduling_gap_us", "duration_us"],
  ]) {
    const value = headline[key];
    if (typeof value !== "number") continue;
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.className = "num";
    detail.setAttribute("data-field", `headline.${key}`);
    detail.setAttribute("data-raw", String(value));
    detail.textContent = kind === "duration_us" ? seconds(value) : String(value);
    split.append(term, detail);
  }
  if (split.children?.length) section.append(split);

  const actions = Array.isArray(headline.top_actions) ? headline.top_actions : [];
  if (actions.length) {
    const list = document.createElement("ol");
    list.className = "actions";
    for (const action of actions) {
      list.append(actionRow(action, investigate));
    }
    section.append(list);
  }
  return section;
}

function actionRow(action, investigate) {
  const row = document.createElement("li");
  row.className = "action";
  row.setAttribute("data-element", action.element_uid ?? "");
  row.setAttribute("data-finding", action.finding_id ?? "");

  const name = document.createElement("code");
  name.textContent = action.element_uid ?? "";
  row.append(name);

  if (typeof action.saving_us === "number") {
    const worth = document.createElement("span");
    worth.className = "worth num";
    worth.setAttribute("data-field", "saving_us");
    worth.setAttribute("data-raw", String(action.saving_us));
    worth.textContent = `saves ${seconds(action.saving_us)}`;
    row.append(worth);
  } else if (typeof action.downstream_count === "number") {
    const reach = document.createElement("span");
    reach.className = "worth num";
    reach.setAttribute("data-field", "downstream_count");
    reach.setAttribute("data-raw", String(action.downstream_count));
    reach.textContent = `${action.downstream_count} downstream`;
    row.append(reach);
  }

  // The reasoning is a section away, not restated here - `finding_id`
  // is a reference for exactly this.
  const why = document.createElement("a");
  why.className = "why";
  why.setAttribute("href", "#findings");
  why.textContent = "why";
  row.append(why);

  // UX-204's transport, where there is a timeline behind it.
  if (investigate) {
    const button = investigate(action);
    if (button) row.append(button);
  }
  return row;
}
