// UX-193: render the schema, not the report.
//
// The load-bearing property is that this file contains no list of the
// report's fields. It asks the schema what a key *is* - a duration, a
// share, a findings array, a table with these columns - and renders
// accordingly. A field added to `analyze/v1` therefore appears here
// with no edit to this file, and a field the schema does not describe
// still renders, generically, rather than vanishing.
//
// The corollary is the constraint Direction 7 wanted: anything the
// viewer should show has to enter the published schema first, where the
// text renderer, CI and every external consumer get it too.

import { handOff, deepLink } from "./perfetto.js";
import { renderBand, renderTrend, renderBlastSearch } from "./views.js";
import { anchor, collapsible, toc, jumpTargets, matches } from "./nav.js";
import { renderQuestions } from "./questions.js";

const QUANTITY = "bga:quantity";
const SEVERITY = "bga:severity";
const COLUMNS = "bga:columns";
const DIRECTION = "bga:direction";

// ---------------------------------------------------------------- format

export function duration(microseconds) {
  if (microseconds === null || microseconds === undefined) return "—";
  const s = microseconds / 1e6;
  if (s < 1) return `${Math.round(microseconds / 1000)} ms`;
  if (s < 90) return `${s.toFixed(1)} s`;
  const m = s / 60;
  if (m < 90) return `${m.toFixed(1)} min`;
  return `${(m / 60).toFixed(1)} h`;
}

export function bytes(value) {
  if (value === null || value === undefined) return "—";
  const units = ["B", "KiB", "MiB", "GiB", "TiB"];
  let n = value, i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i += 1; }
  return `${i === 0 ? n : n.toFixed(1)} ${units[i]}`;
}

export function quantity(value, kind) {
  if (value === null || value === undefined) return "—";
  switch (kind) {
    case "duration_us": return duration(value);
    case "bytes": return bytes(value);
    case "share": return `${(value * 100).toFixed(1)}%`;
    // UX-201: already 0..100. Multiplying again is how a 42% cpu_pct
    // rendered as "4200.0%".
    case "percent": return `${value.toFixed(1)}%`;
    // UX-201: and megabytes are not a byte count - `peak_rss_mb: 512`
    // rendered as "512 B" through the `_mb`-means-bytes guess.
    case "megabytes": return bytes(value * 1024 * 1024);
    case "seconds": return duration(value * 1e6);
    case "ratio": return `${value.toFixed(2)}×`;
    case "count": return String(value);
    default:
      return typeof value === "number"
        ? String(Math.round(value * 1000) / 1000) : String(value);
  }
}

// A key with no hint still wants a sensible unit. This is a *fallback*,
// not a second vocabulary: the schema wins wherever it speaks, and this
// only runs for keys nested below the top level, which the schemas
// deliberately do not describe (see bga/schemas.py's docstring).
export function guessQuantity(key) {
  if (/_us$/.test(key)) return "duration_us";
  if (/_bytes$/.test(key) || /_mb$/.test(key)) return "bytes";
  if (/(share|ratio_pct|_pct)$/.test(key)) return "share";
  if (/_seconds$/.test(key)) return "seconds";
  if (/_count$/.test(key)) return "count";
  return null;
}

export function title(key) {
  return key.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------- render

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value === null || value === undefined) continue;
    if (name === "class") node.className = value;
    else if (name.startsWith("data-")) node.setAttribute(name, value);
    else node[name] = value;
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined) continue;
    node.append(child.nodeType ? child : String(child));
  }
  return node;
}

export function renderFindings(findings) {
  const section = el("section", { "data-section": "findings" },
    el("h2", {}, `Findings (${findings.length})`));
  for (const finding of findings) {
    const severity = String(finding.severity ?? "info").toLowerCase();
    const detail = Array.isArray(finding.detail)
      ? finding.detail : (finding.detail ? [finding.detail] : []);
    section.append(el("article",
      { class: "finding", "data-severity": severity,
        "data-finding-id": finding.id ?? "" },
      el("p", { class: "title" },
        el("span", { class: "badge" }, severity),
        finding.title ?? finding.id ?? ""),
      ...detail.map((line) => el("p", { class: "detail muted" }, line)),
      finding.elements && finding.elements.length
        ? el("p", { class: "muted" },
            el("code", {}, finding.elements.join(", ")))
        : null));
  }
  return section;
}

