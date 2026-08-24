// UX-266: this was an inline `<script type="module">` in
// `sql.html`. The server sends `default-src 'self'`, which refuses
// inline script, so the page rendered **nothing**: `main` had zero
// children and the questions list never existed. External, like
// `index.html`'s has always been.
import { renderQuestions } from "./questions.js";

// The same `make` shape `app.js` uses, so one renderer serves both.
function make(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    node.setAttribute(name, value);
  }
  for (const child of children) {
    node.append(child?.nodeType ? child : String(child));
  }
  return node;
}

const section = renderQuestions(make);
// The page has its own heading; the section's would be a second one.
section.querySelector("h2")?.remove();
document.getElementById("questions").append(section);
