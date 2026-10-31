// Runs before first paint: marks JS as available and applies the saved (or system) colour theme, so there is no flash.
(function () {
  var root = document.documentElement;
  root.classList.add("js");
  var theme = null;
  try { theme = localStorage.getItem("st-theme"); } catch (e) { /* storage blocked: fall back to system */ }
  if (theme !== "light" && theme !== "dark") {
    theme = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  root.setAttribute("data-theme", theme);
})();