/**
 * `bga:columns` v2: an entry is a name, or an object saying what the
 * column *is*.
 *
 * UX-201: `renderTable` decided numeric-ness by sampling row values and
 * the sorter guessed from the same sample, so a column of numeric-
 * looking strings sorted as numbers and a column that should never be
 * sorted was sortable anyway. Declared beats sampled.
 */
export function columnSpecs(hint, rows, node) {
  const declared = hint[COLUMNS];
  const present = (key) => rows.some((r) => key in (r ?? {}));
  const itemNode = node?.items;
  const fallback = () => [...new Set(rows.flatMap((r) => Object.keys(r ?? {})))]
    .map((key) => ({ key }));
  const specs = declared && declared.length
    ? declared.map((c) => (typeof c === "string" ? { key: c } : { ...c }))
              .filter((c) => present(c.key))
    : fallback();
  return specs.map((spec) => {
    const child = childNode(itemNode, spec.key);
    const quantityName = spec.quantity ?? hintsOf(child)[QUANTITY]
      ?? guessQuantity(spec.key);
    return {
      ...spec,
      title: spec.title ?? title(spec.key),
      quantity: quantityName,
      // Numeric-ness is declared by carrying a quantity, or observed
      // only when nothing declared anything.
      numeric: quantityName
        ? true : rows.some((r) => typeof r?.[spec.key] === "number"),
      sortable: spec.sortable !== false,
      description: spec.description ?? hintsOf(child).description ?? null,
    };
  });
}

export function renderTable(key, rows, hint = {}, node = undefined) {
  const specs = columnSpecs(hint, rows, node);
  const columns = specs.map((s) => s.key);
  const table = el("table", { "data-table": key });
  const head = el("tr");
  for (const spec of specs) {
    head.append(el("th", {
      class: spec.numeric ? "num" : null,
      scope: "col", "data-column": spec.key,
      "data-sortable": String(spec.sortable),
      title: spec.description ?? null,
    }, spec.title));
  }
  table.append(el("thead", {}, head));
  const body = el("tbody");
  for (const row of rows) {
    const tr = el("tr");
    for (const spec of specs) {
      const column = spec.key;
      const raw = row?.[column];
      const numeric = typeof raw === "number";
      const kind = numeric ? spec.quantity : null;
      tr.append(el("td",
        { class: numeric ? "num" : null,
          "data-column": column,
          "data-raw": raw === undefined || raw === null ? "" : String(raw) },
        Array.isArray(raw) ? raw.join(", ")
          : (raw && typeof raw === "object") ? JSON.stringify(raw)
          : numeric ? quantity(raw, kind) : (raw ?? "—")));
    }
    body.append(tr);
  }
  table.append(body);
  sortable(table, specs);
  return el("section", { "data-section": key },
    el("h2", {}, title(key)), table);
}

function sortable(table, specs = []) {
  const body = table.querySelector("tbody");
  table.querySelectorAll("th").forEach((th, index) => {
    // UX-201: a column the schema declares unsortable stays unsortable,
    // whatever its values happen to look like.
    if (specs[index] && specs[index].sortable === false) return;
    th.addEventListener("click", () => {
      const ascending = th.getAttribute("aria-sort") !== "ascending";
      table.querySelectorAll("th").forEach((other) =>
        other.removeAttribute("aria-sort"));
      th.setAttribute("aria-sort", ascending ? "ascending" : "descending");
      const rows = [...body.querySelectorAll("tr")];
      rows.sort((a, b) => {
        const x = a.children[index]?.dataset.raw ?? "";
        const y = b.children[index]?.dataset.raw ?? "";
        const nx = Number(x), ny = Number(y);
        const numeric = x !== "" && y !== "" && !Number.isNaN(nx) && !Number.isNaN(ny);
        const order = numeric ? nx - ny : String(x).localeCompare(String(y));
        return ascending ? order : -order;
      });
      rows.forEach((row) => body.append(row));
    });
  });
}

