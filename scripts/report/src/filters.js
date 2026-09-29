/* The filters the board offers, from `strong` up: one pill for the `No
   proof` box, then one per word the strong cell reads that asks for work.
   Each pill carries the count it would leave, so the pill and the box or the
   cell it mirrors state the same number before anything is pressed. They
   compose: a rule shows when every set filter accepts it, and a spec shows
   when one of its rules does. A filter that asks about a step the gate does
   not reach is not offered at all. */

/* One pill per word the strong cell reads, shown at `strong` and above. */
function strongFilter(id, label) {
  var word = label.toLowerCase();
  return {id: id, label: label, step: 'strong', test: function (rule) {
    return cellWord(rule, 'strong') === word;
  }};
}

/* Built on each render rather than declared once, so the labels can read
   the names the shell declares after this file. A pill counts the rules
   whose status is the word on it. */
function allFilters() {
  return [{id: 'no-proof', label: NO_PROOF, step: 'strong',
           test: function (rule) { return rule.left === 'no_proof'; }},
          strongFilter('weak', 'Weak'),
          strongFilter('not-audited', 'Not audited')];
}

function offeredFilters() {
  return allFilters().filter(function (f) { return level(f.step); });
}

function activeFilters() {
  return offeredFilters().filter(function (f) { return VIEW.filters[f.id]; });
}

/* How many rules one filter accepts, over every spec. Counted from the rules
   a spec owns, so an anchor's rule is counted once rather than once per
   feature that requires it, which is how the summary counts it too. */
function filterCount(f) {
  var found = 0;
  (DATA.features || []).forEach(function (feature) {
    ownRules(feature).forEach(function (r) { found += f.test(r, feature) ? 1 : 0; });
  });
  return found;
}

/* The rules of one feature that every set filter accepts. A feature lists
   the rules it owns; a rule it proves from an anchor is listed once, under
   that anchor. */
function visibleRules(feature) {
  var active = activeFilters();
  if (!active.length) { return ownRules(feature); }
  return ownRules(feature).filter(function (rule) {
    return active.every(function (f) { return f.test(rule, feature); });
  });
}

function filtersMarkup() {
  var offered = offeredFilters();
  if (!offered.length) { return ''; }
  return '<div class="filters">' + offered.map(function (f) {
    return '<button class="chip" data-act="filter" data-filter="' + f.id
      + '" aria-pressed="' + (VIEW.filters[f.id] ? 'true' : 'false') + '">'
      + esc(f.label) + '<b>' + filterCount(f) + '</b></button>';
  }).join('') + '</div>';
}
