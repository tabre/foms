/* Browser-side timestamp localization: server renders in the configured
   default timezone; the browser re-renders in the user's own timezone. */
function localizeTimestamps(root) {
  root.querySelectorAll("time.local").forEach((el) => {
    const d = new Date(el.getAttribute("datetime"));
    if (!Number.isNaN(d.getTime())) el.textContent = d.toLocaleString();
  });
}
document.addEventListener("DOMContentLoaded", () => localizeTimestamps(document));

/* HTMX 4 fires colon-separated events and passes everything through event.detail;
   the pre-4 names are kept as a fallback. */
function swapTarget(e) {
  return e.detail?.ctx?.hx?.target ?? e.detail?.ctx?.target ?? e.target ?? document;
}
document.addEventListener("htmx:after:swap", (e) => localizeTimestamps(swapTarget(e)));
document.addEventListener("htmx:afterSwap", (e) => localizeTimestamps(swapTarget(e)));

/* HTMX verbs carry the CSRF token on every state-changing request. */
function addCsrfHeader(e) {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (!meta) return;
  const headers = e.detail?.ctx?.request?.headers ?? e.detail?.headers ?? e.headers;
  if (headers) headers["X-CSRF-Token"] = meta.content;
}
document.addEventListener("htmx:config:request", addCsrfHeader);
document.addEventListener("htmx:configRequest", addCsrfHeader);