export function renderPairs(key, object, hint = {}, node = undefined) {
  const direction = hint[DIRECTION];
  const list = el("dl", { class: "pairs" });
  for (const [name, value] of Object.entries(object)) {
    // UX-201: each member resolved against *its own* schema node, not
    // guessed from its name. `deltas` was hinted at the top level and
    // still name-sniffed every member inside it.
    const child = childNode(node, name);
    const kind = quantityFor(child, name);
    const described = hintsOf(child).description;
    let cell;
    if (value !== null && typeof value === "object") {
      cell = el("details", {}, el("summary", {}, "object"),
                el("pre", {}, JSON.stringify(value, null, 2)));
    } else if (typeof value === "number" && direction) {
      // A signed change, coloured by what the schema says "better" is,
      // without this file knowing which metric it is looking at.
      const better = direction === "lower_is_better" ? value < 0 : value > 0;
      cell = el("span", {
        class: `num delta ${value === 0 ? "" : better ? "better" : "worse"}`,
        "data-raw": String(value),
      }, `${value > 0 ? "+" : ""}${quantity(value, kind)}`);
    } else if (typeof value === "number") {
      cell = el("span", { class: "num", "data-raw": String(value) },
                quantity(value, kind));
    } else {
      cell = el("span", { "data-raw": value === null ? "" : String(value) },
                value === null ? "—" : String(value));
    }
    // UX-201: the schema's own `description` is the popover - the "why
    // does this number matter" answer sourced from the contract, and
    // thence the spec, rather than from prose written beside the
    // renderer where it would drift.
    const term = el("dt", { "data-key": name,
                            title: described ?? null,
                            "data-described": described ? "true" : null },
                    title(name));
    list.append(term, el("dd", {}, cell));
  }
  return el("section", { "data-section": key }, el("h2", {}, title(key)), list);
}

// UX-201: the enum decides, and the prose is a fallback for payloads
// written before `verdict_kind` existed. The viewer used to
// string-match the *sentence* - so rewording "improved" would have
// silently restyled the banner, and a `compare/v1` that changed its
// wording was a rendering change nobody would have called one.
const VERDICT_CLASS = {
  improved: "good",
  regressed: "refused",
  not_comparable: "refused",
  no_significant_change: "",
  within_observed_range: "warn",
};

export function verdictClass(text, kind) {
  if (kind && kind in VERDICT_CLASS) return VERDICT_CLASS[kind];
  const value = String(text).toLowerCase();
  if (value.includes("not comparable") || value.includes("regress")) return "refused";
  if (value.includes("improve")) return "good";
  if (value.includes("no significant")) return "";
  return "warn";
}

export function renderVerdict(payload) {
  // Refusals get visual weight because they are the answer, not an
  // error: `UX-156`/`UX-185`'s incomplete runs and `UX-186`'s
  // cross-host pairs are all "bga will not judge this, and here is
  // why".
  const banner = [];
  if (payload.verdict) {
    banner.push(el("div", {
      class: `verdict ${verdictClass(payload.verdict, payload.verdict_kind)}`,
      "data-verdict": String(payload.verdict),
      "data-verdict-kind": payload.verdict_kind ?? null },
      el("h2", {}, "Verdict"), el("p", {}, String(payload.verdict))));
  }
  const outcome = payload.run_instance?.incomplete_reason
    ?? payload.run_instance?.build_outcome?.incomplete_reason;
  if (outcome) {
    banner.push(el("div", { class: "verdict refused",
                            "data-incomplete": outcome },
      el("h2", {}, `This run is ${outcome}`),
      el("p", { class: "muted" },
        "Durations from a run that did not finish are not measurements.")));
  }
  if (payload.comparability_warning) {
    banner.push(el("div", { class: "verdict warn", "data-warning": "1" },
      el("h2", {}, "Comparability"),
      el("p", {}, String(payload.comparability_warning))));
  }
  return banner;
}

