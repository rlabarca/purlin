/* The filter buttons above the table: one per line of what is left to do,
   in the payload's order. Each is named as its line is, without the count
   and the noun it counts, so `4 rules to strengthen` is the button
   `To strengthen`, and it carries the count the payload gives that line: the
   page counts nothing itself, so the button, the terminal's `Left to do` and
   the evidence state one number. A kind at zero is not in the payload, so it
   has no button. One button is chosen at a time: choosing it shows the rules
   the payload gives that kind, and one line under the buttons names the
   command that clears them, typed in Claude Code. The page runs nothing. */

/* The kind of work that counts the version rather than any rule: choosing
   it names the command and leaves every rule showing, because no rule
   carries it. */
var VERSION_KINDS = ['to_tag'];

/* The words of one line of what is left, without its count and noun, in
   sentence case: `1 rule to fix` reads `To fix`, `2 rules to test on
   Windows` reads `To test on Windows`, `the version to tag` reads `To tag`. */
function leftLabel(item) {
  var text = String(item.text || '');
  var at = text.indexOf(' to ');
  var words = at >= 0 ? text.slice(at + 1) : text;
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/* The lines of what is left, as the payload lists them. */
function leftItems() { return (DATA && DATA.left) || []; }

/* The line chosen, or null. A choice the payload no longer lists, as after a
   reload once the command has run, is no choice. */
function chosenItem() {
  var found = null;
  leftItems().forEach(function (item) {
    if (item.kind === VIEW.filter) { found = item; }
  });
  return found;
}

/* The rules of one feature the chosen line accepts. A feature lists the
   rules it owns; a rule it proves from an anchor is listed once, under that
   anchor. */
function visibleRules(feature) {
  var item = chosenItem();
  if (!item || VERSION_KINDS.indexOf(item.kind) >= 0) {
    return ownRules(feature);
  }
  return ownRules(feature).filter(function (rule) {
    return rule.left === item.kind;
  });
}

/* The buttons, then the command for the one chosen. With nothing left the
   payload's last line stands in their place. */
function filtersMarkup() {
  var items = leftItems();
  if (!items.length) {
    return DATA.last_line ? '<p class="lastline">' + esc(DATA.last_line)
      + '</p>' : '';
  }
  var chosen = chosenItem();
  return '<div class="filters">' + items.map(function (item) {
    return '<button class="chip" data-act="filter" data-filter="'
      + esc(item.kind) + '" aria-pressed="'
      + (chosen && chosen.kind === item.kind ? 'true' : 'false') + '">'
      + esc(leftLabel(item)) + '<b>' + esc(item.count) + '</b></button>';
  }).join('') + '</div>'
    + (chosen ? '<p class="cmdline">Type <span class="cmd">'
      + esc(chosen.command) + '</span> in Claude Code.</p>' : '');
}
