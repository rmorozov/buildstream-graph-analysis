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

export function renderTable(key, rows, hint = {}) {
  const columns = hint[COLUMNS] && hint[COLUMNS].length
    ? hint[COLUMNS].filter((c) => rows.some((r) => c in (r ?? {})))
    : [...new Set(rows.flatMap((r) => Object.keys(r ?? {})))];
  const table = el("table", { "data-table": key });
  const head = el("tr");
  for (const column of columns) {
    const numeric = rows.some((r) => typeof r?.[column] === "number");
    head.append(el("th", { class: numeric ? "num" : null,
                          scope: "col", "data-column": column }, title(column)));
  }
  table.append(el("thead", {}, head));
  const body = el("tbody");
  for (const row of rows) {
    const tr = el("tr");
    for (const column of columns) {
      const raw = row?.[column];
      const numeric = typeof raw === "number";
      const kind = numeric ? guessQuantity(column) : null;
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
  sortable(table);
  return el("section", { "data-section": key },
    el("h2", {}, title(key)), table);
}

function sortable(table) {
  const body = table.querySelector("tbody");
  table.querySelectorAll("th").forEach((th, index) => {
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

export function renderPairs(key, object, hint = {}) {
  const direction = hint[DIRECTION];
  const list = el("dl", { class: "pairs" });
  for (const [name, value] of Object.entries(object)) {
    let node;
    if (value !== null && typeof value === "object") {
      node = el("details", {}, el("summary", {}, "object"),
                el("pre", {}, JSON.stringify(value, null, 2)));
    } else if (typeof value === "number" && direction) {
      // A signed change, coloured by what the schema says "better" is,
      // without this file knowing which metric it is looking at.
      const better = direction === "lower_is_better" ? value < 0 : value > 0;
      node = el("span", {
        class: `num delta ${value === 0 ? "" : better ? "better" : "worse"}`,
        "data-raw": String(value),
      }, `${value > 0 ? "+" : ""}${quantity(value, guessQuantity(name))}`);
    } else if (typeof value === "number") {
      node = el("span", { class: "num", "data-raw": String(value) },
                quantity(value, guessQuantity(name)));
    } else {
      node = el("span", { "data-raw": value === null ? "" : String(value) },
                value === null ? "—" : String(value));
    }
    list.append(el("dt", { "data-key": name }, title(name)), el("dd", {}, node));
  }
  return el("section", { "data-section": key }, el("h2", {}, title(key)), list);
}

function verdictClass(text) {
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
    banner.push(el("div", { class: `verdict ${verdictClass(payload.verdict)}`,
                            "data-verdict": String(payload.verdict) },
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
export function renderSection(key, value, hint = {}) {
  if (value === null || value === undefined) return null;
  if (hint[SEVERITY] && Array.isArray(value)) {
    return value.length ? renderFindings(value) : null;
  }
  if (Array.isArray(value)) {
    if (!value.length) return null;
    if (value.every((item) => item && typeof item === "object" && !Array.isArray(item))) {
      return renderTable(key, value, hint);
    }
    return el("section", { "data-section": key }, el("h2", {}, title(key)),
              el("p", {}, el("code", {}, value.join(", "))));
  }
  if (typeof value === "object") {
    return Object.keys(value).length ? renderPairs(key, value, hint) : null;
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

export function render(payload, schema, root) {
  const hints = {};
  for (const [key, sub] of Object.entries(schema?.properties ?? {})) {
    const hint = {};
    for (const name of [QUANTITY, SEVERITY, COLUMNS, DIRECTION]) {
      if (name in sub) hint[name] = sub[name];
    }
    if (Object.keys(hint).length) hints[key] = hint;
  }

  root.replaceChildren();
  for (const banner of renderVerdict(payload)) root.append(banner);
  const summary = renderSummary(payload, hints);
  if (summary) root.append(summary);
  for (const [key, value] of Object.entries(payload)) {
    if (key === "schema") continue;
    const section = renderSection(key, value, hints[key] ?? {});
    if (section) root.append(section);
  }
  root.setAttribute("aria-busy", "false");
  return root;
}

// ------------------------------------------------------------------ boot

async function boot() {
  const root = document.getElementById("report");
  try {
    const [payload, schemas, run] = await Promise.all([
      fetch("report.json").then((r) => r.json()),
      fetch("schemas.json").then((r) => r.json()),
      fetch("run.json").then((r) => r.json()).catch(() => ({})),
    ]);
    document.getElementById("run-name").textContent = run.name ?? "bga";
    document.getElementById("run-path").textContent = run.run ?? "";
    document.title = `bga — ${run.name ?? "report"}`;
    render(payload, schemas[payload.schema], root);
  } catch (error) {
    root.replaceChildren(el("div", { class: "verdict refused" },
      el("h2", {}, "Could not load this run"),
      el("p", {}, String(error))));
  }
}

if (typeof document !== "undefined" && document.getElementById("report")) {
  boot();
}