// The generic dispatch. Note there is no `switch (key)` here: what a
// value is rendered as follows from its *shape* and its hints.
export function renderSection(key, value, hint = {}, node = undefined) {
  if (value === null || value === undefined) return null;
  if (hint[SEVERITY] && Array.isArray(value)) {
    return value.length ? renderFindings(value) : null;
  }
  if (Array.isArray(value)) {
    if (!value.length) return null;
    if (value.every((item) => item && typeof item === "object" && !Array.isArray(item))) {
      return renderTable(key, value, hint, node);
    }
    return el("section", { "data-section": key }, el("h2", {}, title(key)),
              el("p", {}, el("code", {}, value.join(", "))));
  }
  if (typeof value === "object") {
    return Object.keys(value).length ? renderPairs(key, value, hint, node) : null;
  }
  return null;   // scalars belong in the summary, below
}

export function renderSummary(payload, hints) {
  const scalars = Object.entries(payload).filter(
    ([, value]) => value === null || typeof value !== "object");
  if (!scalars.length) return null;
  const list = el("dl", { class: "pairs" });
  for (const [key, value] of scalars) {
    const kind = hints[key]?.[QUANTITY] ?? guessQuantity(key);
    list.append(
      el("dt", { "data-key": key }, title(key)),
      el("dd", {}, el("span", {
        class: typeof value === "number" ? "num" : null,
        "data-raw": value === null ? "" : String(value),
      }, typeof value === "number" ? quantity(value, kind)
         : value === null ? "—" : String(value))));
  }
  return el("section", { "data-section": "summary" },
            el("h2", {}, "Run"), list);
}

/**
 * The hints on one schema node, plus the node itself so a renderer can
 * keep walking.
 *
 * UX-201: hints used to be read from the *top level only*, and every
 * nested value fell to `guessQuantity(key)` name-sniffing. The two
 * systems demonstrably disagreed - `peak_rss_mb: 512` rendered as
 * "512 B" and a 0-100 `cpu_pct` as "4200.0%", both measured. The schema
 * is the authority now, at every depth; the guess is what happens when
 * the schema says nothing, and that is a schema gap rather than a
 * feature.
 */
export function hintsOf(node) {
  const hint = {};
  if (!node || typeof node !== "object") return hint;
  for (const name of [QUANTITY, SEVERITY, COLUMNS, DIRECTION]) {
    if (name in node) hint[name] = node[name];
  }
  if (node.description) hint.description = node.description;
  return hint;
}

/** The schema node describing `key` inside `node`, or undefined. */
export function childNode(node, key) {
  if (!node || typeof node !== "object") return undefined;
  if (node.properties && key in node.properties) return node.properties[key];
  if (node.items) return node.items;
  return undefined;
}

/**
 * What a value should be rendered as, schema first.
 *
 * The one place the precedence lives, so "declared beats guessed" is a
 * property of the code rather than of every call site remembering.
 */
export function quantityFor(node, key) {
  const declared = hintsOf(node)[QUANTITY];
  if (declared) return declared;
  const guessed = guessQuantity(key);
  if (guessed && typeof console !== "undefined" && globalThis.BGA_STRICT_HINTS) {
    // Dev-mode complaint: an undeclared key the renderer had to guess
    // about is a gap in the published schema, and the schema is what
    // every other consumer reads.
    console.warn(`bga: ${key} has no bga:quantity; guessed ${guessed}`);
  }
  return guessed;
}

