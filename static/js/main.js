// SkillzTrack front end. Plain JavaScript, no framework, no CDN. Every page also works without it
// (forms post normally, numbers are real text); this file only adds speed, feedback and interactivity.
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var csrf = ($('meta[name="csrf-token"]') || {}).content || "";
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SVG = "http://www.w3.org/2000/svg";

  function el(tag, attrs, parent) {
    var n = document.createElementNS(SVG, tag);
    for (var k in attrs) if (attrs.hasOwnProperty(k)) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  // ------------------------------------------------------------------ theme
  $$("[data-theme-toggle]").forEach(function (b) {
    b.addEventListener("click", function () {
      var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("st-theme", next); } catch (e) { /* ignore */ }
    });
  });

  // ------------------------------------------------------- scroll state, drawer, menus
  var bars = $$(".topbar, .site-nav");
  function onScroll() { bars.forEach(function (b) { b.classList.toggle("is-scrolled", window.scrollY > 6); }); }
  window.addEventListener("scroll", onScroll, { passive: true }); onScroll();

  var body = document.body, opener = $("[data-drawer-open]"), scrim = $(".scrim");
  function drawer(open) {
    body.classList.toggle("drawer-open", open);
    if (scrim) scrim.hidden = !open;
    if (opener) opener.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) { var first = $("#sidebar a"); if (first) first.focus(); } else if (opener && document.activeElement && document.activeElement.closest("#sidebar")) opener.focus();
  }
  if (opener) opener.addEventListener("click", function () { drawer(true); });
  $$("[data-drawer-close]").forEach(function (n) { n.addEventListener("click", function () { drawer(false); }); });
  $$("#sidebar a").forEach(function (a) { a.addEventListener("click", function () { drawer(false); }); });

  var siteMenu = $("[data-site-menu]"), siteLinks = $("#siteLinks");
  if (siteMenu && siteLinks) {
    siteMenu.addEventListener("click", function () {
      var open = siteLinks.classList.toggle("open");
      siteMenu.setAttribute("aria-expanded", open ? "true" : "false");
    });
    $$("a", siteLinks).forEach(function (a) { a.addEventListener("click", function () { siteLinks.classList.remove("open"); siteMenu.setAttribute("aria-expanded", "false"); }); });
  }
  document.addEventListener("click", function (e) { $$("details[data-menu][open]").forEach(function (d) { if (!d.contains(e.target)) d.removeAttribute("open"); }); });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    $$("details[data-menu][open]").forEach(function (d) { d.removeAttribute("open"); d.querySelector("summary").focus(); });
    if (body.classList.contains("drawer-open")) drawer(false);
    if (siteLinks && siteLinks.classList.contains("open")) { siteLinks.classList.remove("open"); siteMenu.setAttribute("aria-expanded", "false"); }
  });

  // ------------------------------------------------------------------ toasts
  function toastStack() {
    var s = $(".toasts");
    if (!s) { s = document.createElement("div"); s.className = "toasts"; s.setAttribute("role", "status"); s.setAttribute("aria-live", "polite"); body.appendChild(s); }
    return s;
  }
  function toast(message, category) {
    category = category || "info";
    var icon = { success: "check-circle", info: "info", warning: "alert", danger: "alert" }[category] || "info";
    var t = document.createElement("div");
    t.className = "toast toast-" + category; t.setAttribute("data-toast", "");
    t.innerHTML = '<span class="toast-icon"><svg class="i" aria-hidden="true"><use href="#i-' + icon + '"/></svg></span><p>' + esc(message) +
      '</p><button type="button" class="toast-close" data-toast-close aria-label="Dismiss message"><svg class="i" aria-hidden="true"><use href="#i-x"/></svg></button>';
    toastStack().appendChild(t);
    wireToast(t);
  }
  function wireToast(t) {
    var close = $("[data-toast-close]", t);
    function remove() { if (t.parentNode) t.parentNode.removeChild(t); }
    if (close) close.addEventListener("click", remove);
    t.addEventListener("animationend", function (ev) { if (ev.animationName === "toastOut") remove(); });
  }
  $$("[data-toast]").forEach(wireToast);
  window.SkillzTrack = { toast: toast };

  // ----------------------------------------------- scroll reveal and number count-up
  var reveals = $$("[data-reveal]");
  if ("IntersectionObserver" in window && !reduceMotion) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("is-visible"); io.unobserve(e.target); } });
    }, { threshold: 0.1, rootMargin: "0px 0px -40px 0px" });
    reveals.forEach(function (n, i) { n.style.setProperty("--d", (i % 6) * 60 + "ms"); io.observe(n); });
  } else reveals.forEach(function (n) { n.classList.add("is-visible"); });

  $$("[data-count]").forEach(function (n) {
    var target = parseFloat(n.getAttribute("data-count")); if (isNaN(target) || reduceMotion) return;
    var t0 = null, dur = 900;
    function tick(t) { if (t0 === null) t0 = t; var p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3); n.textContent = Math.round(target * e); if (p < 1) requestAnimationFrame(tick); }
    n.textContent = "0"; requestAnimationFrame(tick);
  });

  // greeting that follows the visitor's own clock
  $$("[data-greeting]").forEach(function (n) {
    var h = new Date().getHours(), g = h < 5 ? "Working late" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
    n.textContent = g + (n.getAttribute("data-name") ? ", " + n.getAttribute("data-name") : "");
  });

  // ------------------------------------------------------------ collapsible panels
  function setCollapse(panel, open) {
    panel.classList.toggle("open", open);
    $$('[data-collapse-toggle="#' + panel.id + '"]').forEach(function (b) { b.setAttribute("aria-expanded", open ? "true" : "false"); });
  }
  $$("[data-collapse-toggle]").forEach(function (b) {
    b.addEventListener("click", function () { var p = $(b.getAttribute("data-collapse-toggle")); if (p) setCollapse(p, !p.classList.contains("open")); });
  });
  function openFromHash() {
    var id = location.hash.slice(1), p = id && document.getElementById(id);
    if (p && p.classList.contains("collapse")) { setCollapse(p, true); p.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" }); }
  }
  window.addEventListener("hashchange", openFromHash); openFromHash();
  $$('a[href^="#"]').forEach(function (a) { a.addEventListener("click", function () { setTimeout(openFromHash, 0); }); });

  // ------------------------------------------- confirmation dialog and loading states
  var dialog = $("#confirmDialog");
  function ask(message, ok) {
    if (!dialog || typeof dialog.showModal !== "function") { if (window.confirm(message)) ok(); return; }
    $("#confirmText").textContent = message;
    dialog.returnValue = ""; dialog.showModal();
    dialog.addEventListener("close", function once() { dialog.removeEventListener("close", once); if (dialog.returnValue === "ok") ok(); });
  }
  $$("form[data-confirm], form[data-confirm-submit]").forEach(function (f) {
    f.addEventListener("submit", function (ev) {
      if (f.dataset.confirmed) return;
      ev.preventDefault();
      ask(f.getAttribute("data-confirm") || f.getAttribute("data-confirm-submit"), function () { f.dataset.confirmed = "1"; if (f.requestSubmit) f.requestSubmit(); else f.submit(); });
    });
  });

  var progress = $("#navProgress");
  function startProgress() { if (progress) progress.classList.add("on"); }
  $$("form").forEach(function (f) {
    if (f.hasAttribute("data-item-form")) return;
    f.addEventListener("submit", function (ev) {
      setTimeout(function () {
        if (ev.defaultPrevented) return;
        var btn = $('button[type="submit"], button:not([type])', f);
        if (btn && f.method === "post") { if (btn.dataset.loadingText) btn.textContent = btn.dataset.loadingText; btn.classList.add("is-loading"); }
        startProgress();
      }, 0);
    });
  });
  $$('a[href^="/"]:not([target])').forEach(function (a) {
    a.addEventListener("click", function (ev) {
      var href = a.getAttribute("href");
      if (!ev.defaultPrevented && !ev.metaKey && !ev.ctrlKey && !ev.shiftKey && href.indexOf("#") < 0) startProgress();
    });
  });
  window.addEventListener("pageshow", function (e) {
    if (!e.persisted) return;
    if (progress) progress.classList.remove("on");
    $$(".is-loading").forEach(function (b) { b.classList.remove("is-loading"); });
  });

  // -------------------------------------------------------------- generic filters
  $$("[data-filter-root]").forEach(function (root) {
    var items = $$("[data-filter-item]", root), groups = $$("[data-filter-group]", root), search = $("[data-filter-search]", root);
    var empty = $("[data-filter-empty]", root), counter = $("[data-filter-count]", root), state = {};
    $$("[data-filter-key]", root).forEach(function (seg) {
      var key = seg.getAttribute("data-filter-key"); state[key] = "all";
      seg.addEventListener("click", function (e) {
        var b = e.target.closest("button[data-value]"); if (!b) return;
        $$("button", seg).forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
        state[key] = b.getAttribute("data-value"); apply();
      });
    });
    function apply() {
      var q = search ? search.value.trim().toLowerCase() : "", shown = 0;
      items.forEach(function (it) {
        var ok = !q || (it.getAttribute("data-text") || "").indexOf(q) > -1;
        for (var k in state) if (ok && state[k] !== "all" && it.getAttribute("data-" + k) !== state[k]) ok = false;
        it.hidden = !ok; if (ok) shown++;
      });
      groups.forEach(function (g) { g.hidden = !$("[data-filter-item]:not([hidden])", g); });
      if (empty) empty.hidden = shown > 0;
      if (counter) counter.textContent = shown + (shown === 1 ? " result" : " results");
    }
    if (search) search.addEventListener("input", apply);
    apply();
  });

  // ------------------------------------------------- password reveal, strength, validation
  $$("[data-reveal-pw]").forEach(function (b) {
    b.addEventListener("click", function () {
      var input = document.getElementById(b.getAttribute("data-reveal-pw")); if (!input) return;
      var show = input.type === "password"; input.type = show ? "text" : "password";
      b.setAttribute("aria-label", show ? "Hide password" : "Show password"); b.setAttribute("aria-pressed", show ? "true" : "false");
      b.innerHTML = '<svg class="i" aria-hidden="true"><use href="#i-' + (show ? "eye-off" : "eye") + '"/></svg>';
    });
  });
  $$("[data-meter-for]").forEach(function (m) {
    var input = document.getElementById(m.getAttribute("data-meter-for")), label = $("[data-meter-label]", m.parentNode);
    if (!input) return;
    input.addEventListener("input", function () {
      var v = input.value, s = 0;
      if (v.length >= 8) s++; if (v.length >= 12) s++; if (/[a-z]/.test(v) && /[A-Z]/.test(v)) s++; if (/\d/.test(v) && /[^A-Za-z0-9]/.test(v)) s++;
      if (/^\d+$/.test(v)) s = Math.min(s, 1);
      if (!v) s = 0;
      m.setAttribute("data-score", s);
      if (label) label.textContent = v ? ["Too weak", "Weak", "Fair", "Good", "Strong"][s] : "";
    });
  });

  var RULES = {
    required: function (v) { return v.trim() ? "" : "This field is required."; },
    email: function (v) { return !v || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v) ? "" : "Enter a valid email address."; },
    username: function (v) { return !v || /^[A-Za-z0-9_.-]{3,30}$/.test(v) ? "" : "Use 3-30 letters, numbers, dots, dashes or underscores."; },
    password: function (v, f) {
      if (!v) return "";
      if (v.length < 8) return "Use at least 8 characters.";
      if (/^\d+$/.test(v)) return "Password cannot be only numbers.";
      var u = f.querySelector("#username"); if (u && u.value && u.value.toLowerCase() === v.toLowerCase()) return "Password cannot be the same as your username.";
      return "";
    },
    match: function (v, f, arg) { var o = f.querySelector(arg); return !v || !o || o.value === v ? "" : "The two passwords do not match."; },
    hours: function (v) { var n = parseInt(v, 10); return !v || (n >= 2 && n <= 40) ? "" : "Choose between 2 and 40 hours."; }
  };
  function fieldError(input, msg) {
    var holder = input.closest(".field") || input.parentNode, err = holder.querySelector(".field-error[data-js]");
    if (!msg) { if (err) err.remove(); input.classList.remove("is-invalid"); input.removeAttribute("aria-invalid"); return; }
    holder.querySelectorAll(".field-error:not([data-js])").forEach(function (n) { n.remove(); });
    if (!err) {
      err = document.createElement("p"); err.className = "field-error"; err.setAttribute("data-js", ""); err.setAttribute("role", "alert");
      err.id = (input.id || input.name) + "-err"; (input.closest(".input-wrap") || input).insertAdjacentElement("afterend", err);
      input.setAttribute("aria-describedby", err.id);
    }
    err.innerHTML = '<svg class="i" aria-hidden="true"><use href="#i-alert"/></svg>' + esc(msg);
    input.classList.add("is-invalid"); input.setAttribute("aria-invalid", "true");
  }
  function check(input, form) {
    var rules = (input.getAttribute("data-rule") || "").split("|"), msg = "";
    for (var i = 0; i < rules.length && !msg; i++) {
      var parts = rules[i].split(":"), fn = RULES[parts[0]];
      if (fn) msg = fn(input.value, form, parts.slice(1).join(":"));
    }
    fieldError(input, msg); return !msg;
  }
  $$("form[data-validate]").forEach(function (form) {
    var inputs = $$("[data-rule]", form);
    inputs.forEach(function (i) {
      i.addEventListener("blur", function () { if (i.value || i.classList.contains("is-invalid")) check(i, form); });
      i.addEventListener("input", function () { if (i.classList.contains("is-invalid")) check(i, form); });
    });
    form.addEventListener("submit", function (ev) {
      var bad = inputs.filter(function (i) { return !check(i, form); });
      if (bad.length) { ev.preventDefault(); bad[0].focus(); }
    });
    var first = $(".is-invalid", form); if (first) first.focus();
  });

  // self-rating page: show the name of the level being chosen
  $$("input[type=radio][data-label]").forEach(function (r) {
    r.addEventListener("change", function () { var t = $('[data-level-name="' + r.name + '"]'); if (t) t.textContent = r.getAttribute("data-label"); });
  });

  // ------------------------------------------- code editors, autosave, timer, quiz progress
  $$("textarea[data-tab-indent]").forEach(function (ta) {
    ta.addEventListener("keydown", function (ev) {
      if (ev.key !== "Tab" || ev.shiftKey || ev.ctrlKey || ev.altKey || ev.metaKey) return;
      ev.preventDefault();
      var s = ta.selectionStart, e = ta.selectionEnd;
      ta.value = ta.value.slice(0, s) + "    " + ta.value.slice(e); ta.selectionStart = ta.selectionEnd = s + 4;
    });
  });
  $$("form[data-autosave]").forEach(function (form) {
    var url = form.getAttribute("data-autosave"), state = $("[data-save-state]"), timer = null, dirty = false, busy = false;
    function say(text, cls) { if (!state) return; state.textContent = text; state.className = "save-state " + (cls || ""); }
    function save() {
      if (busy || !dirty) return; busy = true; dirty = false; say("Saving...");
      var data = new URLSearchParams(new FormData(form));
      fetch(url, { method: "POST", credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRF-Token": csrf, "Content-Type": "application/x-www-form-urlencoded" }, body: data.toString() })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function () { say("Draft saved " + new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), "ok"); })
        .catch(function () { dirty = true; say("Could not save - will retry", "err"); })
        .then(function () { busy = false; if (dirty) { clearTimeout(timer); timer = setTimeout(save, 4000); } });
    }
    var total = $$("fieldset[data-q]", form).length, bar = $("[data-answered-bar]"), txt = $("[data-answered]");
    function progressUpdate() {
      if (!total) return;
      var n = $$("fieldset[data-q]", form).filter(function (f) { return f.querySelector("input:checked"); }).length, pct = Math.round(100 * n / total);
      if (txt) txt.textContent = n + " of " + total + " answered";
      if (bar) { bar.firstElementChild.style.width = pct + "%"; bar.setAttribute("aria-valuenow", pct); }
    }
    function changed() { dirty = true; say("Unsaved changes"); clearTimeout(timer); timer = setTimeout(save, 1500); progressUpdate(); }
    form.addEventListener("input", changed); form.addEventListener("change", changed);
    progressUpdate();
  });
  $$("[data-timer-start]").forEach(function (t) {
    var start = Date.parse(t.getAttribute("data-timer-start").replace(" ", "T") + "Z");
    if (isNaN(start)) return;
    function tick() { var s = Math.max(0, Math.floor((Date.now() - start) / 1000)), m = Math.floor(s / 60); t.textContent = m >= 60 ? Math.floor(m / 60) + "h " + (m % 60) + "m" : m + ":" + String(s % 60).padStart(2, "0"); }
    tick(); setInterval(tick, 1000);
  });

  // ---------------------------------------- roadmap: tick study materials without reload
  function setBar(wrapper, pct) { var bar = wrapper && wrapper.querySelector(".bar"); if (bar) { bar.firstElementChild.style.width = pct + "%"; bar.setAttribute("aria-valuenow", pct); } }
  $$("form[data-item-form]").forEach(function (form) {
    form.addEventListener("submit", function (ev) {
      if (!window.fetch) return;
      ev.preventDefault();
      var btn = form.querySelector("button"); btn.disabled = true;
      fetch(form.action, { method: "POST", credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRF-Token": csrf, "Content-Type": "application/x-www-form-urlencoded" }, body: new URLSearchParams(new FormData(form)).toString() })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (d) {
          var hidden = form.querySelector('input[name="done"]'), done = !!d.completed_now;
          hidden.value = done ? "0" : "1"; btn.setAttribute("aria-pressed", done ? "true" : "false");
          btn.setAttribute("aria-label", (done ? "Mark as not done: " : "Mark as done: ") + (btn.getAttribute("data-title") || ""));
          form.closest("li").classList.toggle("done", done);
          var id = d.milestone_id, c = $('[data-resource-count="' + id + '"]'); if (c) c.textContent = d.resource_done + "/" + d.resource_total;
          setBar($('[data-milestone-bar="' + id + '"]'), d.resource_percent);
          var st = $('[data-status-for="' + id + '"]'); if (st && d.status === "in_progress") st.innerHTML = '<span class="chip chip-brand">In progress</span>';
          if (done && d.new_badges && d.new_badges.length) toast("New badge: " + d.new_badges.join(", ") + "!", "success");
        })
        .catch(function () { form.submit(); })
        .then(function () { btn.disabled = false; });
    });
  });

  // ------------------------------------------------------ notifications "pulse"
  var badge = $("[data-bell-badge]");
  if (badge && window.fetch) {
    var poll = function () {
      if (document.hidden) return;
      fetch("/api/unread", { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) { if (!d) return; badge.hidden = !d.unread; badge.textContent = d.unread > 9 ? "9+" : d.unread; })
        .catch(function () { /* offline: keep the last number */ });
    };
    setInterval(poll, 60000); document.addEventListener("visibilitychange", poll);
  }

  // ---------------------------------------------------------------------- charts
  var tipEl;
  function tip(box, html, x, y) {
    if (!tipEl || tipEl.parentNode !== box) { tipEl = document.createElement("div"); tipEl.className = "tip"; tipEl.setAttribute("aria-hidden", "true"); box.appendChild(tipEl); }
    if (html === null) { tipEl.classList.remove("on"); return; }
    tipEl.innerHTML = html;
    var w = box.clientWidth, tw = tipEl.offsetWidth;
    tipEl.style.left = Math.max(4, Math.min(w - tw - 4, x - tw / 2)) + "px"; tipEl.style.top = Math.max(0, y - tipEl.offsetHeight - 14) + "px";
    tipEl.classList.add("on");
  }
  function wrapLabel(s, n) {
    var words = String(s).split(" "), lines = [], cur = "";
    words.forEach(function (w) { if ((cur + " " + w).trim().length > n && cur) { lines.push(cur); cur = w; } else cur = (cur + " " + w).trim(); });
    if (cur) lines.push(cur); return lines.slice(0, 3);
  }
  function hover(node, box, html, x, y) {
    function show() { tip(box, html, x, y); }
    node.addEventListener("mouseenter", show); node.addEventListener("focus", show);
    node.addEventListener("mouseleave", function () { tip(box, null); }); node.addEventListener("blur", function () { tip(box, null); });
  }

  function radar(box, cfg) {
    var W = 520, H = 440, cx = W / 2, cy = H / 2 + 4, R = 138, n = cfg.labels.length, max = cfg.max || 5;
    var svg = el("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": cfg.title || "Radar chart" }, box);
    function pt(i, v) { var a = -Math.PI / 2 + i * 2 * Math.PI / n, r = R * Math.max(0, Math.min(v, max)) / max; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; }
    for (var k = 1; k <= max; k++) {
      var ring = []; for (var i = 0; i < n; i++) ring.push(pt(i, k).join(","));
      el("polygon", { points: ring.join(" "), "class": "c-grid" }, svg);
      var tk = el("text", { x: cx + 4, y: cy - R * k / max + 11, "class": "c-tick" }, svg); tk.textContent = k;
    }
    for (var j = 0; j < n; j++) {
      var p = pt(j, max); el("line", { x1: cx, y1: cy, x2: p[0], y2: p[1], "class": "c-axis" }, svg);
      var lp = pt(j, max + 0.62), anchor = lp[0] < cx - 8 ? "end" : lp[0] > cx + 8 ? "start" : "middle";
      var lines = wrapLabel(cfg.labels[j], 14), t = el("text", { x: lp[0], y: lp[1] - (lines.length - 1) * 6 + 4, "text-anchor": anchor, "class": "c-label" }, svg);
      lines.forEach(function (ln, li) { var s = el("tspan", { x: lp[0], dy: li ? 13 : 0 }, t); s.textContent = ln; });
    }
    var layers = [];
    cfg.series.forEach(function (s, si) {
      var g = el("g", { "data-series": si }, svg), pts = s.values.map(function (v, i) { return pt(i, v).join(","); }).join(" ");
      var poly = el("polygon", { points: pts, fill: s.color, "fill-opacity": s.fill === false ? 0 : 0.2, stroke: s.color, "stroke-width": 2.4, "stroke-linejoin": "round", "stroke-dasharray": s.dashed ? "6 5" : "none", "class": "c-area" }, g);
      if (!reduceMotion && poly.animate) { poly.style.transformOrigin = cx + "px " + cy + "px"; poly.animate([{ transform: "scale(.05)", opacity: 0 }, { transform: "scale(1)", opacity: 1 }], { duration: 800, easing: "cubic-bezier(.2,.7,.2,1)" }); }
      if (!s.dashed) s.values.forEach(function (v, i) {
        var q = pt(i, v), d = el("circle", { cx: q[0], cy: q[1], r: 4.5, fill: s.color, stroke: "var(--surface)", "stroke-width": 2, "class": "c-dot", tabindex: 0 }, g);
        var req = (cfg.series[1] || {}).values;
        hover(d, box, "<b>" + esc(cfg.labels[i]) + "</b><span>" + esc(s.name) + ": " + v + (req && si === 0 ? " (target " + req[i] + ")" : "") + "</span>", q[0] / W * box.clientWidth, q[1] / H * box.clientHeight);
      });
      layers.push(g);
    });
    return layers;
  }

  function line(box, cfg) {
    var W = 640, H = 300, L = 38, Rr = 16, T = 14, B = 34, max = cfg.max || 5;
    var svg = el("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": cfg.title || "Line chart" }, box);
    function ms(t) { return Date.parse(t.replace(" ", "T") + "Z"); }
    var all = []; cfg.series.forEach(function (s) { s.points.forEach(function (p) { all.push(ms(p.t)); }); });
    var t0 = Math.min.apply(null, all), t1 = Math.max.apply(null, all); if (t0 === t1) { t0 -= 864e5; t1 += 864e5; }
    function X(t) { return L + (ms(t) - t0) / (t1 - t0) * (W - L - Rr); } function Y(v) { return T + (1 - v / max) * (H - T - B); }
    for (var k = 0; k <= max; k++) { el("line", { x1: L, x2: W - Rr, y1: Y(k), y2: Y(k), "class": "c-grid" }, svg); var tt = el("text", { x: L - 10, y: Y(k) + 4, "text-anchor": "end", "class": "c-tick" }, svg); tt.textContent = k; }
    [t0, t1].forEach(function (t, i) { var x = L + i * (W - L - Rr), tx = el("text", { x: x, y: H - 10, "text-anchor": i ? "end" : "start", "class": "c-tick" }, svg); tx.textContent = new Date(t).toLocaleDateString([], { day: "numeric", month: "short" }); });
    var layers = [];
    cfg.series.forEach(function (s, si) {
      var g = el("g", { "data-series": si }, svg), d = s.points.map(function (p, i) { return (i ? "L" : "M") + X(p.t).toFixed(1) + " " + Y(p.y).toFixed(1); }).join(" ");
      el("path", { d: d, stroke: s.color, "class": "c-line" + (reduceMotion ? "" : " c-anim"), pathLength: 1000 }, g);
      s.points.forEach(function (p) {
        var cx = X(p.t), cy = Y(p.y), c = el("circle", { cx: cx, cy: cy, r: 4.5, fill: s.color, stroke: "var(--surface)", "stroke-width": 2, "class": "c-dot", tabindex: 0 }, g);
        hover(c, box, "<b>" + esc(s.name) + ": " + p.y + "/5</b><span>" + esc(p.label || "") + "</span>", cx / W * box.clientWidth, cy / H * box.clientHeight);
      });
      layers.push(g);
    });
    return layers;
  }

  function legend(box, cfg, layers) {
    if (cfg.series.length < 2) return;
    var lg = document.createElement("div"); lg.className = "chart-legend";
    cfg.series.forEach(function (s, i) {
      var b = document.createElement("button"); b.type = "button"; b.setAttribute("aria-pressed", "true");
      b.style.setProperty("--c", s.color); b.innerHTML = "<i></i>" + esc(s.name);
      b.addEventListener("click", function () { var on = b.getAttribute("aria-pressed") !== "true"; b.setAttribute("aria-pressed", on ? "true" : "false"); layers[i].style.display = on ? "" : "none"; });
      lg.appendChild(b);
    });
    box.parentNode.insertBefore(lg, box.nextSibling);
  }
  $$("[data-chart]").forEach(function (box) {
    var cfg; try { cfg = JSON.parse(box.getAttribute("data-chart")); } catch (e) { return; }
    box.classList.add("chart-box");
    var layers = cfg.type === "radar" ? radar(box, cfg) : cfg.type === "line" ? line(box, cfg) : null;
    if (layers) legend(box, cfg, layers);
  });

  // ------------------------------------------------ what-if simulator (skill gaps page)
  $$("[data-sim]").forEach(function (root) {
    var rows = JSON.parse(root.getAttribute("data-sim")), total = 0, base = 0;
    var ring = $(".ring-fill", root), num = $(".ring strong", root), delta = $("[data-sim-delta]", root);
    rows.forEach(function (r) { total += r.required * r.importance; base += Math.min(r.level, r.required) * r.importance; });
    var basePct = total ? 100 * base / total : 100;
    function recompute() {
      var vals = rows.map(function (r) { return r.level; });
      $$("input[type=range]", root).forEach(function (inp) {
        var i = parseInt(inp.getAttribute("data-i"), 10); vals[i] = parseInt(inp.value, 10);
        $("output", inp.closest(".sim-row")).textContent = "Level " + vals[i];
      });
      var got = 0; rows.forEach(function (r, i) { got += Math.min(vals[i], r.required) * r.importance; });
      var pct = total ? 100 * got / total : 100;
      if (ring) { ring.style.animation = "none"; ring.style.setProperty("--p", pct.toFixed(1)); }
      if (num) { num.removeAttribute("data-count"); num.textContent = Math.round(pct); }
      if (delta) delta.textContent = pct > basePct + 0.05 ? "+" + (pct - basePct).toFixed(1) + " points vs. today" : "Move a slider to see the effect";
    }
    root.addEventListener("input", recompute);
    var reset = $("[data-sim-reset]", root);
    if (reset) reset.addEventListener("click", function () { $$("input[type=range]", root).forEach(function (inp) { inp.value = rows[parseInt(inp.getAttribute("data-i"), 10)].level; }); recompute(); });
  });
})();
