/* The Board: where every rule stands against the gate, and which specs hold
   the rules that have not got there yet. */

/* A rule the payload lists under the feature that owns it. An anchor's rule
   appears under every feature that requires it, so counting every entry would
   count that rule once per feature. */
function ownRules(feature) {
  return (feature.rules || []).filter(function (rule) {
    return rule.label === 'own';
  });
}

/* One tile per bucket the gate reaches, and at `signed` a flag card beside
   them for the signatures that no longer match. A flag is counted beside the
   buckets, never instead of one, so it never shares their row. */
function statStrip() {
  var summary = DATA.summary || {};
  var shown = BUCKETS.filter(function (bucket) {
    return bucket === 'untested' || bucket === 'failing' || level(bucket);
  });
  var tiles = shown.map(function (bucket) {
    return '<div class="tile"><div class="tile-v" style="color:var(--state-'
      + bucketTone(bucket) + ')">' + (summary[bucket] || 0) + '</div>'
      + '<div class="tile-l">' + esc(BUCKET_LABELS[bucket]) + '</div></div>';
  }).join('');
  var stale = summary.stale || 0;
  var flag = level('signed')
    ? '<div class="flag' + (stale ? ' on' : '') + '">'
      + '<div class="flag-v">' + stale + '</div>'
      + '<div class="flag-l">Stale</div></div>'
    : '';
  return '<div class="strip' + (flag ? ' flagged' : '') + '">'
    + '<div class="tiles">' + tiles + '</div>' + flag + '</div>';
}

/* The columns the gate reaches, and no others. */
function boardColumns() {
  var columns = [{label: 'Spec', width: '2fr'},
                 {label: 'Rules', width: '0.4fr'},
                 {label: 'Spec status', width: '0.8fr'},
                 {label: 'Tests', width: '0.9fr'},
                 {label: 'Last run', width: '2.6fr'}];
  if (level('strong')) {
    columns.push({label: 'Strength', width: '0.6fr'});
    columns.push({label: 'Strong', width: '1.2fr'});
  }
  if (level('signed')) {
    columns.push({label: 'Signed', width: '1.1fr'});
  }
  return columns;
}

/* How many of this spec's own rules the spec itself has finished: a rule no
   proof line names is drafted, and no test can be written for it. */
function specStatusCell(feature) {
  var ready = 0;
  var drafted = 0;
  ownRules(feature).forEach(function (rule) {
    if (rule.spec === 'drafted') { drafted += 1; } else { ready += 1; }
  });
  return counts([[ready, 'ready', 'pass'], [drafted, 'drafted', 'idle']]);
}

/* What the tagged tests found, as the passed cells read it. A rule waiting on
   an operating system or sitting behind changed code is in none of the three:
   the Last run column and the rule's own row say which. */
function testsCell(feature) {
  var passed = 0;
  var failing = 0;
  var none = 0;
  ownRules(feature).forEach(function (rule) {
    var word = cellWord(rule, 'passed');
    if (word === 'passed') { passed += 1; }
    else if (word === 'failed') { failing += 1; }
    else if (word === 'no test') { none += 1; }
  });
  return counts([[passed, 'passed', 'pass'], [failing, 'failing', 'fail'],
                 [none, 'no test', 'warn']]);
}

function signedCell(feature) {
  var rollup = feature.rollup || {};
  var stale = rollup.stale || 0;
  return '<span class="trio"><b>' + (rollup.signed || 0) + ' of '
    + (rollup.rules || 0) + '</b>'
    + (stale ? '<i>·</i><b style="color:var(--state-fail)">' + stale
        + ' stale</b>' : '') + '</span>';
}

function featureRow(feature, columns) {
  var rollup = feature.rollup || {};
  var open = !!VIEW.features[feature.name];
  var cells = ['<span class="name"><span class="caret">'
    + (open ? '▼' : '▶') + '</span>' + designThumb(feature)
    + '<span class="n">' + esc(feature.name) + '</span></span>'];
  cells.push('<span class="mono">' + (rollup.rules || 0) + '</span>');
  cells.push(specStatusCell(feature));
  cells.push(testsCell(feature));
  cells.push(lastRun(feature));
  if (level('strong')) {
    cells.push(strength(rollup.test_strength == null
      ? feature.test_strength : rollup.test_strength));
    cells.push(ratio(rollup.strong || 0, rollup.rules || 0));
  }
  if (level('signed')) { cells.push(signedCell(feature)); }
  var row = '<div class="tr" data-act="feature" data-feature="'
    + esc(feature.name) + '">' + cells.map(function (cell) {
      return '<div>' + cell + '</div>';
    }).join('') + '</div>';
  if (!open) { return row; }
  return row + visibleRules(feature).map(function (rule) {
    return '<div class="rule" data-act="rule" data-feature="'
      + esc(feature.name) + '" data-rule="' + esc(rule.id) + '">'
      + '<span class="rid">' + esc(rule.id) + '</span>'
      + '<span class="rt">' + esc(rule.text) + '</span>'
      + '<span class="rp">' + GATE_LEVELS.map(function (name) {
        var cell = cellOf(rule, name);
        return cell ? pill(cell.word) : '';
      }).join('') + '</span></div>';
  }).join('');
}

function groupBand(name, features, columns) {
  var open = VIEW.groups[name] !== false;
  var met = 0;
  var total = 0;
  features.forEach(function (feature) {
    met += (feature.rollup || {}).met || 0;
    total += (feature.rollup || {}).rules || 0;
  });
  return '<div class="group" data-act="group" data-group="' + esc(name) + '">'
    + '<span class="caret">' + (open ? '▼' : '▶') + '</span>'
    + '<span class="gt">' + esc(name) + '</span>'
    + '<span class="muted">(' + features.length + ')</span>'
    + ratio(met, total) + '</div>'
    + (open ? features.map(function (feature) {
      return featureRow(feature, columns);
    }).join('') : '');
}

function renderBoard() {
  var columns = boardColumns();
  var shown = (DATA.features || []).filter(function (feature) {
    return visibleRules(feature).length > 0;
  });
  var order = [];
  var groups = {};
  shown.forEach(function (feature) {
    var name = feature.category || 'specs';
    if (!groups[name]) { groups[name] = []; order.push(name); }
    groups[name].push(feature);
  });
  var summary = DATA.summary || {};
  var head = '<section class="ledger"><h1 class="line">'
    + '<b>' + (summary.met || 0) + '</b> of <b>' + (summary.rules || 0)
    + '</b> rules meet the gate <b>' + esc(gateName()) + '</b>'
    + '<span class="sep">·</span><b>' + (summary.failing || 0)
    + '</b> failing</h1></section><section>' + statStrip() + '</section>';
  var table = order.length
    ? '<div class="tbl" style="--cols:' + columns.map(function (c) {
        /* minmax(0, ...) sizes every track from the widths alone. A bare fr
           track grows to fit its widest cell, and the header and each row are
           separate grids, so their columns drifted apart. */
        return 'minmax(0,' + c.width + ')';
      }).join(' ') + '"><div class="th">' + columns.map(function (c) {
        return '<div>' + esc(c.label) + '</div>';
      }).join('') + '</div>' + order.map(function (name) {
        return groupBand(name, groups[name], columns);
      }).join('') + '</div>'
    : '<div class="panel empty">No rule matches every filter you set.</div>';
  return head + '<section><p class="eyebrow">Specs</p>' + filtersMarkup()
    + table + '</section>';
}