export function render(payload, schema, root) {
  const hints = {};
  for (const [key, sub] of Object.entries(schema?.properties ?? {})) {
    const hint = hintsOf(sub);
    if (Object.keys(hint).length) hints[key] = hint;
  }
  const nodes = schema?.properties ?? {};

  root.replaceChildren();
  for (const banner of renderVerdict(payload)) root.append(banner);
  const summary = renderSummary(payload, hints);
  if (summary) root.append(summary);
  for (const [key, value] of Object.entries(payload)) {
    if (key === "schema") continue;
    const section = renderSection(key, value, hints[key] ?? {}, nodes[key]);
    if (section) root.append(section);
  }
  root.setAttribute("aria-busy", "false");
  return root;
}


// UX-199: a served page can ask the server; an export cannot. One
// predicate, so the two modes cannot disagree about which they are.
export function served() {
  return /^https?:$/.test(location.protocol);
}

function safeStorage() {
  try {
    return window.localStorage;
  } catch (error) {
    // Blocked site data, a private window, a thumbnail renderer.
    return null;
  }
}

/** Type-ahead over section names and element uids. Scrolls; never filters. */
export function wireJumpBox(nav, root, payload) {
  const targets = jumpTargets(root, payload);
  const box = document.createElement("input");
  box.setAttribute("type", "search");
  box.setAttribute("id", "jump");
  box.setAttribute("placeholder", "Jump to…");
  box.setAttribute("aria-label", "Jump to a section or element");
  const list = document.createElement("ul");
  list.className = "jump-hits";

  const go = (target) => {
    const node = target.kind === "section"
      ? document.getElementById(target.key)
      : root.querySelector(`[data-element="${CSS?.escape?.(target.key)
          ?? target.key}"]`);
    if (!node) return;
    node.scrollIntoView?.({ behavior: "smooth", block: "start" });
    node.setAttribute("data-jumped", "true");
    setTimeout(() => node.removeAttribute("data-jumped"), 1600);
  };

  box.addEventListener("input", () => {
    const hits = matches(targets, box.value);
    list.replaceChildren();
    for (const hit of hits) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.textContent = hit.text;
      button.setAttribute("data-jump", hit.key);
      button.addEventListener("click", () => { go(hit); box.value = ""; list.replaceChildren(); });
      item.append(button);
      list.append(item);
    }
  });
  box.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    const [first] = matches(targets, box.value, 1);
    if (first) { go(first); box.value = ""; list.replaceChildren(); }
  });

  nav.append(box, list);
  return { targets, box, list };
}

// ------------------------------------------------------------------ boot


export function wireTheHandoff() {
  const actions = document.getElementById("actions");
  const button = document.getElementById("perfetto");
  const status = document.getElementById("handoff");
  const fallback = document.getElementById("perfetto-link");
  if (!actions || !button) return;
  actions.hidden = false;

  // UX-198: the deep link only works when something is serving the
  // trace over http for Perfetto to fetch. An export is a `file://`
  // document with the trace inlined as a data: URL, and nothing can
  // fetch that cross-origin - so the link is shown in served mode and
  // stays hidden in an export, rather than shipping a link that 404s
  // for exactly the readers least able to debug it.
  const url = traceUrl();
  const absolute = new URL(url, location.href);
  const served = absolute.protocol === "http:" || absolute.protocol === "https:";
  if (fallback && served) {
    fallback.href = deepLink(absolute.href);
    fallback.parentElement.hidden = false;
  }

  button.addEventListener("click", async () => {
    status.textContent = "opening ui.perfetto.dev — sent tab to tab, not uploaded…";
    // `handOff` opens the tab before its first `await` (UX-198), so
    // this must call it without one - no `await` may come first in
    // this handler, or the click's activation is gone before the open.
    try {
      const { bytes } = await handOff(url);
      status.textContent = `sent ${(bytes / 1024).toFixed(1)} KiB`;
    } catch (error) {
      status.textContent = String(error.message ?? error);
    }
  });
}

// UX-195: inline first, fetch second - one code path, so the exported
// file and the served page cannot render differently. `bga view
// --export` writes the same payloads into `<script
// type="application/json">` blocks; everything below is identical
// either way, which is the point.
export function inlined(name) {
  const node = document.getElementById(`bga-${name}`);
  if (!node) return null;
  try {
    return JSON.parse(node.textContent);
  } catch (error) {
    return null;
  }
}

