'use strict';
// Light or dark, the way the operator page keeps it: the key 'kryuk-theme' on <html data-theme>. Without a saved
// choice the phone's own setting decides (tokens.css). Loaded in the head, before the page is drawn.
(function () {
  var root = document.documentElement;
  var saved = null;
  try { saved = localStorage.getItem('kryuk-theme'); } catch (e) {}
  if (saved === 'dark' || saved === 'light') root.dataset.theme = saved;
  document.addEventListener('DOMContentLoaded', function () {
    var button = document.getElementById('theme');
    if (!button) return;
    button.addEventListener('click', function () {
      var dark = root.dataset.theme ? root.dataset.theme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
      root.dataset.theme = dark ? 'light' : 'dark';
      try { localStorage.setItem('kryuk-theme', root.dataset.theme); } catch (e) {}
    });
  });
})();
