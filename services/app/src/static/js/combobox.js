/* Combobox behavior: open-on-focus, debounced server filtering, matched-character
   highlighting, state pills, keyboard selection, valid-value-only, dependent clearing,
   prefill, and assistive-technology announcements. */
const DEBOUNCE_MS = 150;

function initCombobox(input) {
  const wrap = input.closest(".combobox");
  if (!wrap || wrap.dataset.ready) return;
  wrap.dataset.ready = "1";

  let hidden = wrap.querySelector("input[type=hidden]");
  if (!hidden) {
    hidden = document.createElement("input");
    hidden.type = "hidden";
    hidden.name = input.dataset.name;
    wrap.appendChild(hidden);
  }
  const list = wrap.querySelector(".combo-list");
  const status = document.createElement("div");
  status.className = "sr-only";
  status.setAttribute("role", "status");
  wrap.appendChild(status);

  const name = input.dataset.name;
  const url = wrap.dataset.url || input.dataset.url || "";
  const staticItems = parseStatic(wrap) || parseStatic(input);

  let timer = null;
  let active = -1;
  let selected = false;
  let items = [];
  let query = "";
  let pageSize = 50;
  let lastValid = { value: hidden.value || input.dataset.value || "", label: input.value || "" };
  let pending = false;

  hidden.value = input.dataset.value || "";
  list.hidden = true;

  wrap.combobox = { record };

  function parseStatic(el) {
    if (!el.dataset.static) return null;
    try { return JSON.parse(el.dataset.static); } catch (e) { return null; }
  }

  function record(value, label) {
    hidden.value = value;
    input.value = label;
    input.dataset.value = value;
    lastValid = { value, label };
    selected = true;
  }

  function open() {
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
  }

  function close() {
    list.hidden = true;
    input.setAttribute("aria-expanded", "false");
    active = -1;
    input.removeAttribute("aria-activedescendant");
  }

  /* Params are resolved live: any param that names another combobox field takes
     that field's current value, so dependents filter by what was just selected. */
  function buildUrl(q) {
    const base = new URL(url, window.location.origin);
    const params = new URLSearchParams(base.search);
    for (const [key, value] of new URLSearchParams(wrap.dataset.params || "")) {
      if (!params.has(key)) params.set(key, value);
    }
    for (const key of [...params.keys()]) {
      const source = document.querySelector(`.combobox input[data-name="${key}"]`);
      if (source) params.set(key, valueOf(source.closest(".combobox")));
    }
    params.set("q", q);
    return base.pathname + "?" + params.toString();
  }

  function valueOf(targetWrap) {
    const h = targetWrap.querySelector("input[type=hidden]");
    return h ? h.value : "";
  }

  function announce(text) {
    status.textContent = text;
  }

  function markLabel(label) {
    const span = document.createElement("span");
    span.className = "label";
    if (!query) { span.textContent = label; return span; }
    const at = label.toLowerCase().indexOf(query.toLowerCase());
    if (at < 0) { span.textContent = label; return span; }
    span.textContent = label.slice(0, at);
    const mark = document.createElement("mark");
    mark.textContent = label.slice(at, at + query.length);
    span.appendChild(mark);
    span.appendChild(document.createTextNode(label.slice(at + query.length)));
    return span;
  }

  function setActive(i) {
    const opts = [...list.querySelectorAll("li[role=option]")];
    if (!opts.length) return;
    active = Math.max(0, Math.min(i, opts.length - 1));
    opts.forEach((li, n) => li.setAttribute("aria-selected", n === active ? "true" : "false"));
    input.setAttribute("aria-activedescendant", opts[active].id);
    opts[active].scrollIntoView({ block: "nearest" });
  }

  function render(payload) {
    const rows = payload.items || [];
    pageSize = payload.page_size || pageSize;
    items = rows;
    list.innerHTML = "";
    rows.forEach((item, i) => {
      const li = document.createElement("li");
      li.id = `opt-${name}-${i}`;
      li.dataset.value = item.value;
      li.dataset.index = i;
      li.setAttribute("role", "option");
      li.setAttribute("aria-selected", "false");
      li.appendChild(markLabel(item.label));

      const detail = document.createElement("span");
      detail.className = "detail";
      if (item.amount && (item.state === "low" || item.state === "empty")) {
        const pill = document.createElement("span");
        pill.className = "pill pill-warning";
        pill.textContent = `${item.amount} · ${item.state === "low" ? "low" : "out"}`;
        detail.appendChild(pill);
      } else if (item.amount) {
        detail.textContent = item.amount;
      }
      if (item.detail) {
        const extra = document.createElement("span");
        if (detail.childNodes.length) extra.textContent = " · ";
        extra.textContent += item.detail;
        detail.appendChild(extra);
      }
      if (detail.childNodes.length) li.appendChild(detail);

      li.addEventListener("click", () => select(item));
      list.appendChild(li);
    });
    if (payload.truncated) {
      const li = document.createElement("li");
      li.className = "truncated";
      li.textContent = `Showing first ${pageSize}. Keep typing to narrow the list`;
      list.appendChild(li);
    }
    if (!rows.length) {
      const li = document.createElement("li");
      li.className = "truncated";
      li.textContent = "No matches";
      list.appendChild(li);
    }
    announce(`${rows.length} result${rows.length === 1 ? "" : "s"}`);
    if (rows.length) setActive(0);
  }

  function fetchOptions(q) {
    query = q;
    if (staticItems) {
      render({ items: staticItems.map((v) => ({ value: v, label: v, state: "normal" })), truncated: false });
      return;
    }
    fetch(buildUrl(q), { headers: { "X-Requested-With": "fetch" } })
      .then((r) => r.json())
      .then(render)
      .catch(() => render({ items: [], truncated: false }));
  }

  function select(item) {
    record(item.value, item.label);
    pending = false;
    close();
    announce(`Selected ${item.label}`);
    if (item.prefill) applyPrefill(item.prefill);
    if (wrap.dataset.swap) swapFieldSet(item.value);
    clearDependents();
  }

  function applyTo(targetWrap, value, label) {
    const h = targetWrap.querySelector("input[type=hidden]");
    const targetInput = targetWrap.querySelector(".combo-input");
    if (h) h.value = value || "";
    if (targetInput) {
      targetInput.value = label || value || "";
      targetInput.dataset.value = value || "";
    }
    if (targetWrap.combobox) targetWrap.combobox.record(value || "", label || value || "");
  }

  function applyPrefill(prefill) {
    for (const entry of prefill) {
      const target = document.querySelector(`.combobox input[data-name="${entry.name}"]`);
      if (target) applyTo(target.closest(".combobox"), entry.value, entry.label);
    }
  }

  function clearDependents() {
    document.querySelectorAll(`.combobox[data-depends*="${name}"]`).forEach((dep) => {
      if (dep === wrap) return;
      applyTo(dep, "", "");
    });
  }

  function swapFieldSet(value) {
    const productForm = document.getElementById("product-fields");
    const filamentForm = document.getElementById("filament-fields");
    if (productForm && filamentForm) {
      productForm.classList.toggle("hidden", value !== "Premade product");
      filamentForm.classList.toggle("hidden", value !== "Filament");
    }
  }

  /* Clicking a row must not move focus out of the input. Without this, blur fires
     before click, the typed value is reverted, and the selection is lost. */
  list.addEventListener("pointerdown", (e) => {
    if (e.target.closest("li[role=option]")) pending = true;
  });
  list.addEventListener("mousedown", (e) => e.preventDefault());

  input.addEventListener("input", () => {
    selected = false;
    pending = false;
    open();
    clearTimeout(timer);
    timer = setTimeout(() => fetchOptions(input.value), DEBOUNCE_MS);
  });

  /* Focus or click opens the list with the first page of options. */
  input.addEventListener("focus", () => {
    open();
    fetchOptions("");
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      open();
      setActive(active + (e.key === "ArrowDown" ? 1 : -1));
    } else if (e.key === "Enter") {
      if (!list.hidden && active >= 0 && items[active]) {
        e.preventDefault();
        select(items[active]);
      }
    } else if (e.key === "Escape") {
      close();
    } else if (e.key === "Tab") {
      close();
    }
  });

  /* Valid values only: free text that was never chosen through the list reverts to
     the previous valid selection (or empty). */
  input.addEventListener("blur", () => {
    if (!selected && !pending) {
      hidden.value = lastValid.value;
      input.value = lastValid.label;
    }
    pending = false;
    close();
  });

  if (input.dataset.value) {
    selected = true;
    if (staticItems) input.value = input.dataset.value;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".combo-input").forEach(initCombobox);
});
document.addEventListener("htmx:afterSwap", (e) => {
  e.target.querySelectorAll(".combo-input").forEach(initCombobox);
});
/* HTMX 4 fires colon-separated event names; without this, comboboxes in
   swapped-in fragments (e.g. the product edit form) never initialize. */
document.addEventListener("htmx:after:swap", (e) => {
  const root = e.detail?.ctx?.target ?? e.target;
  root.querySelectorAll?.(".combo-input").forEach(initCombobox);
});
