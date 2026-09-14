/* Both themes ship in the token block. The toggle sets data-theme on the root
   element and swaps the logo to the colourway that reads on the new ground;
   nothing else changes, because every colour on the page is a token that the
   theme redefines. */

function currentTheme() {
  return document.documentElement.getAttribute('data-theme') === 'light'
    ? 'light' : 'dark';
}

function restoreTheme() {
  var saved = null;
  try { saved = localStorage.getItem('purlin-theme'); } catch (e) {}
  document.documentElement.setAttribute(
    'data-theme', saved === 'light' ? 'light' : 'dark');
}

function toggleTheme() {
  var next = currentTheme() === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', next);
  try { localStorage.setItem('purlin-theme', next); } catch (e) {}
}

function logoSrc() {
  return currentTheme() === 'light' ? PURLIN_LOGO.light : PURLIN_LOGO.dark;
}

function themeButton() {
  var next = currentTheme() === 'light' ? 'Dark theme' : 'Light theme';
  return '<button class="btn glyph" data-act="theme" title="' + next
    + '" aria-label="' + next + '">\u25d0</button>';
}
