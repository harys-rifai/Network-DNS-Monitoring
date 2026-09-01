/**
 * Theme Toggle
 * Persists the user's theme preference (light/dark) in localStorage.
 * On load, reads the saved preference or falls back to system preference.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "ndn-theme";
  var THEME_LIGHT = "light";
  var THEME_DARK = "dark";

  var body = document.body;
  var toggleBtn = document.getElementById("theme-toggle");
  var toggleIcon = toggleBtn ? toggleBtn.querySelector(".theme-icon") : null;

  function applyTheme(theme) {
    if (theme === THEME_DARK) {
      body.classList.add("dark-theme");
      if (toggleIcon) toggleIcon.textContent = "☀️";
    } else {
      body.classList.remove("dark-theme");
      if (toggleIcon) toggleIcon.textContent = "🌙";
    }
  }

  function getSystemPreference() {
    if (typeof window !== "undefined" && window.matchMedia) {
      return window.matchMedia("(prefers-color-scheme: dark)").matches
        ? THEME_DARK
        : THEME_LIGHT;
    }
    return THEME_LIGHT;
  }

  function getSavedTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY) || null;
    } catch (e) {
      return null;
    }
  }

  function saveTheme(theme) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      /* ignore — storage may be unavailable */
    }
  }

  function getCurrentTheme() {
    return getSavedTheme() || getSystemPreference();
  }

  function toggleTheme() {
    var current = getCurrentTheme();
    var next = current === THEME_DARK ? THEME_LIGHT : THEME_DARK;
    applyTheme(next);
    saveTheme(next);
  }

  /* Initialise */
  if (toggleBtn) {
    toggleBtn.addEventListener("click", toggleTheme);
  }

  var initialTheme = getCurrentTheme();
  applyTheme(initialTheme);

  /* Listen for system preference changes */
  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function (e) {
      if (!getSavedTheme()) {
        applyTheme(e.matches ? THEME_DARK : THEME_LIGHT);
      }
    });
  }
})();
