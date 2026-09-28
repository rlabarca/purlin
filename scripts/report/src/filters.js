/* The filters the board offers. There is one pill per bucket the board shows
   and one per evidence column beyond the tests, in the order the tiles and
   the columns read: a person who has just read a tile finds the pill that
   opens it in the same place. Each pill carries the count it would leave, so
   the pill and the tile or the cell it mirrors state the same number before
   anything is pressed. They compose: a rule shows when every set filter
   accepts it, and a spec shows when one of its rules does. A filter that asks
   about a level the gate does not reach is not offered at all. */

/* The three bucket pills read the tile's own label, so a bucket is named once
   on the page. */
function bucketFilter(bucket) {
  return {id: bucket, label: BUCKET_LABELS[bucket], level: 'passed',
    test: function (rule) { return rule.bucket === bucket; }};
}

/* One pill per word the strong cell reads, shown at `strong` and above. */
function strongFilter(id, label) {
  var word = label.toLowerCase();
  return {id: id, label: label, level: 'strong', test: function (rule) {
    return cellWord(rule, 'strong') === word;
  }};
}

/* Built on each render rather than declared once, so the labels can read the
   tile labels the shell declares after this file. */
function allFilters() {
  return [bucketFilter('untested'), bucketFilter('failing'),
          bucketFilter('partial'),
    /* A pill counts the rules whose status is the word on it: `Weak` the
       rules whose strong cell reads `weak`, `Not audited` those whose strong
       cell reads `not audited`. The rules that wait for a person are the
       queue pill's. */
    strongFilter('weak', 'Weak'),
    strongFilter('not-audited', 'Not audited'),
    /* The rules the Queue tab holds: a hand check or a signature, so the
       next step is a person's. */
    {id: 'queue', label: 'Queue', level: 'strong', test: function (rule) {
      return inQueue(rule);
    }},
    {id: 'stale', label: 'Stale', level: 'signed', test: function (rule) {
      return !!(rule.flags || {}).stale;
    }}];
}

/* Whether the queue names this rule, under the feature that owns it. */
function inQueue(rule) {
  return (DATA.queue || []).some(function (entry) {
    return entry.owner === rule.feature && entry.rule === rule.id;
  });
}

function offeredFilters() {
  return allFilters().filter(function (f) { return level(f.level); });
}

function activeFilters() {
  return offeredFilters().filter(function (f) { return VIEW.filters[f.id]; });
}

/* How many rules one filter accepts, over every spec. Counted from the rules
   a spec owns, so an anchor's rule is counted once rather than once per
   feature that requires it, which is how the tiles count it too. */
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
  return '<div class="filters">' + offeredFilters().map(function (f) {
    return '<button class="chip" data-act="filter" data-filter="' + f.id
      + '" aria-pressed="' + (VIEW.filters[f.id] ? 'true' : 'false') + '">'
      + esc(f.label) + '<b>' + filterCount(f) + '</b></button>';
  }).join('') + '</div>';
}
