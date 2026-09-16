/* The filters the board offers. Each one answers a question a person arrives
   with, and they compose: a rule shows when every set filter accepts it, and
   a spec shows when one of its rules does. A filter that asks about a level
   the gate does not reach is not offered at all. */

var FILTERS = [
  {id: 'untested', label: 'Untested', level: 'passed',
   test: function (rule) { return rule.bucket === 'untested'; }},
  {id: 'failing', label: 'Failing', level: 'passed',
   test: function (rule) { return rule.bucket === 'failing'; }},
  {id: 'weak', label: 'Weak', level: 'strong',
   test: function (rule) { return cellWord(rule, 'strong') === 'weak'; }},
  {id: 'unsigned', label: 'Unsigned', level: 'signed',
   test: function (rule) { return cellWord(rule, 'signed') === 'unsigned'; }},
  {id: 'stale-or-held', label: 'Stale or held', level: 'signed',
   test: function (rule) {
     var flags = rule.flags || {};
     return !!flags.stale || !!flags.held;
   }}
];

/* Every finding on a rule, gathered from the proofs that carry them. */
function findingsOf(rule) {
  var found = [];
  (rule.proofs || []).forEach(function (proof) {
    (proof.findings || []).forEach(function (name) {
      if (found.indexOf(name) < 0) { found.push(name); }
    });
  });
  return found;
}

function offeredFilters() {
  return FILTERS.filter(function (f) { return level(f.level); });
}

function activeFilters() {
  return offeredFilters().filter(function (f) { return VIEW.filters[f.id]; });
}

/* The rules of one feature that every set filter accepts. */
function visibleRules(feature) {
  var active = activeFilters();
  if (!active.length) { return feature.rules || []; }
  return (feature.rules || []).filter(function (rule) {
    return active.every(function (f) { return f.test(rule, feature); });
  });
}

function filtersMarkup() {
  return '<div class="filters">' + offeredFilters().map(function (f) {
    return '<button class="chip" data-act="filter" data-filter="' + f.id
      + '" aria-pressed="' + (VIEW.filters[f.id] ? 'true' : 'false') + '">'
      + esc(f.label) + '</button>';
  }).join('') + '</div>';
}
