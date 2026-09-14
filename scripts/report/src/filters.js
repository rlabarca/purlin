/* The five filters the board offers. Each one answers a question a person
   arrives with, and they compose: a rule shows when every active filter
   accepts it, and a feature shows when one of its rules does. */

var FILTERS = [
  {id: 'high-open', label: 'High risk not approved',
   test: function (rule) {
     return rule.risk === 'high' && rule.state !== 'Approved';
   }},
  {id: 'stale', label: 'Stale',
   test: function (rule) { return rule.state === 'Stale'; }},
  {id: 'no-negative', label: 'No negative case',
   test: function (rule) {
     return findingsOf(rule).indexOf('happy_path_only') >= 0;
   }},
  {id: 'low-strength', label: 'Low test strength',
   test: function (rule, feature) {
     return feature.test_strength != null
       && feature.test_strength < minStrength();
   }},
  {id: 'open', label: 'Open items',
   test: function (rule) {
     var flags = rule.flags || {};
     return rule.state === 'Drafted' || rule.state === 'Stale'
       || !!flags.needs_ai_review || !!flags.re_verify_pending;
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

function minStrength() {
  return (DATA.gate && DATA.gate.min_strength) || 0;
}

function activeFilters() {
  return FILTERS.filter(function (f) { return VIEW.filters[f.id]; });
}

/* The rules of one feature that every active filter accepts. */
function visibleRules(feature) {
  var active = activeFilters();
  if (!active.length) { return feature.rules || []; }
  return (feature.rules || []).filter(function (rule) {
    return active.every(function (f) { return f.test(rule, feature); });
  });
}

function filtersMarkup() {
  return '<div class="filters">' + FILTERS.map(function (f) {
    return '<button class="chip" data-act="filter" data-filter="' + f.id
      + '" aria-pressed="' + (VIEW.filters[f.id] ? 'true' : 'false') + '">'
      + esc(f.label) + '</button>';
  }).join('') + '</div>';
}
