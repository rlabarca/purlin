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

/* The button shows the glyph of the theme a click turns to, `◐` for the
   light and `◑` for the dark, and its hover and its name for a screen
   reader say that theme in words. */
function themeButton() {
  var light = currentTheme() === 'light';
  var next = light ? 'Dark theme' : 'Light theme';
  return '<button class="btn" data-act="theme" title="' + next
    + '" aria-label="' + next + '">' + (light ? '◑' : '◐')
    + '</button>';
}