export async function load(name, fallback = null) {
  const here = inlined(name);
  if (here !== null) return here;
  try {
    const response = await fetch(`${name}.json`);
    if (!response.ok) throw new Error(String(response.status));
    return await response.json();
  } catch (error) {
    if (fallback !== null) return fallback;
    throw error;
  }
}

// The trace is a data: URL in an export and a served path otherwise.
// `handOff` fetches whichever it is given; `fetch` handles data: URLs,
// so the Perfetto button works from `file://` with no server at all.
export function traceUrl() {
  const node = document.getElementById("bga-trace");
  return node ? node.textContent.trim() : "timeline.json.gz";
}

async function boot() {
  const root = document.getElementById("report");
  try {
    const [payload, schemas, run] = await Promise.all([
      load("report"),
      load("schemas"),
      load("run", {}),
    ]);
    document.getElementById("run-name").textContent = run.name ?? "bga";
    document.getElementById("run-path").textContent = run.run ?? "";
    document.title = `bga — ${run.name ?? "report"}`;
    render(payload, schemas[payload.schema], root);
    // UX-196: the three views, each only when its payload is there.
    //
    // UX-203: from the *compare* document, which is what `renderBand`
    // has always needed - it reads `baseline_band` and
    // `candidate.total_duration_us`, neither of which an analyze
    // document has. Handing it `payload` meant it returned null every
    // time, so the band had never rendered for any user. `bga view`
    // now serves the comparison against the run before this one.
    const comparison = await load("compare", null).catch(() => null);
    const band = comparison && renderBand(comparison);
    if (band) root.prepend(band);
    const store = await load("store", null).catch(() => null);
    const trend = store && renderTrend(store);
    if (trend) root.append(trend);
    // UX-199: the blast box is a *transport* - it asks the server. An
    // export is a `file://` document with no server, so the box could
    // never answer there and shipped as a control that always errors.
    // Hidden in that mode, with the command to run instead.
    if (served()) {
      root.append(renderBlastSearch(async (target) => {
        const response = await fetch(
          `blast.json?target=${encodeURIComponent(target)}`);
        const answer = await response.json();
        if (!response.ok) throw new Error(answer.error ?? response.status);
        return answer;
      }));
    } else {
      const note = el("section", { "data-section": "blast-offline" },
        el("h2", {}, "Blast radius"),
        el("p", { class: "muted" },
          "Not available in an exported report - the search asks the "
          + "server, and there is not one here. Run "),
        el("p", {}, el("code", {}, "bga blast <target> <run>")));
      root.append(note);
    }

    // UX-199: the export used to strip the link to the questions page
    // and leave nothing behind it - functionality lost rather than
    // moved. They are inlined here instead, from the same module
    // `sql.html` renders, so the two cannot drift.
    if (!served()) root.append(renderQuestions(el));
    // UX-194: only when there is a timeline behind it. A dead button is
    // worse than no button - the run that has no Plane 2 log is exactly
    // the run whose user would spend a minute wondering what broke.
    if (run.has_timeline) wireTheHandoff();

    // UX-199: navigation, last, over whatever was rendered. Nothing
    // above changes; a reader who ignores all of it sees the same
    // report in the same order.
    anchor(root);
    const controls = collapsible(root, {
      document, storage: served() ? safeStorage() : null });
    const contents = toc(root, { document, controls });
    if (contents) {
      wireJumpBox(contents, root, payload);
      document.body.insertBefore(contents, document.body.firstChild);
      document.body.setAttribute("data-has-toc", "true");
    }
  } catch (error) {
    root.replaceChildren(el("div", { class: "verdict refused" },
      el("h2", {}, "Could not load this run"),
      el("p", {}, String(error))));
  }
}

if (typeof document !== "undefined" && document.getElementById("report")) {
  boot();
}
